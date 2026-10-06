import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")
from app.main import app
from app.db import Base, get_db
from app.models import Movie
from app.dependencies import require_admin


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for i, language in enumerate(["English", "English", "Tamil"], 1):
            db.add(Movie(id=i, title=f"Film {i}", year=2020, genres="Comedy", runtime=90,
                         overview="Fixture", language=language, studio="A" if i < 3 else "B"))
        db.commit()
    def database():
        with Session() as db:
            yield db
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)
    engine.dispose()


def test_public_catalogue_counts(client):
    data = client.get("/api/responsible-ai/catalogue").json()
    assert data["total_movies"] == 3
    assert data["languages"]["Tamil"]["count"] == 1


def test_exposure_requires_authentication(client):
    assert client.post("/api/responsible-ai/exposure", json={"movie_ids": [1]}).status_code == 401
    assert client.get("/api/responsible-ai/feedback").status_code == 401


def test_exposure_metric_known_distance(client):
    app.dependency_overrides[require_admin] = lambda: object()
    r = client.post("/api/responsible-ai/exposure", json={"movie_ids": [3]})
    assert r.status_code == 200
    assert r.json()["dimensions"]["language"]["total_variation_distance"] == pytest.approx(2/3, abs=1e-6)
    full = client.post("/api/responsible-ai/exposure", json={"movie_ids": [1, 2, 3]}).json()
    assert full["dimensions"]["language"]["total_variation_distance"] == 0


def test_invalid_shortlists(client):
    app.dependency_overrides[require_admin] = lambda: object()
    for ids, code in [([], 422), ([1, 1], 422), ([999], 404), (list(range(101)), 422)]:
        assert client.post("/api/responsible-ai/exposure", json={"movie_ids": ids}).status_code == code


def test_methodology_does_not_claim_compliance(client):
    data = client.get("/api/responsible-ai/methodology").json()
    assert len(data["areas"]) == 7
    assert "not proof" in data["interpretation"]
