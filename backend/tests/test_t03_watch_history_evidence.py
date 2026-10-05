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


def test_t03_watch_history_and_rating_isolation():
    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_id = beta_id = None
        try:
            alpha_id = _register_family_account(alpha, "alpha")
            beta_id = _register_family_account(beta, "beta")

            profiles_a = alpha.get("/api/family/profiles")
            assert profiles_a.status_code == 200
            profile_a = profiles_a.json()[0]["id"]
            create_profile = alpha.post("/api/family/profiles", json={"name": "Synthetic Profile B"})
            assert create_profile.status_code == 200
            profile_b = create_profile.json()["id"]
            assert profile_a != profile_b

            movie_id = alpha.get("/api/movies").json()[0]["id"]
            assert alpha.post("/api/family/profiles/switch", json={"profile_id": profile_a}).status_code == 200
            write = alpha.post("/api/watch-events", json={"movie_id": movie_id, "rating": 4.5, "watched": True})
            assert write.status_code == 200

            history_a = alpha.get(f"/api/family/profiles/{profile_a}/history")
            assert history_a.status_code == 200
            history_b = alpha.get(f"/api/family/profiles/{profile_b}/history")
            assert history_b.status_code == 200
            foreign_history = beta.get(f"/api/family/profiles/{profile_a}/history")

            evidence = {
                "test": "T-03",
                "watch_write_status": write.status_code,
                "profile_a_history_count": len(history_a.json()),
                "profile_a_rating_present": any(row.get("rating") == 4.5 for row in history_a.json()),
                "profile_b_history_count": len(history_b.json()),
                "beta_foreign_profile_status": foreign_history.status_code,
                "result": "PASS",
            }
            assert evidence["profile_a_history_count"] >= 1
            assert evidence["profile_a_rating_present"]
            assert evidence["profile_b_history_count"] == 0
            assert foreign_history.status_code == 404
            print(json.dumps(evidence, indent=2))
        finally:
            if alpha_id is not None:
                alpha.delete("/api/account")
            if beta_id is not None:
                beta.delete("/api/account")
