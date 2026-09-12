import hashlib,json,uuid,secrets
from datetime import datetime,timezone
import httpx
from fastapi import APIRouter,Depends,Header,HTTPException,Query
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import AgentTrace,Movie,B2BUsage,MonitoringEvent,B2BClient,MovieProducer
from ..config import get_settings
from ..security import encrypt_text,decrypt_text
from ..dependencies import require_admin
from ..schemas import B2BClientCreateRequest
router=APIRouter(prefix="/api",tags=["audit"]);settings=get_settings()

def _b2b_key_hash(key:str)->str:return hashlib.sha256(key.encode()).hexdigest()

def _b2b_client(db,key):
    h=_b2b_key_hash(key)
    client=db.query(B2BClient).filter(B2BClient.api_key_hash==h,B2BClient.active==True).first()
    if client:return client
    if key==settings.b2b_api_key:
        return None
    raise HTTPException(401,"Invalid B2B API key.")

@router.post("/admin/b2b-clients")
def create_b2b_client(data:B2BClientCreateRequest,x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    if x_admin_key!=settings.admin_api_key:raise HTTPException(401,"Invalid admin API key.")
    raw="csb2b_"+secrets.token_urlsafe(32);h=_b2b_key_hash(raw)
    row=B2BClient(name_enc=encrypt_text(data.name),api_key_hash=h,monthly_included_calls=settings.b2b_monthly_included_calls,overage_per_1000_usd=settings.b2b_overage_per_1000_usd)
    db.add(row);db.commit();db.refresh(row)
    return {"id":row.id,"name":data.name,"api_key":raw,"warning":"Copy this API key now. CineSense stores only its hash."}

@router.get("/admin/b2b-clients")
def list_b2b_clients(x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    if x_admin_key!=settings.admin_api_key:raise HTTPException(401,"Invalid admin API key.")
    return [{"id":r.id,"name":decrypt_text(r.name_enc),"active":r.active,"monthly_included_calls":r.monthly_included_calls,"overage_per_1000_usd":r.overage_per_1000_usd} for r in db.query(B2BClient).order_by(B2BClient.id).all()]

def _consume_b2b(db,key,client=None):
    month=datetime.now(timezone.utc).strftime("%Y-%m");h=_b2b_key_hash(key)
    row=db.query(B2BUsage).filter(B2BUsage.api_key_hash==h,B2BUsage.usage_month==month).first()
    if not row:row=B2BUsage(api_key_hash=h,usage_month=month,call_count=0);db.add(row)
    row.call_count+=1;db.commit()
    included=client.monthly_included_calls if client else settings.b2b_monthly_included_calls; rate=client.overage_per_1000_usd if client else settings.b2b_overage_per_1000_usd;over=max(0,row.call_count-included)
    over_units=(over+999)//1000
    return {"month":month,"calls":row.call_count,"included":included,"remaining":max(0,included-row.call_count),"overage_calls":over,"estimated_overage_usd":round(over_units*rate,2)}

@router.get("/traces")
def traces(limit:int=80,db:Session=Depends(get_db),admin=Depends(require_admin)):
    rows=db.query(AgentTrace).order_by(AgentTrace.timestamp.desc()).limit(min(max(limit,1),200)).all()
    return [{"trace_id":r.trace_id,"sender":r.sender,"receiver":r.receiver,"intent":r.intent,"payload":json.loads(r.payload_safe),"timestamp":r.timestamp} for r in rows]

@router.get("/monitoring")
def monitoring(limit:int=100,x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    if x_admin_key!=settings.admin_api_key:raise HTTPException(401,"Invalid admin API key.")
    rows=db.query(MonitoringEvent).order_by(MonitoringEvent.created_at.desc()).limit(min(max(limit,1),500)).all()
    return [{"level":r.level,"event_type":r.event_type,"detail":r.detail_safe,"created_at":r.created_at} for r in rows]

@router.post("/admin/sync-tmdb")
async def sync_tmdb(x_admin_key:str|None=Header(None),expand:bool=Query(True),pages:int=Query(2,ge=1,le=10),db:Session=Depends(get_db)):
    if x_admin_key!=settings.admin_api_key:raise HTTPException(401,"Invalid admin API key.")
    if not settings.tmdb_api_key:raise HTTPException(400,"TMDB_API_KEY is not configured.")
    updated=0;added=0
    async with httpx.AsyncClient(timeout=15) as client:
        for movie in db.query(Movie).filter(Movie.tmdb_id.is_not(None)).all():
            try:
                r=await client.get(f"https://api.themoviedb.org/3/movie/{movie.tmdb_id}",params={"api_key":settings.tmdb_api_key,"language":"en-US","append_to_response":"credits,keywords"})
                if r.status_code!=200:continue
                data=r.json();_apply_tmdb(db,movie,data);updated+=1
            except Exception:continue
        if expand:
            for page in range(1,pages+1):
                try:
                    r=await client.get("https://api.themoviedb.org/3/movie/popular",params={"api_key":settings.tmdb_api_key,"language":"en-US","page":page})
                    if r.status_code!=200:continue
                    for item in r.json().get("results",[]):
                        tmdb_id=item.get("id")
                        if not tmdb_id or db.query(Movie).filter(Movie.tmdb_id==tmdb_id).first():continue
                        d=await client.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}",params={"api_key":settings.tmdb_api_key,"language":"en-US","append_to_response":"credits,keywords"})
                        if d.status_code!=200:continue
                        data=d.json()
                        if not data.get("runtime") or not data.get("overview"):continue
                        movie=Movie(title=data.get("title") or "Untitled",year=int((data.get("release_date") or "0000")[:4] or 0),genres="|".join(g.get("name","") for g in data.get("genres",[]) if g.get("name")),runtime=int(data.get("runtime") or 0),overview=data.get("overview") or "",rating=float(data.get("vote_average") or 0),language=(data.get("original_language") or "").upper(),studio=((data.get("production_companies") or [{}])[0].get("name") or "Independent"),director="",cast="",moods=_infer_moods(data),pace="Moderate",keywords="",tmdb_id=tmdb_id,poster_url="",backdrop_url="")
                        _apply_tmdb(db,movie,data);db.add(movie);added+=1
                except Exception:continue
    db.commit();return {"updated":updated,"added":added,"total":db.query(Movie).count()}

def _infer_moods(data):
    genres={g.get("name","") for g in data.get("genres",[])};m=[]
    if genres & {"Comedy","Animation","Family"}:m.append("Happy")
    if genres & {"Romance"}:m.append("Romantic")
    if genres & {"Thriller","Horror","Action","Mystery"}:m.append("Thrilled")
    if genres & {"Drama"}:m.append("Sad/Cathartic")
    if not m:m.append("Relaxed")
    return "|".join(dict.fromkeys(m))

def _apply_tmdb(db,movie,data):
    if data.get("poster_path"):movie.poster_url="https://image.tmdb.org/t/p/w500"+data["poster_path"]
    if data.get("backdrop_path"):movie.backdrop_url="https://image.tmdb.org/t/p/original"+data["backdrop_path"]
    if data.get("runtime"):movie.runtime=int(data["runtime"])
    if data.get("vote_average") is not None:movie.rating=float(data.get("vote_average") or 0)
    credits=data.get("credits") or {};crew=credits.get("crew") or [];cast=credits.get("cast") or []
    directors=[x.get("name") for x in crew if x.get("job")=="Director" and x.get("name")]
    if directors:movie.director=directors[0]
    if cast:movie.cast="|".join(x.get("name") for x in cast[:8] if x.get("name"))
    if getattr(movie,"id",None):
        db.query(MovieProducer).filter(MovieProducer.movie_id==movie.id).delete(synchronize_session=False)
        names=[]
        for person in crew:
            if person.get("job") in {"Producer","Executive Producer","Co-Producer"} and person.get("name") and person.get("name") not in names:
                names.append(person.get("name"))
        for name in names[:12]:db.add(MovieProducer(movie_id=movie.id,producer_name=name,source="tmdb"))
    kw=data.get("keywords") or {};items=kw.get("keywords") or kw.get("results") or []
    if items:movie.keywords="|".join(x.get("name") for x in items[:20] if x.get("name"))

@router.get("/b2b/recommend")
def b2b(mood:str|None=None,genre:str|None=None,minutes:int|None=None,x_api_key:str|None=Header(None),db:Session=Depends(get_db)):
    if not x_api_key:raise HTTPException(401,"Missing B2B API key.")
    client=_b2b_client(db,x_api_key)
    from ..agents.orchestrator import orchestrator
    from ..protocol import AgentEnvelope
    usage=_consume_b2b(db,x_api_key,client);trace_id=str(uuid.uuid4());prefs={"mood":mood,"genres":[genre] if genre else [],"time_available":minutes,"disliked":[]}
    env=AgentEnvelope(trace_id=trace_id,sender="orchestrator",receiver="retrieval",intent="b2b_recommend",payload=prefs)
    return {"trace_id":trace_id,"usage":usage,"results":orchestrator.retrieval.retrieve(db,env,f"{mood or ''} {genre or ''}",prefs,0,8)}

@router.get("/b2b/usage")
def b2b_usage(x_api_key:str|None=Header(None),db:Session=Depends(get_db)):
    if not x_api_key:raise HTTPException(401,"Missing B2B API key.")
    client=_b2b_client(db,x_api_key)
    month=datetime.now(timezone.utc).strftime("%Y-%m");h=_b2b_key_hash(x_api_key)
    row=db.query(B2BUsage).filter(B2BUsage.api_key_hash==h,B2BUsage.usage_month==month).first();calls=row.call_count if row else 0
    included=client.monthly_included_calls if client else settings.b2b_monthly_included_calls;rate=client.overage_per_1000_usd if client else settings.b2b_overage_per_1000_usd;over=max(0,calls-included);units=(over+999)//1000
    return {"month":month,"calls":calls,"included":included,"remaining":max(0,included-calls),"overage_calls":over,"estimated_overage_usd":round(units*rate,2),"starter_price_usd":49}
