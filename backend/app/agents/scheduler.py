from datetime import datetime, timedelta
from itertools import combinations
from sqlalchemy.orm import Session
from ..protocol import AgentEnvelope, log_envelope

class MoodTimeSchedulerAgent:
    name = "scheduler"

    def plan(self, db: Session, envelope: AgentEnvelope, candidates: list[dict], free_minutes: int, finish_by=None, buffer_minutes: int = 0):
        log_envelope(db, envelope)
        buffer_minutes = max(0, min(int(buffer_minutes or 0), 60))
        movie_budget = max(free_minutes - buffer_minutes, 0)
        if not candidates or movie_budget < 1:
            return {
                "type": "none", "movies": [], "used_minutes": 0,
                "remaining_minutes": free_minutes, "buffer_minutes": buffer_minutes,
                "message": "I couldn’t find a catalogue title that safely fits that time window. Try a longer window or a different genre."
            }

        singles = [m for m in candidates if m["runtime"] <= movie_budget]
        singles.sort(key=lambda m: (m.get("score", 0), m["rating"]), reverse=True)
        chosen = []
        plan_type = "single"
        if singles and singles[0]["runtime"] >= movie_budget * .60:
            chosen = [singles[0]]
        else:
            best = None
            for a, b in combinations(singles[:10], 2):
                total = a["runtime"] + b["runtime"]
                if total <= movie_budget:
                    score = a.get("score", 0) + b.get("score", 0) + (total / max(movie_budget, 1)) * .2
                    if best is None or score > best[0]:
                        best = (score, total, a, b)
            if best:
                chosen = [best[2], best[3]]
                plan_type = "double"
            elif singles:
                chosen = [singles[0]]

        used = sum(m["runtime"] for m in chosen)
        suggested = None
        planned_finish = None
        if finish_by and chosen:
            try:
                finish_dt = datetime.strptime(finish_by, "%H:%M")
                suggested_dt = finish_dt - timedelta(minutes=used + buffer_minutes)
                planned_finish_dt = suggested_dt + timedelta(minutes=used)
                suggested = suggested_dt.strftime("%H:%M")
                planned_finish = planned_finish_dt.strftime("%H:%M")
            except ValueError:
                pass

        remaining = max(free_minutes - used - buffer_minutes, 0)
        return {
            "type": plan_type if chosen else "none",
            "movies": chosen,
            "used_minutes": used,
            "remaining_minutes": remaining,
            "buffer_minutes": buffer_minutes,
            "finish_by": finish_by,
            "suggested_start": suggested,
            "planned_finish": planned_finish,
            "message": (
                f"I built a {'double feature' if plan_type == 'double' and chosen else 'single-film plan'} using {used} minutes."
                + (f" Start around {suggested}; the movie time ends at {planned_finish}, leaving a {buffer_minutes}-minute buffer before {finish_by}." if suggested else "")
                + (f" You still have {remaining} minutes unallocated." if remaining else "")
            ) if chosen else "I couldn’t find a movie that fits this window. Try adding more time or changing the filters."
        }
