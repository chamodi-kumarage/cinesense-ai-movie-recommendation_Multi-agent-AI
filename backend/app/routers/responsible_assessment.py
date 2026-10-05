"""Student 3 assessment helpers; these do not change recommendation behaviour."""
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import require_admin
from ..models import Movie, RecommendationFeedback
from ..security import decrypt_text

router = APIRouter(prefix="/api/responsible-ai", tags=["Student 3 - Responsible AI assessment"])


class ExposureRequest(BaseModel):
    movie_ids: list[int] = Field(min_length=1, max_length=100)


def distribution(rows, attribute):
    counts = Counter((getattr(row, attribute) or "Unknown").strip() for row in rows)
    total = len(rows)
    return {key: {"count": count, "share": round(count / total, 4) if total else 0}
            for key, count in sorted(counts.items())}


@router.get("/methodology", summary="Read Student 3 assessment scope and metric definitions")
def methodology():
    return {
        "specialization": "Student 3 - Responsible AI and Bias Assessment",
        "areas": ["hallucination", "bias", "toxicity", "fairness", "transparency", "explainability", "harmful content"],
        "metric": "Total variation distance = 0.5 * sum(abs(recommendation share - catalogue share))",
        "interpretation": "0 means identical distributions; 1 means no overlap. This is a descriptive exposure metric, not proof of discrimination.",
        "limitations": ["Catalogue composition is not a fairness ground truth.", "Language and studio are movie attributes, not user protected characteristics.", "Offline results do not establish live-LLM safety.", "Small samples require human review; no automatic compliance score is assigned."],
    }


@router.get("/catalogue", summary="Measure catalogue representation without personal data")
def catalogue(db: Session = Depends(get_db)):
    rows = db.query(Movie).order_by(Movie.id).all()
    return {"total_movies": len(rows), "languages": distribution(rows, "language"),
            "studios": distribution(rows, "studio"), "limitation": "Descriptive representation only; not a fairness certification."}


@router.post("/exposure", summary="Compare a unique recommendation shortlist with catalogue representation")
def exposure(data: ExposureRequest, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if len(set(data.movie_ids)) != len(data.movie_ids):
        raise HTTPException(422, "Duplicate movie IDs would distort exposure; provide a unique shortlist.")
    all_rows = db.query(Movie).all()
    selected = [row for row in all_rows if row.id in data.movie_ids]
    if len(selected) != len(data.movie_ids):
        raise HTTPException(404, "One or more movie IDs are not in the catalogue.")
    result = {"sample_size": len(selected), "catalogue_size": len(all_rows), "dimensions": {}}
    for dimension in ("language", "studio"):
        baseline = distribution(all_rows, dimension)
        observed = distribution(selected, dimension)
        keys = sorted(set(baseline) | set(observed))
        # Compute with unrounded shares to avoid accumulated rounding error.
        a = Counter(getattr(row, dimension).strip() or "Unknown" for row in all_rows)
        b = Counter(getattr(row, dimension).strip() or "Unknown" for row in selected)
        distance = .5 * sum(abs(a[k] / len(all_rows) - b[k] / len(selected)) for k in keys)
        result["dimensions"][dimension] = {"catalogue": baseline, "recommendations": observed,
            "total_variation_distance": round(distance, 6)}
    result["interpretation"] = "Exposure difference may reflect query relevance, catalogue imbalance or ranking. Investigate matched queries before attributing bias."
    return result


@router.get("/feedback", summary="Read encrypted recommendation flags for administrator human review")
def feedback(db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(RecommendationFeedback).order_by(RecommendationFeedback.id.desc()).limit(100).all()
    return {"items": [{"id": row.id, "movie_id": row.movie_id, "reason": row.reason,
                       "details": decrypt_text(row.details_enc), "created_at": row.created_at} for row in rows],
            "limitation": "Review queue only; no claim that a flag has been resolved."}
