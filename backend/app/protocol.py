from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field
import hashlib, json
from sqlalchemy.orm import Session
from .models import AgentTrace

class AgentEnvelope(BaseModel):
    trace_id: str
    sender: str
    receiver: str
    intent: str
    user_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def safe_payload(payload: dict) -> dict:
    allowed = {"agent", "status", "latency_ms", "intent", "result_count", "movie_count", "candidate_count", "free_minutes", "buffer_minutes", "response_type", "runtime"}
    safe = {}
    for key, value in payload.items():
        if key.lower() in allowed and not isinstance(value, (dict, list, str)):
            safe[key] = value
        elif key.lower() in allowed and isinstance(value, str) and len(value) <= 80:
            safe[key] = value
        elif isinstance(value, (dict, list, str)):
            raw = json.dumps(value, ensure_ascii=False, default=str)
            safe[f"{key}_sha256"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        else:
            safe[key] = value if isinstance(value, (int, float, bool)) or value is None else "[redacted]"
    return safe

def log_envelope(db: Session, envelope: AgentEnvelope):
    db.add(AgentTrace(
        trace_id=envelope.trace_id, user_id=envelope.user_id, sender=envelope.sender, receiver=envelope.receiver,
        intent=envelope.intent, payload_safe=json.dumps(safe_payload(envelope.payload), ensure_ascii=False, default=str),
        timestamp=envelope.timestamp))
    db.commit()
