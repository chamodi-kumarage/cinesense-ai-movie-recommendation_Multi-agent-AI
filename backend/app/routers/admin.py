import asyncio, json, re, secrets, httpx
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Movie, MovieMedia, User, AdminAccount, MonitoringEvent, SecurityEvent, Subscription, Profile
from ..dependencies import require_admin
from ..config import get_settings
from ..security import decrypt_text
from ..agents.retrieval import movie_dict

router=APIRouter(prefix="/api/admin",tags=["admin"]); settings=get_settings()
UPLOAD_ROOT=Path(__file__).resolve().parents[2]/"uploads"
ALLOWED_TYPES={"image/jpeg":".jpg","image/png":".png","image/webp":".webp"}

class MovieUpdate(BaseModel):
    title:str|None=Field(None,max_length=255); year:int|None=None; genres:list[str]|None=None
    runtime:int|None=None; overview:str|None=Field(None,max_length=5000); rating:float|None=None
    language:str|None=Field(None,max_length=50); studio:str|None=Field(None,max_length=120)
    director:str|None=Field(None,max_length=120); cast:list[str]|None=None; moods:list[str]|None=None
    pace:str|None=Field(None,max_length=30); keywords:list[str]|None=None
    content_rating:str|None=Field(None,max_length=16)
    trailer_youtube_url:str|None=Field(None,max_length=500); featured:bool|None=None


def _youtube_embed(url:str)->str:
    url=(url or '').strip()
    if not url:return ''
    parsed=urlparse(url)
    host=parsed.netloc.lower().replace('www.','')
    vid=''
    if host in {'youtu.be'}: vid=parsed.path.strip('/').split('/')[0]
    elif host in {'youtube.com','m.youtube.com'}:
        if parsed.path=='/watch': vid=(parse_qs(parsed.query).get('v') or [''])[0]
        elif parsed.path.startswith('/embed/'): vid=parsed.path.split('/embed/',1)[1].split('/')[0]
        elif parsed.path.startswith('/shorts/'): vid=parsed.path.split('/shorts/',1)[1].split('/')[0]
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}',vid or ''):
        raise HTTPException(400,'Enter a valid YouTube video URL.')
    return f'https://www.youtube.com/embed/{vid}'

@router.get('/overview')
def overview(db:Session=Depends(get_db),admin=Depends(require_admin)):
    return {
        'users':db.query(User).count(),'admins':db.query(AdminAccount).filter(AdminAccount.active==True).count(),
        'movies':db.query(Movie).count(),'family_profiles':db.query(Profile).count(),
        'paid_subscriptions':db.query(Subscription).filter(Subscription.status.in_(['active','trialing'])).count(),
        'tmdb_configured':bool(settings.tmdb_api_key),'environment':settings.environment,
        'uploads':sum(1 for p in UPLOAD_ROOT.rglob('*') if p.is_file()) if UPLOAD_ROOT.exists() else 0,
    }

@router.get('/movies')
def movies(q:str='',limit:int=80,db:Session=Depends(get_db),admin=Depends(require_admin)):
    query=db.query(Movie)
    if q: query=query.filter(Movie.title.ilike(f'%{q[:100]}%'))
    rows=query.order_by(Movie.rating.desc()).limit(min(max(limit,1),250)).all(); out=[]
    for m in rows:
        d=movie_dict(m); media=db.get(MovieMedia,m.id)
        d.update({'trailer_youtube_url':media.trailer_youtube_url if media else '', 'featured':bool(media and media.featured)})
        out.append(d)
    return out

@router.put('/movies/{movie_id}')
def update_movie(movie_id:int,data:MovieUpdate,db:Session=Depends(get_db),admin=Depends(require_admin)):
    m=db.get(Movie,movie_id)
    if not m: raise HTTPException(404,'Movie not found.')
    scalar=['title','year','runtime','overview','rating','language','studio','director','pace','content_rating']
    for field in scalar:
        value=getattr(data,field)
        if value is not None:setattr(m,field,value)
    for field in ['genres','cast','moods','keywords']:
        value=getattr(data,field)
        if value is not None:setattr(m,field,'|'.join(x.strip() for x in value if x.strip()))
    media=db.get(MovieMedia,movie_id) or MovieMedia(movie_id=movie_id)
    if data.trailer_youtube_url is not None: media.trailer_youtube_url=_youtube_embed(data.trailer_youtube_url) if data.trailer_youtube_url else ''
    if data.featured is not None:
        if data.featured: db.query(MovieMedia).update({MovieMedia.featured:False})
        media.featured=data.featured
    db.add(media);db.add(SecurityEvent(user_id=admin.id,category='admin_change',severity='info',detail_safe=f'updated_movie:{movie_id}'));db.commit()
    return {'ok':True,'movie':movie_dict(m),'trailer_youtube_url':media.trailer_youtube_url,'featured':media.featured}

