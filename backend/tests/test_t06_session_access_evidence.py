import json
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")

import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings


def test_t06_private_endpoint_rejects_missing_malformed_and_expired_sessions():
    with TestClient(app) as client:
        missing = client.get("/api/plans")

        client.cookies.set("access_token", "not-a-valid-token")
        malformed = client.get("/api/plans")

        now = datetime.now(timezone.utc)
        expired_token = jwt.encode(
            {"sub": "999999", "iat": int((now - timedelta(days=2)).timestamp()),
             "exp": int((now - timedelta(days=1)).timestamp())},
            get_settings().secret_key,
            algorithm="HS256",
        )
        client.cookies.set("access_token", expired_token)
        expired = client.get("/api/plans")

        def contains_private_data(response):
            body = response.text.lower()
            return any(field in body for field in ('"email"', '"display_name"', '"plan"'))

        evidence = {
            "test": "T-06",
            "missing_cookie_status": missing.status_code,
            "malformed_cookie_status": malformed.status_code,
            "expired_token_status": expired.status_code,
            "private_fields_in_responses": any(map(contains_private_data, (missing, malformed, expired))),
            "result": "PASS",
        }
        assert missing.status_code == malformed.status_code == expired.status_code == 401
        assert not evidence["private_fields_in_responses"]
        print(json.dumps(evidence, indent=2))
