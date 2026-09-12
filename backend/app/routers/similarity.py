from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import require_consent
from ..models import User
from ..schemas import SimilarityRequest
from ..agents.orchestrator import orchestrator

router=APIRouter(prefix="/api",tags=["similarity"])

@router.post("/similar")
async def find_similar(data:SimilarityRequest, db:Session=Depends(get_db), user:User=Depends(require_consent)):
    try:
        if data.year_mode=="custom" and (data.custom_year_min is None or data.custom_year_max is None or data.custom_year_min>data.custom_year_max):
            raise HTTPException(422,"Choose a valid custom release-year range.")
        return await orchestrator.find_similar(
            db,user,data.movie_id,data.modes,data.weights,data.preset,data.required_genre,
            data.year_mode,data.custom_year_min,data.custom_year_max,data.mood,data.free_minutes,data.limit
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(429 if "10 AI" in str(exc) else 400,str(exc))
