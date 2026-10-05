import json
from collections import Counter
from sqlalchemy.orm import Session
from ..models import Movie, Profile, ProfilePreference, ProfileWatchEvent, FamilyProfileSafety
from ..security import decrypt_text
from ..agents.retrieval import parse_csvish

RATING_LEVELS = {"G": 0, "TV-Y": 0, "TV-G": 0, "PG": 1, "TV-PG": 1, "PG-13": 2, "TV-14": 2, "R": 3, "TV-MA": 3, "NC-17": 4, "X": 4}
AGE_MAX_RATING = {"all": None, "under13": "PG", "teen": "PG-13", "adult": "NC-17"}


def safety_row(db: Session, user_id: int, profile_id: int, create: bool = False):
    row = db.get(FamilyProfileSafety, profile_id)
    if row and row.user_id != user_id:
        raise ValueError("Profile safety ownership mismatch.")
    if not row and create:
        row = FamilyProfileSafety(profile_id=profile_id, user_id=user_id)
        db.add(row)
        db.flush()
    return row


def safety_payload(db: Session, user_id: int, profile_id: int) -> dict:
    row = safety_row(db, user_id, profile_id)
    if not row:
        return {"age_group": "all", "excluded_genres": [], "block_unrated": True}
    try:
        excluded = json.loads(row.excluded_genres_json or "[]")
    except Exception:
        excluded = []
    return {"age_group": row.age_group, "excluded_genres": excluded, "block_unrated": row.block_unrated}


def set_safety_settings(db: Session, user_id: int, profile_id: int, *, age_group=None, excluded_genres=None, block_unrated=None):
    row = safety_row(db, user_id, profile_id, create=True)
    if age_group is not None: row.age_group = age_group
    if excluded_genres is not None: row.excluded_genres_json = json.dumps(sorted(set(excluded_genres)))
    if block_unrated is not None: row.block_unrated = block_unrated
    return row


def movie_allowed_for_profiles(movie: Movie, profiles: list[Profile], db: Session) -> bool:
    genres = {g.casefold() for g in parse_csvish(movie.genres)}
    movie_rating = (movie.content_rating or "").upper().strip()
    movie_level = RATING_LEVELS.get(movie_rating)
    for profile in profiles:
        setting = safety_row(db, profile.user_id, profile.id)
        if not setting:
            continue
        try: excluded = {str(x).casefold() for x in json.loads(setting.excluded_genres_json or "[]")}
        except Exception: excluded = set()
        if genres & excluded:
            return False
        maximum = AGE_MAX_RATING.get(setting.age_group)
        if maximum:
            if movie_level is None and setting.block_unrated:
                return False
            if movie_level is not None and movie_level > RATING_LEVELS[maximum]:
                return False
    return True


