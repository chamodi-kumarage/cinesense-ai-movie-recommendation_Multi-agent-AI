import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")
from app.main import app
from app.db import Base, get_db
from app.dependencies import get_current_user
from app.models import User, Profile, ActiveProfile, Movie, ProfileWatchEvent, PlannerActivity
from app.security import encrypt_text


@pytest.fixture
def history():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        user = User(email="insights@example.com", password_hash="fixture", plan="family", consented=True)
        db.add(user); db.flush()
        a = Profile(user_id=user.id, name_enc=encrypt_text("Viewer A"))
        b = Profile(user_id=user.id, name_enc=encrypt_text("Viewer B"))
        db.add_all([a, b]); db.flush()
        db.add(ActiveProfile(user_id=user.id, profile_id=a.id))
        for mid, runtime in [(1, 90), (2, 120)]:
            db.add(Movie(id=mid, title=f"Movie {mid}", year=2020, genres="Comedy", moods="Happy",
                         runtime=runtime, overview="Fixture"))
        db.commit()
    def database():
        with Session() as db:
            yield db
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: user
    c = TestClient(app)
    try:
        yield c, Session, user, a, b
    finally:
        c.close()
        app.dependency_overrides.clear(); app.dependency_overrides.update(previous)
        engine.dispose()


def add_watch(db, user, profile, mid, days=0, watched=True):
    db.add(ProfileWatchEvent(user_id=user.id, profile_id=profile.id, movie_id_enc=encrypt_text(str(mid)),
                             watched=watched, created_at=datetime.now(timezone.utc)-timedelta(days=days)))


def test_real_counts_runtime_genre_and_profile_isolation(history):
    c, Session, user, a, b = history
    with Session() as db:
        add_watch(db, user, a, 1); add_watch(db, user, a, 2)
        add_watch(db, user, a, 1, 20); add_watch(db, user, b, 2)
        add_watch(db, user, a, 2, watched=False)
        db.commit()
    stats = c.get("/api/planner/weekly-summary").json()
    assert stats["profile_name"] == "Viewer A"
    assert stats["movies_watched"] == 2
    assert stats["watch_minutes"] == 210 and stats["watch_time_label"] == "3h 30m"
    assert stats["average_movie_length"] == 105
    assert stats["favourite_genre"] == "Comedy"
    assert stats["most_common_mood"] is None  # Movie tags do not describe the user's mood.
    assert c.get("/api/planner/weekly-summary?days=30").json()["movies_watched"] == 3
    assert c.get("/api/planner/weekly-summary?days=0").json()["movies_watched"] == 3
    assert c.get("/api/planner/weekly-summary?days=-1").status_code == 422


def test_planned_values_do_not_invent_watched_values(history):
    c, Session, user, a, _ = history
    with Session() as db:
        db.add(PlannerActivity(user_id=user.id, profile_id=a.id, mood="Relaxed", genres_json='["Comedy"]',
                              movie_ids_json='[1,2]', used_minutes=210, free_minutes=240))
        db.commit()
    stats = c.get("/api/planner/weekly-summary").json()
    assert stats["plans_created"] == 1 and stats["planned_movie_slots"] == 2
    assert stats["planned_minutes"] == 210 and stats["favourite_planned_genre"] == "Comedy"
    assert stats["most_common_mood"] == "Relaxed"
    assert stats["movies_watched"] == 0 and stats["watch_minutes"] == 0
    assert stats["average_movie_length"] is None
    assert len(stats["recent_planned_movies"]) == 2


def test_watch_endpoint_updates_summary_without_duplicate_clicks(history):
    c, Session, user, a, b = history
    body = {"movie_id": 1, "watched": True, "rating": None}
    assert c.post("/api/watch-events", json=body).status_code == 200
    assert c.post("/api/watch-events", json=body).json()["already_recorded"] is True
    stats = c.get("/api/planner/weekly-summary").json()
    assert stats["movies_watched"] == 1 and stats["watch_minutes"] == 90
    assert c.post("/api/family/profiles/switch", json={"profile_id": b.id}).status_code == 200
    other = c.get("/api/planner/weekly-summary").json()
    assert other["profile_id"] == b.id and other["movies_watched"] == 0
    assert c.post("/api/watch-events", json=body).status_code == 200
    assert c.get("/api/planner/weekly-summary").json()["movies_watched"] == 1


def test_empty_or_invalid_metadata_is_not_a_fake_zero_length_movie(history):
    c, Session, user, a, _ = history
    with Session() as db:
        add_watch(db, user, a, 999)
        db.commit()
    stats = c.get("/api/planner/weekly-summary").json()
    assert stats["movies_watched"] == 0 and stats["average_movie_length"] is None
    assert stats["favourite_genre"] is None and stats["recent_watches"] == []
