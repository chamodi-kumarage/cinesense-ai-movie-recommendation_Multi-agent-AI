import os
import sys
from pathlib import Path
from io import BytesIO
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")
from app.main import app
from app.db import Base, get_db
from app.models import User, Profile, ProfilePhoto
from app.dependencies import get_current_user
from app.security import encrypt_text


def image_bytes(color="red"):
    data = BytesIO()
    Image.new("RGB", (400, 300), color).save(data, "PNG")
    return data.getvalue()


@pytest.fixture
def photos():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        owner = User(email="photos@example.com", password_hash="fixture", plan="family", consented=True)
        other = User(email="other@example.com", password_hash="fixture", plan="family", consented=True)
        db.add_all([owner, other]); db.flush()
        first = Profile(user_id=owner.id, name_enc=encrypt_text("First"))
        second = Profile(user_id=owner.id, name_enc=encrypt_text("Second"))
        db.add_all([first, second]); db.commit()
        profile_id = first.id
    def database():
        with Session() as db:
            yield db
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: owner
    client = TestClient(app)
    try:
        yield client, owner, other, profile_id, Session
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_upload_persists_and_replacement_refreshes_url(photos):
    c, _, _, pid, _ = photos
    url = f"/api/family/profiles/{pid}/photo"
    first = c.put(url, content=image_bytes(), headers={"Content-Type": "image/png"})
    assert first.status_code == 200
    picture = c.get(first.json()["photo_url"])
    assert picture.status_code == 200 and picture.headers["content-type"] == "image/jpeg"
    assert picture.headers["cache-control"] == "private, no-store"
    with Image.open(BytesIO(picture.content)) as image:
        assert image.size == (256, 256)
    listed = next(p for p in c.get("/api/family/profiles").json() if p["id"] == pid)
    assert listed["photo_url"] == first.json()["photo_url"]
    second = c.put(url, content=image_bytes("blue"), headers={"Content-Type": "image/png"})
    assert second.status_code == 200
    assert second.json()["photo_url"] != first.json()["photo_url"]
    assert c.get(second.json()["photo_url"]).content != picture.content


def test_reject_invalid_image_and_keep_existing_photo(photos):
    c, _, _, pid, _ = photos
    url = f"/api/family/profiles/{pid}/photo"
    c.put(url, content=image_bytes(), headers={"Content-Type": "image/png"})
    before = c.get(url).content
    assert c.put(url, content=b"not an image", headers={"Content-Type": "image/png"}).status_code == 400
    assert c.put(url, content=b"<svg/>", headers={"Content-Type": "image/svg+xml"}).status_code == 400
    assert c.get(url).content == before


def test_upload_size_limit(photos):
    c, _, _, pid, _ = photos
    assert c.put(f"/api/family/profiles/{pid}/photo", content=b"x" * (5*1024*1024+1),
                 headers={"Content-Type": "image/png"}).status_code == 413


def test_other_account_cannot_read_replace_or_remove(photos):
    c, _, other, pid, _ = photos
    url = f"/api/family/profiles/{pid}/photo"
    c.put(url, content=image_bytes(), headers={"Content-Type": "image/png"})
    app.dependency_overrides[get_current_user] = lambda: other
    assert c.get(url).status_code == 404
    assert c.put(url, content=image_bytes(), headers={"Content-Type": "image/png"}).status_code == 404
    assert c.delete(url).status_code == 404
    app.dependency_overrides.pop(get_current_user)
    assert c.get(url).status_code == 401


def test_remove_photo_and_profile_cleanup(photos):
    c, _, _, pid, Session = photos
    url = f"/api/family/profiles/{pid}/photo"
    c.put(url, content=image_bytes(), headers={"Content-Type": "image/png"})
    assert c.delete(url).json()["photo_url"] is None
    assert c.get(url).status_code == 404
    c.put(url, content=image_bytes(), headers={"Content-Type": "image/png"})
    assert c.delete(f"/api/family/profiles/{pid}").status_code == 200
    with Session() as db:
        assert db.get(ProfilePhoto, pid) is None


def test_non_family_plan_cannot_upload(photos):
    c, owner, _, pid, _ = photos
    owner.plan = "free"
    assert c.put(f"/api/family/profiles/{pid}/photo", content=image_bytes(),
                 headers={"Content-Type": "image/png"}).status_code == 403
