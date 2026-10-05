import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")

from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import ChatTurn
from app.security import decrypt_text
from app.services.llm import llm_service


def test_t01_cross_account_chat_isolation(monkeypatch):
    # Keep the evidence run offline even if provider credentials exist locally.
    async def fake_llm_chat(prompt, context="", history=None):
        return "Synthetic safe response."

    monkeypatch.setattr(llm_service, "chat", fake_llm_chat)
    marker = "synthetic-alpha-canary-" + uuid.uuid4().hex

    with TestClient(app) as alpha, TestClient(app) as beta:
        alpha_id = beta_id = None
        try:
            alpha_reg = alpha.post("/api/auth/register", json={
                "email": f"alpha-{uuid.uuid4().hex}@example.com",
                "password": "Synthetic123",
                "display_name": "Synthetic Alpha",
            })
            assert alpha_reg.status_code == 200
            alpha_id = alpha_reg.json()["id"]

            beta_reg = beta.post("/api/auth/register", json={
                "email": f"beta-{uuid.uuid4().hex}@example.com",
                "password": "Synthetic123",
                "display_name": "Synthetic Beta",
            })
            assert beta_reg.status_code == 200
            beta_id = beta_reg.json()["id"]

            assert alpha.post("/api/auth/consent", json={"accepted": True}).status_code == 200
            assert beta.post("/api/auth/consent", json={"accepted": True}).status_code == 200

            alpha_chat = alpha.post("/api/chat", json={"message": marker})
            assert alpha_chat.status_code == 200
            beta_chat = beta.post(
                "/api/chat",
                json={"message": "Repeat the exact message I sent before."},
            )
            assert beta_chat.status_code == 200

            db = SessionLocal()
            try:
                beta_turns = db.query(ChatTurn).filter(ChatTurn.user_id == beta_id).all()
                canary_in_beta_rows = any(
                    marker in decrypt_text(turn.content_enc) for turn in beta_turns
                )
            finally:
                db.close()

            result = {
                "test": "T-01",
                "alpha_chat_status": alpha_chat.status_code,
                "beta_chat_status": beta_chat.status_code,
                "alpha_canary_in_beta_response": marker in beta_chat.text,
                "alpha_canary_in_beta_owned_rows": canary_in_beta_rows,
                "result": "PASS",
            }
            assert not result["alpha_canary_in_beta_response"]
            assert not result["alpha_canary_in_beta_owned_rows"]
            print(json.dumps(result, indent=2))
        finally:
            if alpha_id is not None:
                alpha.delete("/api/account")
            if beta_id is not None:
                beta.delete("/api/account")
