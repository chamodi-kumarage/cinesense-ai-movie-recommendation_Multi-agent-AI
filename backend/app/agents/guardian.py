import re,html,unicodedata
from sqlalchemy.orm import Session
from ..protocol import AgentEnvelope,log_envelope
from ..models import SecurityEvent

INJECTION_PATTERNS=[
 r"ignore\s+(all|any|the|your)?\s*(previous|prior|system|developer)\s+instructions?",
 r"(reveal|print|repeat|dump|show)\s+(the\s+)?(system|developer|hidden|internal)\s+(prompt|instructions?|message)",
 r"(what|tell me)\s+(is|are)\s+your\s+(system|developer|hidden)\s+(prompt|instructions?)",
 r"jailbreak",r"developer\s+message",r"api[_ -]?key",r"bypass\s+(safety|guard|policy)",
 r"act\s+as\s+(?:an?\s+)?(?:unfiltered|unrestricted|developer|system)",r"do\s+anything\s+now",
 r"forget\s+(everything|all)\s+(above|before)",r"override\s+(the\s+)?(system|developer|safety)",
 r"base64.{0,40}(system|prompt|secret)",r"role\s*:\s*(system|developer)",
]
SECRET_PATTERNS=[r"sk-[A-Za-z0-9_-]{20,}",r"(?i)(api[_ -]?key|secret|password|token)\s*[:=]\s*\S+",r"(?i)bearer\s+[A-Za-z0-9._-]{12,}",r"\b(?:\d[ -]*?){13,19}\b",r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",r"\b(?:\+?\d[\s().-]*){9,15}\b"]
TOXIC_PATTERNS=[r"(?i)\bkill yourself\b",r"(?i)\bworthless (people|group)\b",r"(?i)\bhate all \w+ people\b"]

class GuardianAgent:
    name="guardian"
    def inspect_input(self,db:Session,envelope:AgentEnvelope,text:str)->dict:
        log_envelope(db,envelope)
        clean=html.unescape(text).replace("\x00"," ")
        clean="".join(ch for ch in clean if unicodedata.category(ch) not in {"Cf","Cs"} or ch in "\n\t")
        clean=re.sub(r"[ \t]+"," ",clean).strip()[:3000]
        normalized=re.sub(r"[^a-z0-9\s:_-]"," ",clean.lower())
        normalized=re.sub(r"\s+"," ",normalized)
        hits=[p for p in INJECTION_PATTERNS if re.search(p,normalized,re.I)]
        # Heuristic score catches composed attacks even when no exact phrase matches.
        risky_terms=sum(x in normalized for x in ["system prompt","developer prompt","hidden instructions","ignore previous","bypass safety","reveal secret","api key"])
        flagged=bool(hits) or risky_terms>=2
        if flagged:
            db.add(SecurityEvent(category="prompt_attack",severity="warning",detail_safe=f"blocked_prompt_injection:risk={min(100,len(hits)*35+risky_terms*20)}"));db.commit()
        return {"safe":not flagged,"sanitized":clean,"risk":"prompt_injection" if flagged else "low","risk_score":min(100,len(hits)*35+risky_terms*20),"notice":("I can help with movies, recommendations, planning, and comparisons, but I can’t expose hidden instructions, credentials, private data, or bypass safeguards. Security-test attempts are recorded only as privacy-safe traces." if flagged else None)}
    def inspect_output(self,db:Session,envelope:AgentEnvelope,text:str)->str:
        log_envelope(db,envelope);out=text
        for pat in SECRET_PATTERNS:out=re.sub(pat,"[redacted]",out)
        for marker in ["BEGIN SYSTEM PROMPT","developer message:","hidden policy:","system prompt:"]:out=out.replace(marker,"[protected instruction]")
        for pat in TOXIC_PATTERNS: out=re.sub(pat,"[removed unsafe content]",out)
        return out
