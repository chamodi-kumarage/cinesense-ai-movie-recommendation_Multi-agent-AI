from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from ..db import get_db
from ..models import Movie,RecommendationFeedback,ProfileWatchEvent,MovieMedia,MovieProducer
from ..schemas import WatchEventRequest,FeedbackRequest,SummarizeRequest
from ..dependencies import get_current_user
from ..security import encrypt_text
from ..services.profiles import active_profile_id
from ..agents.retrieval import movie_dict
from ..agents.orchestrator import orchestrator
from ..services.llm import llm_service
from ..config import get_settings
import httpx, re
router=APIRouter(prefix="/api",tags=["movies"]);settings=get_settings()

@router.get("/movies")
def list_movies(q:str|None=Query(None,max_length=120),genre:str|None=Query(None,max_length=50),mood:str|None=Query(None,max_length=50),limit:int=Query(360,ge=1,le=500),db:Session=Depends(get_db)):
    query=db.query(Movie)
    if q:
        p=f"%{q}%";query=query.filter(or_(Movie.title.ilike(p),Movie.overview.ilike(p),Movie.keywords.ilike(p)))
    if genre:query=query.filter(Movie.genres.ilike(f"%{genre}%"))
    if mood:query=query.filter(Movie.moods.ilike(f"%{mood}%"))
    return [movie_dict(m) for m in query.order_by(Movie.rating.desc()).limit(limit).all()]

@router.get("/movies/{movie_id}")
def get_movie(movie_id:int,db:Session=Depends(get_db)):
    m=db.get(Movie,movie_id)
    if not m:raise HTTPException(404,"Movie not found.")
    return movie_dict(m)

