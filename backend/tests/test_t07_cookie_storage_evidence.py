import json
import os
import uuid
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")

from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings


def test_t07_cookie_flags_logout_and_frontend_storage_source():
    settings = get_settings()
    with TestClient(app) as client:
        registration = client.post("/api/auth/register", json={
            "email": f"t07-{uuid.uuid4().hex}@example.com",
            "password": "Synthetic123",
            "display_name": "Synthetic Cookie Tester",
        })
        assert registration.status_code == 200
        set_cookie = registration.headers.get("set-cookie", "").lower()

        http_only = "httponly" in set_cookie
        same_site_lax = "samesite=lax" in set_cookie
        secure_flag = "secure" in set_cookie
        expected_secure = settings.environment == "production"

        # Remove the disposable test account, then verify logout still clears its cookie.
        assert client.delete("/api/account").status_code == 204
        logout = client.post("/api/auth/logout")
        cleared_cookie = logout.headers.get("set-cookie", "").lower()
        cookie_cleared = "max-age=0" in cleared_cookie

    frontend_src = Path(__file__).resolve().parents[2] / "frontend" / "src"
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in frontend_src.rglob("*")
        if path.is_file()
    )
    uses_local_storage = "localStorage" in source_text
    uses_session_storage = "sessionStorage" in source_text

    evidence = {
        "test": "T-07",
        "environment": settings.environment,
        "cookie_http_only": http_only,
        "cookie_same_site_lax": same_site_lax,
        "cookie_secure": secure_flag,
        "secure_matches_environment": secure_flag == expected_secure,
        "logout_cookie_cleared": cookie_cleared,
        "frontend_uses_local_storage": uses_local_storage,
        "frontend_uses_session_storage": uses_session_storage,
        "result": "PASS",
    }
    assert http_only and same_site_lax
    assert secure_flag == expected_secure
    assert cookie_cleared
    assert not uses_local_storage and not uses_session_storage
    print(json.dumps(evidence, indent=2))
