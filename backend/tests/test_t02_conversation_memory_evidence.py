import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cinesense.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import ChatTurn, ProfileConversationState, User
from app.security import decrypt_text
from app.services.llm import llm_service


def test_t02_chat_memory_is_isolated_when_switching_profiles(monkeypatch):
    # Capture only the history supplied to the offline adapter, never contact a provider.
    observed_histories = []

    async def fake_llm_chat(prompt, context="", history=None):
        observed_histories.append(history or [])
        return "Synthetic offline reply."

    monkeypatch.setattr(llm_service, "chat", fake_llm_chat)

    with TestClient(app) as client:
        registration = client.post("/api/auth/register", json={
            "email": f"t02-{uuid.uuid4().hex}@example.com",
            "password": "Synthetic123",
            "display_name": "Synthetic Profile Tester",
        })
        assert registration.status_code == 200
        user_id = registration.json()["id"]
        try:
            db = SessionLocal()
            try:
                db.query(User).filter(User.id == user_id).update({User.plan: "family"})
                db.commit()
            finally:
                db.close()

            assert client.post("/api/auth/consent", json={"accepted": True}).status_code == 200
            first_profile = client.get("/api/family/profiles").json()[0]["id"]
            second_response = client.post("/api/family/profiles", json={"name": "Synthetic Profile B"})
            assert second_response.status_code == 200
            second_profile = second_response.json()["id"]
            assert first_profile != second_profile

            assert client.post("/api/family/profiles/switch", json={"profile_id": first_profile}).status_code == 200
            canary = "profile-memory-canary-" + uuid.uuid4().hex
            first_chat = client.post("/api/chat", json={"message": f"Remember this synthetic note: {canary}"})
            assert first_chat.status_code == 200

            assert client.post("/api/family/profiles/switch", json={"profile_id": second_profile}).status_code == 200
            followup = client.post("/api/chat", json={"message": "What did I tell you earlier?"})
            assert followup.status_code == 200

            second_adapter_history = observed_histories[-1]
            db = SessionLocal()
            try:
                turns_a = db.query(ChatTurn).filter(
                    ChatTurn.user_id == user_id, ChatTurn.profile_id == first_profile
                ).all()
                turns_b = db.query(ChatTurn).filter(
                    ChatTurn.user_id == user_id, ChatTurn.profile_id == second_profile
                ).all()
                state_a = db.get(ProfileConversationState, first_profile)
                state_b = db.get(ProfileConversationState, second_profile)
                canary_in_b_turns = any(canary in decrypt_text(row.content_enc) for row in turns_b)
                canary_in_b_state = bool(state_b and canary in decrypt_text(state_b.last_query_enc))
                canary_in_a_turns = any(canary in decrypt_text(row.content_enc) for row in turns_a)
            finally:
                db.close()

            history_text = json.dumps(second_adapter_history, ensure_ascii=False)
            evidence = {
                "test": "T-02",
                "profile_switch_status": 200,
                "profile_a_turn_count": len(turns_a),
                "profile_b_turn_count": len(turns_b),
                "profile_a_canary_stored_in_profile_a": canary_in_a_turns,
                "profile_a_canary_in_profile_b_llm_history": canary in history_text,
                "profile_a_canary_in_profile_b_response": canary in followup.text,
                "profile_a_canary_in_profile_b_persisted_turns": canary_in_b_turns,
                "profile_a_canary_in_profile_b_state": canary_in_b_state,
                "profile_state_rows_exist": {"profile_a": state_a is not None, "profile_b": state_b is not None},
                "provider_mode": "offline mock; no external request",
                "result": "PASS",
            }
            assert canary_in_a_turns
            assert not evidence["profile_a_canary_in_profile_b_llm_history"]
            assert not evidence["profile_a_canary_in_profile_b_response"]
            assert not canary_in_b_turns
            assert not canary_in_b_state
            print(json.dumps(evidence, indent=2))
        finally:
            client.delete("/api/account")