@router.post("/movies/summarize")
async def summarize(data:SummarizeRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    m=db.get(Movie,data.movie_id)
    if not m:raise HTTPException(404,"Movie not found.")
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

def _genre_filter(query,genre:str):
    """Match a pipe-delimited genre exactly instead of matching substrings."""
    value=_safe_search_query(genre).casefold()
    column=func.lower(Movie.genres)
    return query.filter(or_(
        column==value,
        column.startswith(f"{value}|",autoescape=True),
        column.endswith(f"|{value}",autoescape=True),
        column.contains(f"|{value}|",autoescape=True),
    ))

def _search_rank(movie:Movie,value:str):
    """Put useful title/credit matches ahead of incidental overview matches."""
    needle=" ".join((value or "").casefold().split())
    terms=re.findall(r"[\w']+",needle,flags=re.UNICODE)
    title=" ".join((movie.title or "").casefold().split())
    title_without_article=re.sub(r"^(?:the|a|an)\s+","",title)
    title_terms=re.findall(r"[\w']+",title,flags=re.UNICODE)
    director=(movie.director or "").casefold()
    cast=(movie.cast or "").casefold()
    genres=[x.strip().casefold() for x in (movie.genres or "").split("|") if x.strip()]
    moods=[x.strip().casefold() for x in (movie.moods or "").split("|") if x.strip()]
    keywords=[x.strip().casefold() for x in (movie.keywords or "").split("|") if x.strip()]
    overview=(movie.overview or "").casefold()
    studio=(movie.studio or "").casefold()
    language=(movie.language or "").casefold()
    score=0

    if needle:
        if title==needle:score+=12000
        elif title_without_article==needle:score+=11000
        elif title.startswith(needle):score+=8500
        elif title_without_article.startswith(needle):score+=8200
        elif re.search(rf"\b{re.escape(needle)}\b",title):score+=7000
        elif needle in title:score+=5500

        if director==needle:score+=5000
        elif director.startswith(needle):score+=3500
        elif needle in director:score+=2400
        if any(name.strip()==needle for name in cast.split("|")):score+=4200
        elif needle in cast:score+=1900
        if needle in genres:score+=3600
        if needle in moods:score+=3200
        if needle in keywords:score+=2600
        if studio==needle:score+=2400
        elif needle in studio:score+=1200
        if language==needle:score+=1800
        if needle.isdigit() and len(needle)==4 and int(needle)==movie.year:score+=4500

    matched_title_terms=0
    searchable_credits=" ".join([director,cast,studio])
    searchable_tags=" ".join(genres+moods+keywords)
    for term in terms:
        if term in title_terms:
            score+=650
            matched_title_terms+=1
        elif any(word.startswith(term) for word in title_terms):score+=350
        if term in searchable_credits:score+=180
        if term in searchable_tags:score+=140
        if term in overview:score+=20
    if terms and matched_title_terms==len(terms):score+=1000
    return (score,float(movie.rating or 0),int(movie.year or 0))

def _local_catalogue_search(db:Session,q:str,genre:str,limit:int):
    query=db.query(Movie)
    if q:
        fields=(Movie.title,Movie.overview,Movie.keywords,Movie.director,Movie.cast,Movie.studio,Movie.genres,Movie.moods,Movie.language)
        clauses=[field.contains(q,autoescape=True) for field in fields]
        if q.isdigit() and len(q)==4:clauses.append(Movie.year==int(q))
        query=query.filter(or_(*clauses))
    if genre:query=_genre_filter(query,genre)
    rows=query.all()
    if q:rows.sort(key=lambda movie:_search_rank(movie,q),reverse=True)
    else:rows.sort(key=lambda movie:(float(movie.rating or 0),int(movie.year or 0)),reverse=True)
    return rows[:limit]

def _moods_for_genres(genres):
    names={g.get("name","") for g in genres}; moods=[]
    if names & {"Comedy","Animation","Family"}:moods.append("Happy")
    if names & {"Romance"}:moods.append("Romantic")
    if names & {"Thriller","Horror","Action","Mystery"}:moods.append("Thrilled")
    if names & {"Drama"}:moods.append("Sad/Cathartic")
    return "|".join(moods or ["Relaxed"])

async def _import_tmdb_movie(db:Session,client,http_id:int):
    existing=db.query(Movie).filter(Movie.tmdb_id==http_id).first()
    if existing:return existing
    r=await client.get(f"https://api.themoviedb.org/3/movie/{http_id}",params={"api_key":settings.tmdb_api_key,"language":"en-US","append_to_response":"credits,keywords"})
    if r.status_code!=200:return None
    data=r.json(); runtime=int(data.get("runtime") or 0)
    if not data.get("title") or not runtime:return None
    credits=data.get("credits") or {};crew=credits.get("crew") or [];cast=credits.get("cast") or []
    directors=[x.get("name") for x in crew if x.get("job")=="Director" and x.get("name")]
    kw=(data.get("keywords") or {}).get("keywords") or []
    movie=Movie(title=data.get("title"),year=int((data.get("release_date") or "0000")[:4] or 0),genres="|".join(g.get("name","") for g in data.get("genres",[]) if g.get("name")),runtime=runtime,overview=data.get("overview") or "No overview is currently available.",rating=float(data.get("vote_average") or 0),language=(data.get("original_language") or "").upper(),studio=((data.get("production_companies") or [{}])[0].get("name") or "Independent"),director=directors[0] if directors else "",cast="|".join(x.get("name") for x in cast[:8] if x.get("name")),moods=_moods_for_genres(data.get("genres",[])),pace="Moderate",keywords="|".join(x.get("name") for x in kw[:20] if x.get("name")),tmdb_id=http_id,poster_url=("https://image.tmdb.org/t/p/w500"+data["poster_path"]) if data.get("poster_path") else "",backdrop_url=("https://image.tmdb.org/t/p/original"+data["backdrop_path"]) if data.get("backdrop_path") else "")
    db.add(movie);db.flush()
    producer_names=[]
    for person in crew:
        if person.get("job") in {"Producer","Executive Producer","Co-Producer"} and person.get("name") and person.get("name") not in producer_names:
            producer_names.append(person.get("name"))
    for name in producer_names[:12]:
        db.add(MovieProducer(movie_id=movie.id,producer_name=name,source="tmdb"))
    return movie

@router.get("/catalogue/search")
async def search_movies(q:str|None=Query(None,max_length=120),genre:str|None=Query(None,max_length=50),limit:int=Query(24,ge=1,le=50),db:Session=Depends(get_db)):
    q=_safe_search_query(q or "");genre=_safe_search_query(genre or "")
    if q and len(q)<2:raise HTTPException(422,"Type at least 2 characters to search.")
    if not q and not genre:raise HTTPException(422,"Enter a search term or choose a genre.")
    local=_local_catalogue_search(db,q,genre,limit)
    strong_local=bool(q and local and _search_rank(local[0],q)[0]>=1000)
    if strong_local or len(local)>=min(8,limit) or not settings.tmdb_api_key:
        return {"results":[movie_dict(m) for m in local],"total":len(local),"external_search":False,"tmdb_configured":bool(settings.tmdb_api_key)}
    if not q:
        return {"results":[movie_dict(m) for m in local],"total":len(local),"external_search":False,"tmdb_configured":bool(settings.tmdb_api_key)}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r=await client.get("https://api.themoviedb.org/3/search/movie",params={"api_key":settings.tmdb_api_key,"query":q,"include_adult":"false","language":"en-US","page":1})
            if r.status_code==200:
                for item in r.json().get("results",[])[:max(10,limit)]:
                    tid=item.get("id")
                    if tid: await _import_tmdb_movie(db,client,int(tid))
                db.commit()
                local=_local_catalogue_search(db,q,genre,limit)
                return {"results":[movie_dict(m) for m in local],"total":len(local),"external_search":True,"tmdb_configured":True}
    except Exception:
        db.rollback()
    return {"results":[movie_dict(m) for m in local],"total":len(local),"external_search":False,"tmdb_configured":bool(settings.tmdb_api_key)}