@router.post('/movies/{movie_id}/image')
async def upload_image(movie_id:int,request:Request,kind:str='poster',db:Session=Depends(get_db),admin=Depends(require_admin)):
    m=db.get(Movie,movie_id)
    if not m:raise HTTPException(404,'Movie not found.')
    if kind not in {'poster','backdrop'}:raise HTTPException(400,'kind must be poster or backdrop.')
    content_type=(request.headers.get('content-type') or '').split(';')[0].strip().lower()
    if content_type not in ALLOWED_TYPES:raise HTTPException(400,'Only JPG, PNG and WebP images are allowed.')
    data=await request.body()
    if len(data)>settings.max_upload_mb*1024*1024:raise HTTPException(413,f'Image must be {settings.max_upload_mb} MB or smaller.')
    if not data:raise HTTPException(400,'Image file is empty.')
    valid=(data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n') or (data.startswith(b'RIFF') and b'WEBP' in data[:16]))
    if not valid:raise HTTPException(400,'The uploaded file is not a valid supported image.')
    ext=ALLOWED_TYPES[content_type];folder=UPLOAD_ROOT/('posters' if kind=='poster' else 'backdrops');folder.mkdir(parents=True,exist_ok=True)
    name=f'{movie_id}_{secrets.token_hex(8)}{ext}';path=folder/name;path.write_bytes(data)
    url=f"{settings.public_api_url.rstrip('/')}/media/{folder.name}/{name}"
    if kind=='poster':m.poster_url=url
    else:m.backdrop_url=url
    db.add(SecurityEvent(user_id=admin.id,category='admin_upload',severity='info',detail_safe=f'{kind}:{movie_id}:{len(data)}bytes'));db.commit()
    return {'ok':True,'url':url,'movie':movie_dict(m)}

@router.post('/catalogue/import-popular')
async def import_popular(pages:int=3,db:Session=Depends(get_db),admin=Depends(require_admin)):
    if not settings.tmdb_api_key:raise HTTPException(400,'TMDB_API_KEY is not configured. Add it to backend/.env first.')
    pages=min(max(pages,1),20);added=0
    import httpx
    from .movies import _import_tmdb_movie
    async with httpx.AsyncClient(timeout=12) as client:
        for page in range(1,pages+1):
            r=await client.get('https://api.themoviedb.org/3/movie/popular',params={'api_key':settings.tmdb_api_key,'language':'en-US','page':page})
            if r.status_code!=200:continue
            for item in r.json().get('results',[]):
                tid=item.get('id')
                if not tid or db.query(Movie).filter(Movie.tmdb_id==tid).first():continue
                if await _import_tmdb_movie(db,client,int(tid)):added+=1
    db.add(SecurityEvent(user_id=admin.id,category='catalogue_sync',severity='info',detail_safe=f'tmdb_popular_added:{added}'));db.commit()
    return {'ok':True,'added':added,'total':db.query(Movie).count()}

@router.post('/catalogue/sync-tmdb-images')
async def sync_tmdb_images(limit:int=Query(360,ge=1,le=360),db:Session=Depends(get_db),admin=Depends(require_admin)):
    """Fetch missing poster/backdrop paths for existing TMDB-linked catalogue movies."""
    if not settings.tmdb_api_key:
        raise HTTPException(400,'TMDB_API_KEY is not configured. Add it to backend/.env first.')
    movies=(db.query(Movie).filter(Movie.tmdb_id.is_not(None)).filter(
        (Movie.poster_url.is_(None)) | (Movie.poster_url=='') |
        (Movie.backdrop_url.is_(None)) | (Movie.backdrop_url=='') |
        (Movie.content_rating.is_(None)) | (Movie.content_rating=='')
    ).order_by(Movie.rating.desc()).limit(limit).all())
    semaphore=asyncio.Semaphore(6)

    async def fetch_artwork(client,movie):
        async with semaphore:
            try:
                response=await client.get(
                    f'https://api.themoviedb.org/3/movie/{movie.tmdb_id}',
                    params={'api_key':settings.tmdb_api_key,'language':'en-US','append_to_response':'release_dates'},
                )
                if response.status_code!=200:
                    return movie.id,None,None
                data=response.json()
                releases=(data.get('release_dates') or {}).get('results') or []
                us=next((row for row in releases if row.get('iso_3166_1')=='US'),None)
                dates=(us or {}).get('release_dates') or []
                certification=next((str(item.get('certification') or '').strip().upper() for item in dates if item.get('certification')),'')
                return movie.id,data.get('poster_path'),data.get('backdrop_path'),certification
            except Exception:
                return movie.id,None,None,''

    async with httpx.AsyncClient(timeout=20) as client:
        results=await asyncio.gather(*(fetch_artwork(client,movie) for movie in movies))
    by_id={movie.id:movie for movie in movies}
    posters_updated=0;backdrops_updated=0
    ratings_updated=0
    for movie_id,poster_path,backdrop_path,certification in results:
        movie=by_id[movie_id]
        if poster_path and not movie.poster_url:
            movie.poster_url='https://image.tmdb.org/t/p/w500'+poster_path
            posters_updated+=1
        if backdrop_path and not movie.backdrop_url:
            movie.backdrop_url='https://image.tmdb.org/t/p/original'+backdrop_path
            backdrops_updated+=1
        if certification and not movie.content_rating:
            movie.content_rating=certification
            ratings_updated+=1
    db.add(SecurityEvent(user_id=admin.id,category='catalogue_sync',severity='info',detail_safe=f'tmdb_images:checked={len(movies)}:posters={posters_updated}:backdrops={backdrops_updated}'))
    db.commit()
    return {'ok':True,'checked':len(movies),'posters_updated':posters_updated,'backdrops_updated':backdrops_updated,'ratings_updated':ratings_updated}

@router.get('/hero')
def hero(db:Session=Depends(get_db),admin=Depends(require_admin)):
    media=db.query(MovieMedia).filter(MovieMedia.featured==True).first()
    if not media:return {'featured':None}
    movie=db.get(Movie,media.movie_id)
    return {'featured':movie_dict(movie) if movie else None,'trailer_youtube_url':media.trailer_youtube_url}

@router.get('/users')
def users(limit:int=100,db:Session=Depends(get_db),admin=Depends(require_admin)):
    rows=db.query(User).order_by(User.created_at.desc()).limit(min(max(limit,1),250)).all()
    admins={a.user_id for a in db.query(AdminAccount).filter(AdminAccount.active==True).all()}
    return [{'id':u.id,'email':u.email,'display_name':decrypt_text(u.display_name_enc),'plan':u.plan,'consented':u.consented,'is_admin':u.id in admins,'created_at':u.created_at} for u in rows]

@router.get('/security-events')
def security_events(limit:int=100,db:Session=Depends(get_db),admin=Depends(require_admin)):
    rows=db.query(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(min(max(limit,1),300)).all()
    return [{'category':r.category,'severity':r.severity,'detail':r.detail_safe,'created_at':r.created_at} for r in rows]

@router.post('/catalogue/enrich-producers')
async def enrich_producers(limit:int=Query(60,ge=1,le=360),db:Session=Depends(get_db),admin=Depends(require_admin)):
    """Fetch verified producer credits for existing TMDB-linked catalogue movies."""
    if not settings.tmdb_api_key:raise HTTPException(400,'TMDB_API_KEY is not configured. Add it to backend/.env first.')
    from ..models import MovieProducer
    movies=db.query(Movie).filter(Movie.tmdb_id.is_not(None)).order_by(Movie.rating.desc()).limit(limit).all()
    updated=0
    async with httpx.AsyncClient(timeout=12) as client:
        for movie in movies:
            try:
                r=await client.get(f'https://api.themoviedb.org/3/movie/{movie.tmdb_id}/credits',params={'api_key':settings.tmdb_api_key,'language':'en-US'})
                if r.status_code!=200:continue
                crew=r.json().get('crew') or []
                names=[]
                for person in crew:
                    if person.get('job') in {'Producer','Executive Producer','Co-Producer'} and person.get('name') and person.get('name') not in names:names.append(person.get('name'))
                db.query(MovieProducer).filter(MovieProducer.movie_id==movie.id).delete(synchronize_session=False)
                for name in names[:12]:db.add(MovieProducer(movie_id=movie.id,producer_name=name,source='tmdb'))
                if names:updated+=1
            except Exception:
                continue
    db.commit()
    return {'ok':True,'movies_checked':len(movies),'movies_with_verified_producers':updated,'source':'TMDB credits'}
