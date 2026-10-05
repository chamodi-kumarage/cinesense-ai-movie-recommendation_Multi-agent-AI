import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import User, ProfilePreference


def test_t04_profile_preferences_stay_with_their_profile():
    with TestClient(app) as client:
        user_id = None
        try:
            registration = client.post("/api/auth/register", json={
                "email": f"t04-{uuid.uuid4().hex}@example.com",
                "password": "Synthetic123",
                "display_name": "Synthetic Preference Tester",
            })
            assert registration.status_code == 200
            user_id = registration.json()["id"]

            db = SessionLocal()
            try:
                db.query(User).filter(User.id == user_id).update({User.plan: "family"})
                db.commit()
            finally:
                db.close()

            profiles = client.get("/api/family/profiles")
            assert profiles.status_code == 200
            profile_a = profiles.json()[0]["id"]
            created = client.post("/api/family/profiles", json={"name": "Synthetic Profile B"})
            assert created.status_code == 200
            profile_b = created.json()["id"]
            assert profile_a != profile_b

            update = client.put(
                f"/api/family/profiles/{profile_a}",
                json={"preferred_genres": ["Comedy"], "preferred_moods": ["Relaxed"]},
            )
            assert update.status_code == 200
            prefs_a = client.get(f"/api/family/profiles/{profile_a}/preferences")
            prefs_b = client.get(f"/api/family/profiles/{profile_b}/preferences")
            assert prefs_a.status_code == prefs_b.status_code == 200

            db = SessionLocal()
            try:
                row_a = db.get(ProfilePreference, profile_a)
                row_b = db.get(ProfilePreference, profile_b)
                row_a_scoped = bool(row_a and row_a.user_id == user_id and "Comedy" in row_a.preferred_genres_json)
                row_b_has_a_value = bool(row_b and "Comedy" in row_b.preferred_genres_json)
            finally:
                db.close()

            result = {
                "test": "T-04",
                "profile_ids_are_distinct": profile_a != profile_b,
                "profile_a_preferences_status": prefs_a.status_code,
                "profile_b_preferences_status": prefs_b.status_code,
                "profile_a_comedy_preference_present": "Comedy" in prefs_a.text,
                "profile_b_contains_profile_a_preference": "Comedy" in prefs_b.text,
                "preference_row_scoped_to_profile_a": row_a_scoped,
                "profile_b_stored_profile_a_preference": row_b_has_a_value,
                "result": "PASS",
            }
            assert result["profile_a_comedy_preference_present"]
            assert not result["profile_b_contains_profile_a_preference"]
            assert result["preference_row_scoped_to_profile_a"]
            assert not result["profile_b_stored_profile_a_preference"]
            print(json.dumps(result, indent=2))
        finally:
            if user_id is not None:
                client.delete("/api/account")
