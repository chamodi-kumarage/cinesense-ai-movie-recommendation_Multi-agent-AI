import json, uuid
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..db import get_db
from ..dependencies import get_current_user
from ..models import (
    Profile, ActiveProfile, ProfileWatchEvent, ProfilePreference, Movie,
    GroupSession, GroupVote, PlannerActivity,
)
from ..schemas import (
    ProfileCreateRequest, ProfileUpdateRequest, ProfileSwitchRequest,
    GroupChoiceRequest, GroupCompareRequest, GroupVoteRequest,
)
from ..security import encrypt_text, decrypt_text
from ..services.profiles import ensure_default_profile, active_profile_id
from ..services.family_logic import (
    preference_payload, set_preferences, profile_learning_snapshot, consensus_for_movie,
)
from ..agents.retrieval import movie_dict
from ..agents.orchestrator import orchestrator
from ..protocol import AgentEnvelope

router = APIRouter(prefix="/api/family", tags=["family"])


def require_family(user):
    if user.plan != "family":
        raise HTTPException(403, "Family profiles and group choice require the Family plan.")


def owned_profile(db: Session, user_id: int, profile_id: int) -> Profile:
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found in this Family account.")
    return profile


def rich_profile_payload(db: Session, user, profile: Profile, active_id: int | None = None) -> dict:
    prefs = preference_payload(db, user.id, profile.id)
    history_count = db.query(ProfileWatchEvent).filter(
        ProfileWatchEvent.user_id == user.id,
        ProfileWatchEvent.profile_id == profile.id,
        ProfileWatchEvent.watched == True,
    ).count()
    return {
        "id": profile.id,
        "family_id": user.id,
        "name": decrypt_text(profile.name_enc),
        "display_name": decrypt_text(profile.name_enc),
        "active": profile.id == active_id,
        "preferences": prefs,
        "history_count": history_count,
        "created_at": profile.created_at,
    }


def validate_profile_ids(db: Session, user, profile_ids: list[int]) -> list[Profile]:
    ids = list(dict.fromkeys(profile_ids))
    if len(ids) < 2:
        raise HTTPException(400, "Choose at least two different family profiles.")
    profiles = db.query(Profile).filter(Profile.user_id == user.id, Profile.id.in_(ids)).all()
    if len(profiles) != len(ids):
        raise HTTPException(400, "One or more selected profiles do not belong to this Family account.")
    order = {pid: i for i, pid in enumerate(ids)}
    return sorted(profiles, key=lambda p: order[p.id])


def session_or_404(db: Session, user, session_id: str) -> GroupSession:
    row = db.query(GroupSession).filter(GroupSession.id == session_id, GroupSession.family_id == user.id).first()
    if not row:
        raise HTTPException(404, "Group movie session not found.")
    return row


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db), user=Depends(get_current_user)):
    ensure_default_profile(db, user)
    active_id = active_profile_id(db, user)
    rows = db.query(Profile).filter(Profile.user_id == user.id).order_by(Profile.id).all()
    return [rich_profile_payload(db, user, p, active_id) for p in rows]


