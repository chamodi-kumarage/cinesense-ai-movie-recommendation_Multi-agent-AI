import re
from sqlalchemy.orm import Session
from ..protocol import AgentEnvelope, log_envelope
from ..config import get_settings

settings=get_settings()
MOOD_MAP = {
    "Happy":["happy","cheer","funny","fun","uplifting","light","joy","good mood","laugh","feel good","euphoric","playful"],
    "Relaxed":["relax","calm","cozy","cosy","warm hug","chill","gentle","stressed","stress","easy","unwind","decompress","exhausted","tired"],
    "Sad/Cathartic":["sad","cry","emotional","heartbreak","cathartic","grief","melancholy","touching","bittersweet"],
    "Thrilled":["thrill","tense","exciting","suspense","adrenaline","scary","intense","edge of my seat","gripping"],
    "Romantic":["romantic","romance","date night","love story","in love","couple"],
    "Nostalgic":["nostalgic","nostalgia","childhood","classic","old school","comfort movie","throwback"],
}
GENRES = ["Action","Adventure","Animation","Comedy","Crime","Documentary","Drama","Family","Fantasy","History","Horror","Music","Mystery","Romance","Science Fiction","Thriller","War","Western"]

class MoodPreferenceAgent:
    name="mood_preference"
    def __init__(self):
        self._nlp=None
        if settings.enable_spacy_ner:
            try:
                import spacy
                self._nlp=spacy.load(settings.spacy_model)
            except Exception:
                self._nlp=None

    def _entities(self,text):
        entities=[]
        if self._nlp is not None:
            try:
                doc=self._nlp(text)
                entities.extend(ent.text for ent in doc.ents if ent.label_ in {"PERSON","WORK_OF_ART","ORG","GPE","LANGUAGE"})
            except Exception: pass
        quoted=re.findall(r'["“](.+?)["”]',text)
        proper=re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b",text)
        return list(dict.fromkeys(entities+quoted+proper))[:10]

    def analyze(self,db:Session,envelope:AgentEnvelope,text:str,mood_override=None,dismissed_moods=None)->dict:
        log_envelope(db,envelope);lower=text.lower();dismissed={x.lower() for x in (dismissed_moods or [])}
        scores={}
        for mood,words in MOOD_MAP.items():
            score=sum(2 if re.search(rf"\b{re.escape(w)}\b",lower) else 0 for w in words)
            # Negated mood terms should not drive the result.
            score-=sum(2 for w in words if re.search(rf"\b(?:not|no|avoid|without)\s+(?:too\s+)?{re.escape(w)}\b",lower))
            if score>0 and mood.lower() not in dismissed:scores[mood]=score
        mood=mood_override or (max(scores,key=scores.get) if scores else None)
        genres=[];disliked=[]
        for g in GENRES:
            gl=g.lower()
            if re.search(rf"\b(?:no|not|avoid|hate|without|anything but)\s+(?:too\s+)?{re.escape(gl)}\b",lower): disliked.append(g)
            elif re.search(rf"\b{re.escape(gl)}\b",lower): genres.append(g)
        minutes=None
        matches=[]
        for m in re.finditer(r"(\d{2,3})\s*(?:minutes?|mins?|min)\b",lower):matches.append(int(m.group(1)))
        for m in re.finditer(r"(\d(?:\.\d+)?)\s*(?:hours?|hrs?|hr)\b",lower):matches.append(int(float(m.group(1))*60))
        if matches:minutes=min(matches)
        return {"genres":list(dict.fromkeys(genres)),"mood":mood,"time_available":minutes,"disliked":list(dict.fromkeys(disliked)),"entities":self._entities(text),"detected_moods":sorted(scores,key=scores.get,reverse=True),"nlp_backend":"spacy+rules" if self._nlp else "enhanced-rules"}
