import json
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User,SavedPlan
from ..schemas import ChatRequest,CompareRequest,PlanRequest,SavePlanRequest
from ..dependencies import require_consent,get_current_user
from ..agents.orchestrator import orchestrator
router=APIRouter(prefix="/api",tags=["ai"])

@router.post("/chat")
async def chat(data:ChatRequest,db:Session=Depends(get_db),user:User=Depends(require_consent)):
    try:return await orchestrator.chat(db,user,data.message,data.mood_override,data.dismissed_moods)
    except ValueError as e:raise HTTPException(429,str(e))

@router.post("/compare")
async def compare(data:CompareRequest,db:Session=Depends(get_db),user:User=Depends(require_consent)):
    try:return await orchestrator.compare_movies(db,user,data.movie_ids,data.mood,data.user_note,data.mode,data.free_minutes,data.scenario)
    except ValueError as e:raise HTTPException(429 if "10 AI" in str(e) else 400,str(e))

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
