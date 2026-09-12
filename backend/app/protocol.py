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
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def safe_payload(payload: dict) -> dict:
    safe = {}
    for key, value in payload.items():
        if key.lower() in {"message","content","email","display_name","history","raw_text"}:
            raw = json.dumps(value, ensure_ascii=False, default=str)
            safe[f"{key}_sha256"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        elif isinstance(value, str) and len(value) > 160:
            safe[key] = value[:157] + "..."
        elif isinstance(value, (dict, list)):
            raw = json.dumps(value, ensure_ascii=False, default=str)
            safe[f"{key}_summary"] = f"{type(value).__name__}:{len(value)} sha256:{hashlib.sha256(raw.encode()).hexdigest()[:12]}"
        else:
            safe[key] = value
    return safe

def log_envelope(db: Session, envelope: AgentEnvelope):
    db.add(AgentTrace(
        trace_id=envelope.trace_id, sender=envelope.sender, receiver=envelope.receiver,
        intent=envelope.intent, payload_safe=json.dumps(safe_payload(envelope.payload), ensure_ascii=False, default=str),
        timestamp=envelope.timestamp))
    db.commit()