def _json_list(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
        return [str(x) for x in data if str(x).strip()]
    except Exception:
        return []


def preference_row(db: Session, user_id: int, profile_id: int) -> ProfilePreference:
    row = db.get(ProfilePreference, profile_id)
    if row and row.user_id != user_id:
        raise ValueError("Profile preference ownership mismatch.")
    if not row:
        row = ProfilePreference(profile_id=profile_id, user_id=user_id)
        db.add(row)
        db.flush()
    return row


def preference_payload(db: Session, user_id: int, profile_id: int) -> dict:
    row = preference_row(db, user_id, profile_id)
    return {
        "preferred_genres": _json_list(row.preferred_genres_json),
        "disliked_genres": _json_list(row.disliked_genres_json),
        "preferred_moods": _json_list(row.preferred_moods_json),
    }


def set_preferences(db: Session, user_id: int, profile_id: int, *, preferred_genres=None, disliked_genres=None, preferred_moods=None):
    row = preference_row(db, user_id, profile_id)
    if preferred_genres is not None:
        row.preferred_genres_json = json.dumps(sorted(set(preferred_genres)))
    if disliked_genres is not None:
        row.disliked_genres_json = json.dumps(sorted(set(disliked_genres)))
    if preferred_moods is not None:
        row.preferred_moods_json = json.dumps(sorted(set(preferred_moods)))
    return row


def profile_learning_snapshot(db: Session, user_id: int, profile_id: int, limit: int = 40) -> dict:
    stored = preference_payload(db, user_id, profile_id)
    genre_counts, mood_counts, watched_ids = Counter(), Counter(), set()
    events = (db.query(ProfileWatchEvent)
              .filter(ProfileWatchEvent.user_id == user_id, ProfileWatchEvent.profile_id == profile_id, ProfileWatchEvent.watched == True)
              .order_by(ProfileWatchEvent.created_at.desc()).limit(limit).all())
    for event in events:
        try:
            movie_id = int(decrypt_text(event.movie_id_enc)); movie = db.get(Movie, movie_id)
        except Exception:
            movie = None
        if not movie:
            continue
        watched_ids.add(movie.id)
        try:
            rating = float(decrypt_text(event.rating_enc)) if event.rating_enc else 3.0
        except Exception:
            rating = 3.0
        weight = max(.25, 1.0 + (rating - 3.0) * .35)
        for g in parse_csvish(movie.genres): genre_counts[g] += weight
        for m in parse_csvish(movie.moods): mood_counts[m] += weight
    return {
        **stored,
        "learned_genres": [x for x,_ in genre_counts.most_common(5)],
        "learned_moods": [x for x,_ in mood_counts.most_common(4)],
        "watched_movie_ids": list(watched_ids),
        "history_count": len(events),
    }


def member_score(movie: Movie, snapshot: dict, requested_mood: str | None = None) -> dict:
    genres, moods = set(parse_csvish(movie.genres)), set(parse_csvish(movie.moods))
    preferred = set(snapshot.get("preferred_genres") or []) | set(snapshot.get("learned_genres") or [])
    disliked = set(snapshot.get("disliked_genres") or [])
    preferred_moods = set(snapshot.get("preferred_moods") or []) | set(snapshot.get("learned_moods") or [])
    conflicts = genres & disliked
    genre_hits = genres & preferred
    mood_hits = moods & preferred_moods
    score = 52.0
    if preferred:
        score += min(22.0, 11.0 * len(genre_hits))
    if preferred_moods:
        score += min(12.0, 6.0 * len(mood_hits))
    if requested_mood:
        score += 10.0 if requested_mood in moods else -3.0
    if movie.id in set(snapshot.get("watched_movie_ids") or []):
        score -= 8.0
    score -= 28.0 * len(conflicts)
    score += min(4.0, max(0.0, (float(movie.rating or 0) - 6.0)))
    score = max(0.0, min(100.0, score))
    return {
        "score": round(score, 1),
        "genre_matches": sorted(genre_hits),
        "mood_matches": sorted(mood_hits),
        "conflicts": sorted(conflicts),
    }


def consensus_for_movie(movie: Movie, member_snapshots: list[tuple[Profile, dict]], requested_mood: str | None = None) -> dict:
    members = []
    for profile, snap in member_snapshots:
        detail = member_score(movie, snap, requested_mood)
        members.append({"profile_id": profile.id, "profile_name": decrypt_text(profile.name_enc), **detail})
    scores = [m["score"] for m in members]
    average = sum(scores) / len(scores) if scores else 0.0
    satisfied = sum(1 for s in scores if s >= 60)
    strong = sum(1 for s in scores if s >= 75)
    conflicts = sum(1 for m in members if m["conflicts"])
    satisfaction_bonus = (satisfied / len(scores) * 10.0) if scores else 0.0
    balance_bonus = (strong / len(scores) * 4.0) if scores else 0.0
    conflict_penalty = (conflicts / len(scores) * 18.0) if scores else 0.0
    group_score = max(0.0, min(100.0, average + satisfaction_bonus + balance_bonus - conflict_penalty))
    return {
        "group_score": round(group_score, 1),
        "average_member_score": round(average, 1),
        "satisfied_members": satisfied,
        "member_count": len(scores),
        "conflict_count": conflicts,
        "member_scores": members,
        "formula": "average(member_scores) + satisfaction_bonus + balance_bonus - conflict_penalty",
    }
