import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User,SavedPlan,Movie,ProfilePreference
from ..schemas import ChatRequest,CompareRequest,PlanRequest,SavePlanRequest,TournamentSignalRequest
from ..dependencies import require_consent,get_current_user
from ..agents.orchestrator import orchestrator
from ..services.profiles import active_profile_id
router=APIRouter(prefix="/api",tags=["ai"])

@router.post("/chat")
async def chat(data:ChatRequest,db:Session=Depends(get_db),user:User=Depends(require_consent)):
    try:return await orchestrator.chat(db,user,data.message,data.mood_override,data.dismissed_moods)
    except ValueError as e:raise HTTPException(429,str(e))

@router.post("/compare")
async def compare(data:CompareRequest,db:Session=Depends(get_db),user:User=Depends(require_consent)):
    try:return await orchestrator.compare_movies(db,user,data.movie_ids,data.mood,data.user_note,data.mode,data.free_minutes,data.scenario)
    except ValueError as e:raise HTTPException(429 if "10 AI" in str(e) else 400,str(e))

@router.post("/compare/tournament-signal")
def tournament_signal(data:TournamentSignalRequest,db:Session=Depends(get_db),user:User=Depends(require_consent)):
    winner=db.get(Movie,data.winner_movie_id); loser=db.get(Movie,data.loser_movie_id)
    if not winner or not loser: raise HTTPException(404,"One of the tournament movies no longer exists.")
    profile_id=active_profile_id(db,user)
    pref=db.get(ProfilePreference,profile_id)
    if not pref:
        pref=ProfilePreference(profile_id=profile_id,user_id=user.id);db.add(pref)
    def load(value):
        try:return json.loads(value or "[]")
        except Exception:return []
    genres=load(pref.preferred_genres_json);moods=load(pref.preferred_moods_json)
    reason=data.reason.lower()
    winner_genres=[g for g in (winner.genres or "").split("|") if g]
    winner_moods=[m for m in (winner.moods or "").split("|") if m]
    if "genre" in reason or "prefer" in reason:
        for g in winner_genres[:2]:
            if g not in genres:genres.append(g)
    if "mood" in reason:
        for m in winner_moods[:2]:
            if m not in moods:moods.append(m)
    pref.preferred_genres_json=json.dumps(genres[:8],ensure_ascii=False)
    pref.preferred_moods_json=json.dumps(moods[:6],ensure_ascii=False)
    db.commit()
    return {"ok":True,"profile_id":profile_id,"message":"Your tournament choice was saved as a lightweight preference signal."}

@router.post("/plan")
def plan(data:PlanRequest,db:Session=Depends(get_db),user:User=Depends(require_consent)):
    try:return orchestrator.build_plan(db,user,data.genres,data.mood,data.free_minutes,data.finish_by,data.query,data.buffer_minutes)
    except ValueError as e:raise HTTPException(429,str(e))

@router.post("/plans/save")
def save_plan(data:SavePlanRequest,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    if user.plan not in {"premium","family"}:raise HTTPException(403,"Saved watch plans are a Premium/Family feature.")
    row=SavedPlan(user_id=user.id,title=data.title,payload_json=json.dumps(data.plan,ensure_ascii=False));db.add(row);db.commit();db.refresh(row)
    return {"id":row.id,"title":row.title,"created_at":row.created_at}

@router.get("/plans")
def plans(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    rows=db.query(SavedPlan).filter(SavedPlan.user_id==user.id).order_by(SavedPlan.created_at.desc()).all()
    return [{"id":r.id,"title":r.title,"plan":json.loads(r.payload_json),"created_at":r.created_at} for r in rows]
