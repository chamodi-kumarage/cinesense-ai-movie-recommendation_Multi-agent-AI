import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import Movie,User,AdminAccount,MovieMedia
from ..security import hash_password,encrypt_text
from ..config import get_settings
settings=get_settings()

def _list(v):
    return '|'.join(v or [])

def seed_movies(db:Session):
    """Synchronise the bundled catalogue into the DB without deleting user/admin data.
    Existing rows are matched by TMDB id first, then title+year. Admin-uploaded media URLs
    are preserved when the seed has blank media fields. This allows upgrades from the old
    36-film DB to the new 360-film catalogue on the next startup.
    """
    path=Path(__file__).resolve().parents[2]/'data'/'movies_seed.json'
    items=json.loads(path.read_text(encoding='utf-8'))
    for raw in items:
        item=dict(raw)
        tmdb_id=item.get('tmdb_id')
        movie=db.query(Movie).filter(Movie.tmdb_id==tmdb_id).first() if tmdb_id else None
        if not movie:
            movie=db.query(Movie).filter(Movie.title==item.get('title'),Movie.year==item.get('year')).first()
        values={
            'title':item.get('title','').strip(),'year':int(item.get('year') or 0),
            'genres':_list(item.get('genres')),'runtime':int(item.get('runtime') or 0),
            'overview':item.get('overview') or 'No overview is currently available.',
            'rating':float(item.get('rating') or 0),'language':item.get('language') or '',
            'studio':item.get('studio') or '','director':item.get('director') or '',
            'cast':_list(item.get('cast')),'moods':_list(item.get('moods')),
            'pace':item.get('pace') or 'Moderate','keywords':_list(item.get('keywords')),
            'tmdb_id':tmdb_id,
        }
        if not movie:
            values['poster_url']=item.get('poster_url') or ''
            values['backdrop_url']=item.get('backdrop_url') or ''
            db.add(Movie(**values))
        else:
            for key,val in values.items(): setattr(movie,key,val)
            # Only adopt seeded artwork when it is non-empty; keep admin uploads/TMDB artwork.
            if item.get('poster_url') and not (movie.poster_url or '').startswith(settings.public_api_url.rstrip('/')+'/media/'):
                movie.poster_url=item['poster_url']
            if item.get('backdrop_url') and not (movie.backdrop_url or '').startswith(settings.public_api_url.rstrip('/')+'/media/'):
                movie.backdrop_url=item['backdrop_url']
    db.commit()

def seed_demo_user(db:Session):
    if not settings.enable_demo_account:return
    if db.query(User).filter(User.email=='demo@cinesense.ai').first():return
    db.add(User(email='demo@cinesense.ai',password_hash=hash_password('Demo123!'),display_name_enc=encrypt_text('Demo Viewer'),consented=True,plan='premium'));db.commit()

def seed_admin_user(db:Session):
    email=settings.admin_email.strip().lower()
    if not email or not settings.admin_password:return
    user=db.query(User).filter(User.email==email).first()
    if not user:
        user=User(email=email,password_hash=hash_password(settings.admin_password),display_name_enc=encrypt_text('CineSense Admin'),consented=True,plan='premium');db.add(user);db.commit();db.refresh(user)
    if not db.get(AdminAccount,user.id):db.add(AdminAccount(user_id=user.id,role='admin',active=True));db.commit()
    if not db.query(MovieMedia).filter(MovieMedia.featured==True).first():
        movie=db.query(Movie).filter(Movie.title.ilike('%Inception%')).first() or db.query(Movie).first()
        if movie:db.add(MovieMedia(movie_id=movie.id,trailer_youtube_url='https://www.youtube.com/watch?v=YoHD9XEInc0',featured=True));db.commit()
