from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..db import get_db
from ..models import Movie,RecommendationFeedback,ProfileWatchEvent,MovieMedia,MovieProducer
from ..schemas import WatchEventRequest,FeedbackRequest,SummarizeRequest
from ..dependencies import get_current_user, get_optional_user
from ..security import encrypt_text
from ..services.profiles import active_profile_id
from ..agents.retrieval import movie_dict
from ..agents.orchestrator import orchestrator
from ..services.llm import llm_service
from ..config import get_settings
from ..models import Profile
from ..services.family_logic import movie_allowed_for_profiles
import httpx, re
router=APIRouter(prefix="/api",tags=["movies"]);settings=get_settings()

def _visible_to_active_profile(db,user,movie):
    if not user:return True
    profile=db.get(Profile,active_profile_id(db,user))
    return not profile or movie_allowed_for_profiles(movie,[profile],db)

@router.get("/movies")
def list_movies(q:str|None=Query(None,max_length=120),genre:str|None=Query(None,max_length=50),mood:str|None=Query(None,max_length=50),limit:int=Query(360,ge=1,le=500),db:Session=Depends(get_db),user=Depends(get_optional_user)):
    query=db.query(Movie)
    if q:
        p=f"%{q}%";query=query.filter(or_(Movie.title.ilike(p),Movie.overview.ilike(p),Movie.keywords.ilike(p)))
    if genre:query=query.filter(Movie.genres.ilike(f"%{genre}%"))
    if mood:query=query.filter(Movie.moods.ilike(f"%{mood}%"))
    return [movie_dict(m) for m in query.order_by(Movie.rating.desc()).limit(limit).all() if _visible_to_active_profile(db,user,m)]

@router.get("/movies/{movie_id}")
def get_movie(movie_id:int,db:Session=Depends(get_db),user=Depends(get_optional_user)):
    m=db.get(Movie,movie_id)
    if not m:raise HTTPException(404,"Movie not found.")
    if not _visible_to_active_profile(db,user,m):raise HTTPException(404,"Movie not found.")
    return movie_dict(m)

