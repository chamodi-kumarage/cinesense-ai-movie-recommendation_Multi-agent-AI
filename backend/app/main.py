from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .db import Base,engine,SessionLocal
from .config import get_settings
from .services.seed import seed_movies,seed_demo_user,seed_admin_user
from .models import MonitoringEvent
from .routers import auth,movies,ai,audit,family,commerce,planner,admin,security_assessment,similarity
settings=get_settings()

@asynccontextmanager
async def lifespan(app:FastAPI):
    if settings.environment=="production":
        if settings.secret_key=="change-this-before-public-deployment":
            raise RuntimeError("SECRET_KEY must be changed before production deployment.")
        if settings.admin_password=="CineSenseAdmin!2026":
            raise RuntimeError("ADMIN_PASSWORD must be changed before production deployment.")
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try:seed_movies(db);seed_demo_user(db);seed_admin_user(db)
    finally:db.close()
    yield

app=FastAPI(title=settings.app_name,version="1.0.0",
            description="Six-agent mood-aware movie discovery and companion platform.",lifespan=lifespan)
allowed_origins = list(dict.fromkeys([
    settings.frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router);app.include_router(movies.router);app.include_router(ai.router);app.include_router(audit.router);app.include_router(family.router);app.include_router(commerce.router);app.include_router(planner.router);app.include_router(admin.router);app.include_router(security_assessment.router);app.include_router(similarity.router)
from pathlib import Path
UPLOAD_DIR=Path(__file__).resolve().parents[1]/"uploads"
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
app.mount("/media",StaticFiles(directory=str(UPLOAD_DIR)),name="media")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method in {"POST","PUT","PATCH"}:
        length=request.headers.get("content-length")
        if length and int(length)>12*1024*1024:
            return JSONResponse({"detail":"Request body is too large."},status_code=413)
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="SAMEORIGIN"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]="camera=(), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"]="default-src 'self'; img-src 'self' data: https://image.tmdb.org http://localhost:8000 http://127.0.0.1:8000; media-src 'self'; frame-src https://www.youtube.com https://youtube.com; connect-src 'self' http://localhost:8000 http://127.0.0.1:8000; style-src 'self' 'unsafe-inline'; script-src 'self'"
    if settings.environment=="production":
        response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    return response

@app.middleware("http")
async def production_monitoring(request: Request, call_next):
    import time, json
    started=time.perf_counter()
    try:
        response=await call_next(request)
        status=response.status_code
        return response
    except Exception:
        status=500
        raise
    finally:
        if settings.enable_monitoring and request.url.path.startswith("/api"):
            try:
                db=SessionLocal(); elapsed=round((time.perf_counter()-started)*1000,2)
                level="error" if status>=500 else ("warning" if status>=400 else "info")
                detail=json.dumps({"method":request.method,"path":request.url.path,"status":status,"duration_ms":elapsed})
                db.add(MonitoringEvent(level=level,event_type="http_request",detail_safe=detail));db.commit();db.close()
            except Exception:
                pass

@app.get("/api/health")
def health():return {"ok":True,"service":settings.app_name,"agents":6,"topology":"hub-and-spoke","llm_provider":settings.llm_provider}