@router.post("/profiles")
def create_profile(data: ProfileCreateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    ensure_default_profile(db, user)
    rows = db.query(Profile).filter(Profile.user_id == user.id).all()
    if len(rows) >= 5:
        raise HTTPException(409, "Family plan supports a maximum of five profiles.")
    normalized = data.name.strip().casefold()
    if any(decrypt_text(p.name_enc).strip().casefold() == normalized for p in rows):
        raise HTTPException(409, "A profile with that display name already exists.")
    profile = Profile(user_id=user.id, name_enc=encrypt_text(data.name.strip()))
    db.add(profile); db.flush()
    set_preferences(
        db, user.id, profile.id,
        preferred_genres=data.preferred_genres,
        disliked_genres=data.disliked_genres,
        preferred_moods=data.preferred_moods,
    )
    db.commit(); db.refresh(profile)
    return rich_profile_payload(db, user, profile, active_profile_id(db, user))


@router.put("/profiles/{profile_id}")
def update_profile(profile_id: int, data: ProfileUpdateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    profile = owned_profile(db, user.id, profile_id)
    if data.name is not None:
        normalized = data.name.strip().casefold()
        peers = db.query(Profile).filter(Profile.user_id == user.id, Profile.id != profile_id).all()
        if any(decrypt_text(p.name_enc).strip().casefold() == normalized for p in peers):
            raise HTTPException(409, "A profile with that display name already exists.")
        profile.name_enc = encrypt_text(data.name.strip())
    set_preferences(
        db, user.id, profile.id,
        preferred_genres=data.preferred_genres,
        disliked_genres=data.disliked_genres,
        preferred_moods=data.preferred_moods,
    )
    db.commit(); db.refresh(profile)
    return rich_profile_payload(db, user, profile, active_profile_id(db, user))


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    rows = db.query(Profile).filter(Profile.user_id == user.id).order_by(Profile.id).all()
    if len(rows) <= 1:
        raise HTTPException(409, "At least one profile must remain.")
    profile = owned_profile(db, user.id, profile_id)
    active = db.get(ActiveProfile, user.id)
    if active and active.profile_id == profile_id:
        replacement = next(x for x in rows if x.id != profile_id)
        active.profile_id = replacement.id
        db.flush()
    # Sessions remain as audit history, but votes/preferences/history owned by this profile are removed.
    db.query(GroupVote).filter(GroupVote.profile_id == profile_id).delete(synchronize_session=False)
    db.query(ProfileWatchEvent).filter(ProfileWatchEvent.profile_id == profile_id, ProfileWatchEvent.user_id == user.id).delete(synchronize_session=False)
    db.query(ProfilePreference).filter(ProfilePreference.profile_id == profile_id, ProfilePreference.user_id == user.id).delete(synchronize_session=False)
    db.query(PlannerActivity).filter(PlannerActivity.profile_id == profile_id, PlannerActivity.user_id == user.id).update({PlannerActivity.profile_id: None}, synchronize_session=False)
    db.delete(profile); db.commit()
    return {"ok": True, "active_profile_id": active_profile_id(db, user)}


@router.post("/profiles/switch")
def switch_profile(data: ProfileSwitchRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    ensure_default_profile(db, user)
    profile = owned_profile(db, user.id, data.profile_id)
    active = db.query(ActiveProfile).filter(ActiveProfile.user_id == user.id).first()
    if not active:
        active = ActiveProfile(user_id=user.id, profile_id=profile.id); db.add(active)
    else:
        active.profile_id = profile.id
    db.commit()
    return rich_profile_payload(db, user, profile, profile.id)


@router.get("/profiles/{profile_id}/preferences")
def get_profile_preferences(profile_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    owned_profile(db, user.id, profile_id)
    snapshot = profile_learning_snapshot(db, user.id, profile_id)
    return snapshot


@router.get("/profiles/{profile_id}/history")
def profile_history(profile_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    owned_profile(db, user.id, profile_id)
    rows = (db.query(ProfileWatchEvent)
            .filter(ProfileWatchEvent.profile_id == profile_id, ProfileWatchEvent.user_id == user.id)
            .order_by(ProfileWatchEvent.created_at.desc()).limit(100).all())
    output = []
    for event in rows:
        try:
            movie_id = int(decrypt_text(event.movie_id_enc)); movie = db.get(Movie, movie_id)
        except Exception:
            movie = None
        if not movie: continue
        try:
            rating = float(decrypt_text(event.rating_enc)) if event.rating_enc else None
        except Exception:
            rating = None
        output.append({"movie": movie_dict(movie), "watched": event.watched, "rating": rating, "created_at": event.created_at})
    return output


@router.post("/groups")
def create_group_session(data: GroupChoiceRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    profiles = validate_profile_ids(db, user, data.profile_ids)
    session_id = uuid.uuid4().hex
    row = GroupSession(
        id=session_id, family_id=user.id,
        selected_profile_ids_json=json.dumps([p.id for p in profiles]),
        request_text=data.request_text.strip(), mood=(data.mood or ""), free_minutes=data.free_minutes,
        status="open",
    )
    db.add(row); db.commit(); db.refresh(row)
    return {
        "session_id": row.id,
        "status": row.status,
        "members": [{"id": p.id, "name": decrypt_text(p.name_enc)} for p in profiles],
        "request_text": row.request_text,
        "mood": row.mood or None,
        "free_minutes": row.free_minutes,
    }


def run_group_recommendation(db: Session, user, row: GroupSession):
    profile_ids = json.loads(row.selected_profile_ids_json or "[]")
    profiles = validate_profile_ids(db, user, profile_ids)
    snapshots = [(p, profile_learning_snapshot(db, user.id, p.id)) for p in profiles]

    genre_counts, mood_counts, disliked_counts = Counter(), Counter(), Counter()
    for _, snap in snapshots:
        for g in set((snap.get("preferred_genres") or []) + (snap.get("learned_genres") or [])): genre_counts[g] += 1
        for m in set((snap.get("preferred_moods") or []) + (snap.get("learned_moods") or [])): mood_counts[m] += 1
        for g in set(snap.get("disliked_genres") or []): disliked_counts[g] += 1
    genres = [g for g,_ in genre_counts.most_common(5)]
    mood = row.mood or (mood_counts.most_common(1)[0][0] if mood_counts else None)
    # Do not hard-filter a genre disliked by only one person; consensus scoring applies a strong penalty instead.
    hard_disliked = [g for g,count in disliked_counts.items() if count == len(profiles)]
    prefs = {"genres": genres, "mood": mood, "time_available": row.free_minutes, "disliked": hard_disliked}
    query = (row.request_text or "family group movie") + " " + " ".join(genres) + " " + (mood or "")
    trace_id = str(uuid.uuid4())
    env = AgentEnvelope(trace_id=trace_id, sender="orchestrator", receiver="retrieval", intent="family_group_recommend", payload={"session_id": row.id, "profile_ids": profile_ids, "preferences": prefs})
    candidates = orchestrator.retrieval.retrieve(db, env, query.strip(), prefs, 0, limit=24)

    scored = []
    score_map = {}
    for item in candidates:
        movie = db.get(Movie, item["id"])
        if not movie: continue
        consensus = consensus_for_movie(movie, snapshots, mood)
        enriched = {**item, "consensus": consensus, "group_score": consensus["group_score"]}
        enriched["reason"] = (
            f"Fits {consensus['satisfied_members']}/{consensus['member_count']} selected members"
            + (f" with {consensus['conflict_count']} preference conflict" if consensus['conflict_count'] == 1 else (f" with {consensus['conflict_count']} preference conflicts" if consensus['conflict_count'] else " with no major disliked-genre conflicts"))
            + "."
        )
        scored.append(enriched)
        score_map[str(movie.id)] = consensus
    scored.sort(key=lambda x: (x["group_score"], x.get("rating", 0)), reverse=True)
    row.candidate_scores_json = json.dumps(score_map)
    row.status = "recommended"
    db.commit()
    return {
        "trace_id": trace_id,
        "session_id": row.id,
        "status": row.status,
        "members": [{"id": p.id, "name": decrypt_text(p.name_enc), "snapshot": snap} for p,snap in snapshots],
        "shared_preferences": prefs,
        "results": scored[:12],
    }


@router.post("/groups/{session_id}/recommend")
def group_recommend(session_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    row = session_or_404(db, user, session_id)
    return run_group_recommendation(db, user, row)


# Backwards-compatible endpoint used by earlier frontend builds: create session + recommend in one call.
@router.post("/group-choice")
def group_choice(data: GroupChoiceRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    created = create_group_session(data, db, user)
    row = session_or_404(db, user, created["session_id"])
    return run_group_recommendation(db, user, row)


@router.get("/groups/{session_id}")
def group_session_detail(session_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    row = session_or_404(db, user, session_id)
    ids = json.loads(row.selected_profile_ids_json or "[]")
    profiles = db.query(Profile).filter(Profile.user_id == user.id, Profile.id.in_(ids)).all()
    votes = db.query(GroupVote).filter(GroupVote.session_id == row.id).all()
    return {
        "session_id": row.id, "status": row.status, "request_text": row.request_text,
        "mood": row.mood or None, "free_minutes": row.free_minutes,
        "winner_movie_id": row.winner_movie_id,
        "members": [{"id": p.id, "name": decrypt_text(p.name_enc)} for p in profiles],
        "votes": [{"profile_id": v.profile_id, "movie_id": v.movie_id, "created_at": v.created_at} for v in votes],
    }


@router.post("/groups/{session_id}/compare")
async def group_compare(session_id: str, data: GroupCompareRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    row = session_or_404(db, user, session_id)
    score_map = json.loads(row.candidate_scores_json or "{}")
    if any(str(mid) not in score_map for mid in data.movie_ids):
        raise HTTPException(400, "Compare movies from this group session's recommendation set.")
    profile_ids = json.loads(row.selected_profile_ids_json or "[]")
    profiles = validate_profile_ids(db, user, profile_ids)
    names = [decrypt_text(p.name_enc) for p in profiles]
    note = f"Family group members: {', '.join(names)}. Use the supplied group consensus data and explain the best compromise for the participating members."
    result = await orchestrator.compare_movies(db, user, data.movie_ids, row.mood or None, note)
    consensus_rows = []
    for mid in data.movie_ids:
        movie = db.get(Movie, mid)
        c = score_map[str(mid)]
        consensus_rows.append({"movie_id": mid, "title": movie.title if movie else str(mid), **c})
    consensus_rows.sort(key=lambda x: x["group_score"], reverse=True)
    winner = consensus_rows[0]
    result["group_consensus"] = consensus_rows
    result["winner_id"] = winner["movie_id"]
    result["explanation"] = (
        f"{winner['title']} is the strongest family compromise: it satisfies {winner['satisfied_members']}/{winner['member_count']} participating profiles "
        f"with a {winner['group_score']}% consensus score and {winner['conflict_count']} major preference conflict(s). "
        + result.get("explanation", "")
    )
    return result


@router.post("/groups/{session_id}/vote")
def group_vote(session_id: str, data: GroupVoteRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    row = session_or_404(db, user, session_id)
    profile_ids = json.loads(row.selected_profile_ids_json or "[]")
    if data.profile_id not in profile_ids:
        raise HTTPException(403, "Only profiles participating in this group session can vote.")
    owned_profile(db, user.id, data.profile_id)
    score_map = json.loads(row.candidate_scores_json or "{}")
    if str(data.movie_id) not in score_map:
        raise HTTPException(400, "Vote for a movie from this group's recommendation set.")
    if not db.get(Movie, data.movie_id):
        raise HTTPException(404, "Movie not found.")
    vote = db.query(GroupVote).filter(GroupVote.session_id == row.id, GroupVote.profile_id == data.profile_id).first()
    if vote:
        vote.movie_id = data.movie_id
    else:
        db.add(GroupVote(session_id=row.id, profile_id=data.profile_id, movie_id=data.movie_id))
    row.status = "voting"
    db.commit()
    return final_selection_payload(db, row)


def final_selection_payload(db: Session, row: GroupSession) -> dict:
    score_map = json.loads(row.candidate_scores_json or "{}")
    profile_ids = json.loads(row.selected_profile_ids_json or "[]")
    votes = db.query(GroupVote).filter(GroupVote.session_id == row.id).all()
    vote_counts = Counter(v.movie_id for v in votes)
    member_count = max(1, len(profile_ids))
    candidate_ids = {int(k) for k in score_map} | set(vote_counts)
    ranking = []
    for movie_id in candidate_ids:
        consensus = float((score_map.get(str(movie_id)) or {}).get("group_score", 0.0))
        count = vote_counts.get(movie_id, 0)
        vote_share = count / member_count * 100.0
        final_score = consensus * .65 + vote_share * .35
        movie = db.get(Movie, movie_id)
        ranking.append({
            "movie_id": movie_id, "title": movie.title if movie else str(movie_id),
            "group_score": round(consensus, 1), "votes": count, "vote_share": round(vote_share, 1),
            "final_score": round(final_score, 1),
        })
    ranking.sort(key=lambda x: (x["final_score"], x["votes"], x["group_score"]), reverse=True)
    winner = ranking[0] if ranking else None
    if winner:
        row.winner_movie_id = winner["movie_id"]
        if len(votes) >= len(profile_ids): row.status = "complete"
        db.commit()
    return {
        "session_id": row.id, "status": row.status,
        "votes_cast": len(votes), "members": len(profile_ids),
        "ranking": ranking,
        "winner": winner,
        "explanation": (
            f"{winner['title']} currently leads because it combines a {winner['group_score']}% AI consensus score with {winner['votes']} family vote(s). "
            "The final score intentionally keeps human voting influential while preserving group compatibility."
            if winner else "No final choice is available yet."
        ),
    }


@router.get("/groups/{session_id}/result")
def group_result(session_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user)
    row = session_or_404(db, user, session_id)
    return final_selection_payload(db, row)