@router.post("/movies/summarize")
async def summarize(data:SummarizeRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    m=db.get(Movie,data.movie_id)
    if not m:raise HTTPException(404,"Movie not found.")
    if not _visible_to_active_profile(db,user,m):raise HTTPException(404,"Movie not found.")
    context=f"Title: {m.title}\nYear: {m.year}\nGenres: {m.genres}\nOverview: {m.overview}"
    if llm_service.enabled:
        text=await llm_service.chat(f"Summarize this supplied movie plot in no more than {data.max_sentences} sentences. Do not add facts and avoid spoilers beyond the supplied overview.",context,[])
        if text:return {"movie_id":m.id,"summary":text,"provider":"llm"}
    sentences=[x.strip() for x in m.overview.replace("! ",". ").replace("? ",". ").split(". ") if x.strip()]
    summary=". ".join(sentences[:data.max_sentences])+("." if sentences else "")
    return {"movie_id":m.id,"summary":summary or m.overview,"provider":"deterministic"}

@router.post("/watch-events")
def watch(data:WatchEventRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    if not db.get(Movie,data.movie_id):raise HTTPException(404,"Movie not found.")
    profile_id=active_profile_id(db,user)
    db.add(ProfileWatchEvent(user_id=user.id,profile_id=profile_id,movie_id_enc=encrypt_text(str(data.movie_id)),rating_enc=encrypt_text(str(data.rating)) if data.rating is not None else "",watched=data.watched))
    db.commit();return {"ok":True,"profile_id":profile_id,"watch_history_encrypted":True,"rating_encrypted":data.rating is not None}

@router.post("/feedback")
def feedback(data:FeedbackRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    if not db.get(Movie,data.movie_id):raise HTTPException(404,"Movie not found.")
    db.add(RecommendationFeedback(user_id=user.id,movie_id=data.movie_id,reason=data.reason,details_enc=encrypt_text(data.details)));db.commit();return {"ok":True,"message":"Thanks. Your feedback was recorded for human review."}

@router.get("/fairness")
def fairness(db:Session=Depends(get_db)):return orchestrator.retrieval.fairness_snapshot(db)


@router.get("/site/hero")
def site_hero(db:Session=Depends(get_db)):
    media=db.query(MovieMedia).filter(MovieMedia.featured==True).first()
    if not media:return {"movie":None,"trailer_youtube_url":""}
    movie=db.get(Movie,media.movie_id)
    return {"movie":movie_dict(movie) if movie else None,"trailer_youtube_url":media.trailer_youtube_url}

def _safe_search_query(value:str)->str:
    value=re.sub(r"[\x00-\x1f]+"," ",value or "")
    value=re.sub(r"\s+"," ",value).strip()[:120]
    return value

def _moods_for_genres(genres):
    names={g.get("name","") for g in genres}; moods=[]
    if names & {"Comedy","Animation","Family"}:moods.append("Happy")
    if names & {"Romance"}:moods.append("Romantic")
    if names & {"Thriller","Horror","Action","Mystery"}:moods.append("Thrilled")
    if names & {"Drama"}:moods.append("Sad/Cathartic")
    return "|".join(moods or ["Relaxed"])

def _content_rating_from_tmdb(data):
    """Return a US movie certification when TMDB provides one; blank means unknown."""
    releases=(data.get("release_dates") or {}).get("results") or []
    us=next((row for row in releases if row.get("iso_3166_1")=="US"),None)
    dates=(us or {}).get("release_dates") or []
    return next((str(item.get("certification") or "").strip().upper() for item in dates if item.get("certification")),"")

async def _import_tmdb_movie(db:Session,client,http_id:int):
    existing=db.query(Movie).filter(Movie.tmdb_id==http_id).first()
    if existing:return existing
    r=await client.get(f"https://api.themoviedb.org/3/movie/{http_id}",params={"api_key":settings.tmdb_api_key,"language":"en-US","append_to_response":"credits,keywords,release_dates"})
    if r.status_code!=200:return None
    data=r.json(); runtime=int(data.get("runtime") or 0)
    if not data.get("title") or not runtime:return None
    credits=data.get("credits") or {};crew=credits.get("crew") or [];cast=credits.get("cast") or []
    directors=[x.get("name") for x in crew if x.get("job")=="Director" and x.get("name")]
    kw=(data.get("keywords") or {}).get("keywords") or []
    movie=Movie(title=data.get("title"),year=int((data.get("release_date") or "0000")[:4] or 0),genres="|".join(g.get("name","") for g in data.get("genres",[]) if g.get("name")),runtime=runtime,overview=data.get("overview") or "No overview is currently available.",rating=float(data.get("vote_average") or 0),language=(data.get("original_language") or "").upper(),studio=((data.get("production_companies") or [{}])[0].get("name") or "Independent"),director=directors[0] if directors else "",cast="|".join(x.get("name") for x in cast[:8] if x.get("name")),moods=_moods_for_genres(data.get("genres",[])),pace="Moderate",keywords="|".join(x.get("name") for x in kw[:20] if x.get("name")),tmdb_id=http_id,poster_url=("https://image.tmdb.org/t/p/w500"+data["poster_path"]) if data.get("poster_path") else "",backdrop_url=("https://image.tmdb.org/t/p/original"+data["backdrop_path"]) if data.get("backdrop_path") else "",content_rating=_content_rating_from_tmdb(data))
    db.add(movie);db.flush()
    producer_names=[]
    for person in crew:
        if person.get("job") in {"Producer","Executive Producer","Co-Producer"} and person.get("name") and person.get("name") not in producer_names:
            producer_names.append(person.get("name"))
    for name in producer_names[:12]:
        db.add(MovieProducer(movie_id=movie.id,producer_name=name,source="tmdb"))
    return movie

@router.get("/catalogue/search")
async def search_movies(q:str=Query(...,min_length=2,max_length=120),limit:int=Query(24,ge=1,le=50),db:Session=Depends(get_db),user=Depends(get_optional_user)):
    q=_safe_search_query(q);p=f"%{q}%"
    local=db.query(Movie).filter(or_(Movie.title.ilike(p),Movie.overview.ilike(p),Movie.keywords.ilike(p),Movie.director.ilike(p))).order_by(Movie.rating.desc()).limit(limit).all()
    if len(local)>=min(8,limit) or not settings.tmdb_api_key:
        return {"results":[movie_dict(m) for m in local if _visible_to_active_profile(db,user,m)],"external_search":False,"tmdb_configured":bool(settings.tmdb_api_key)}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r=await client.get("https://api.themoviedb.org/3/search/movie",params={"api_key":settings.tmdb_api_key,"query":q,"include_adult":"false","language":"en-US","page":1})
            if r.status_code==200:
                for item in r.json().get("results",[])[:max(10,limit)]:
                    tid=item.get("id")
                    if tid: await _import_tmdb_movie(db,client,int(tid))
                db.commit()
                local=db.query(Movie).filter(or_(Movie.title.ilike(p),Movie.overview.ilike(p),Movie.keywords.ilike(p),Movie.director.ilike(p))).order_by(Movie.rating.desc()).limit(limit).all()
                return {"results":[movie_dict(m) for m in local if _visible_to_active_profile(db,user,m)],"external_search":True,"tmdb_configured":True}
    except Exception:
        db.rollback()
    return {"results":[movie_dict(m) for m in local if _visible_to_active_profile(db,user,m)],"external_search":False,"tmdb_configured":bool(settings.tmdb_api_key)}
