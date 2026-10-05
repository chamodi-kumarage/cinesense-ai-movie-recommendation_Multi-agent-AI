import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import User


def _register_family_account(client, alias):
    response = client.post("/api/auth/register", json={
        "email": f"{alias}-{uuid.uuid4().hex}@example.com",
        "password": "Synthetic123",
        "display_name": f"Synthetic {alias.title()}",
    })
    assert response.status_code == 200
    user_id = response.json()["id"]
    db = SessionLocal()
    try:
        db.query(User).filter(User.id == user_id).update({User.plan: "family"})
        db.commit()
    finally:
        db.close()
    return user_id


def test_t05_foreign_profile_resource_is_denied():
    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_id = beta_id = None
        try:
            alpha_id = _register_family_account(alpha, "t05-alpha")
            beta_id = _register_family_account(beta, "t05-beta")

            alpha_profiles = alpha.get("/api/family/profiles")
            assert alpha_profiles.status_code == 200
            alpha_profile_id = alpha_profiles.json()[0]["id"]
            movie_id = alpha.get("/api/movies").json()[0]["id"]
            write = alpha.post("/api/watch-events", json={"movie_id": movie_id, "rating": 4.0, "watched": True})
            assert write.status_code == 200

            # Beta attempts a direct-object request for Alpha's known profile ID.
            foreign = beta.get(f"/api/family/profiles/{alpha_profile_id}/history")
            own_plans = beta.get("/api/plans")
            assert own_plans.status_code == 200
            assert foreign.status_code == 404
            assert own_plans.json() == []

            evidence = {
                "test": "T-05",
                "alpha_profile_has_synthetic_history": True,
                "beta_foreign_profile_history_status": foreign.status_code,
                "beta_own_plans_status": own_plans.status_code,
                "beta_own_plan_count": len(own_plans.json()),
                "result": "PASS",
            }
            print(json.dumps(evidence, indent=2))
        finally:
            if alpha_id is not None:
                alpha.delete("/api/account")
            if beta_id is not None:
                beta.delete("/api/account")
