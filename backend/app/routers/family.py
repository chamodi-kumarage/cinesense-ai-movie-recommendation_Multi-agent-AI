import hashlib, json, secrets, uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..db import get_db
from ..dependencies import get_current_user
from ..models import (
    Profile, ActiveProfile, ProfileWatchEvent, ProfilePreference, Movie,
    GroupSession, GroupVote, PlannerActivity, User, FamilyGroup, FamilyMember, FamilyInvite,
)
from ..schemas import (
    ProfileCreateRequest, ProfileUpdateRequest, ProfileSwitchRequest,
    GroupChoiceRequest, GroupCompareRequest, GroupVoteRequest, FamilyInviteCreateRequest,
    FamilyInviteAcceptRequest, FamilyMemberRoleRequest,
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

MAX_FAMILY_PEOPLE = 5

def now_utc():
    return datetime.now(timezone.utc)

def active_membership(db: Session, user_id: int):
    return db.query(FamilyMember).filter(FamilyMember.user_id == user_id, FamilyMember.status == "active").first()

def owner_group(db: Session, user, create: bool = False):
    group = db.query(FamilyGroup).filter(FamilyGroup.owner_user_id == user.id).first()
    if not group and create:
        if user.plan != "family":
            raise HTTPException(403, "A Family subscription is required to create a household.")
        group = FamilyGroup(owner_user_id=user.id, plan="family")
        db.add(group); db.flush()
        db.add(FamilyMember(family_group_id=group.id, user_id=user.id, role="owner", status="active"))
        db.commit(); db.refresh(group)
    return group

def family_access(db: Session, user):
    membership = active_membership(db, user.id)
    if membership:
        return db.get(FamilyGroup, membership.family_group_id), membership
    if user.plan == "family":
        group = owner_group(db, user, create=True)
        return group, active_membership(db, user.id)
    raise HTTPException(403, "Family profiles and group choice require an active Family household membership.")

def require_owner(db: Session, user):
    group, membership = family_access(db, user)
    if not membership or membership.role != "owner" or group.owner_user_id != user.id:
        raise HTTPException(403, "Only the Family plan owner can manage household members.")
    return group

def member_payload(db: Session, member: FamilyMember):
    account = db.get(User, member.user_id)
    profile = ensure_default_profile(db, account) if account else None
    return {"id": member.id, "user_id": member.user_id, "email": account.email if account else "", "display_name": decrypt_text(account.display_name_enc) if account else "", "profile_id": profile.id if profile else None, "role": member.role, "status": member.status, "is_owner": member.role == "owner", "participant_type": "account", "created_at": member.created_at}

def family_owner_id(db: Session, user) -> int:
    group, _ = family_access(db, user)
    return group.owner_user_id

def allowed_family_profiles(db: Session, user) -> list[Profile]:
    group, _ = family_access(db, user)
    members = db.query(FamilyMember).filter(FamilyMember.family_group_id == group.id, FamilyMember.status == "active").all()
    account_profile_ids = []
    for member in members:
        account = db.get(User, member.user_id)
        if account:
            account_profile_ids.append(ensure_default_profile(db, account).id)
    account_profiles = db.query(Profile).filter(Profile.id.in_(account_profile_ids or [-1])).all()
    return account_profiles


def require_family(user, db: Session | None = None):
    if user.plan != "family" and (db is None or not active_membership(db, user.id)):
        raise HTTPException(403, "Family profiles and group choice require the Family plan.")

@router.get("/household")
def household(db: Session = Depends(get_db), user=Depends(get_current_user)):
    group, membership = family_access(db, user)
    members = db.query(FamilyMember).filter(FamilyMember.family_group_id == group.id, FamilyMember.status == "active").order_by(FamilyMember.id).all()
    pending = db.query(FamilyInvite).filter(FamilyInvite.family_group_id == group.id, FamilyInvite.status == "pending").order_by(FamilyInvite.created_at.desc()).all()
    current = now_utc()
    for invite in pending:
        expires = invite.expires_at if invite.expires_at.tzinfo else invite.expires_at.replace(tzinfo=timezone.utc)
        if expires <= current: invite.status = "expired"
    db.commit()
    member_rows = [member_payload(db, m) for m in members]
    for row, member in zip(member_rows, members):
        if member.role not in {"owner", "member"}:
            member.role = "member"
            row["role"] = "member"
    participants = [{"id": m["profile_id"], "name": m["display_name"] or m["email"].split("@")[0], "subtitle": m["email"], "participant_type": "account", "role": m["role"], "user_id": m["user_id"]} for m in member_rows if m["profile_id"]]
    db.commit()
    return {"group_id": group.id, "owner_user_id": group.owner_user_id, "current_role": membership.role, "can_manage": membership.role == "owner", "max_members": MAX_FAMILY_PEOPLE, "members": member_rows, "participants": participants, "pending_invites": [{"id": i.id, "email": i.invited_email, "status": i.status, "expires_at": i.expires_at, "created_at": i.created_at} for i in pending if i.status == "pending"]}

@router.get("/members")
def list_household_members(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return household(db, user)

@router.post("/invites")
def create_family_invite(data: FamilyInviteCreateRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    group = require_owner(db, user)
    email = str(data.email).strip().lower()
    target = db.query(User).filter(User.email == email).first()
    active_count = db.query(FamilyMember).filter(FamilyMember.family_group_id == group.id, FamilyMember.status == "active").count()
    pending_count = db.query(FamilyInvite).filter(FamilyInvite.family_group_id == group.id, FamilyInvite.status == "pending", FamilyInvite.expires_at > now_utc()).count()
    if active_count + pending_count >= MAX_FAMILY_PEOPLE:
        raise HTTPException(409, "Family plan supports a maximum of five people, including pending invitations.")
    if target and active_membership(db, target.id):
        raise HTTPException(409, "That user already belongs to a family household.")
    existing = db.query(FamilyInvite).filter(FamilyInvite.family_group_id == group.id, FamilyInvite.invited_email == email, FamilyInvite.status == "pending").first()
    if existing:
        existing.status = "expired"
    raw_token = secrets.token_urlsafe(32)
    invite = FamilyInvite(family_group_id=group.id, invited_email=email, invited_by_user_id=user.id, role="member", token_hash=hashlib.sha256(raw_token.encode()).hexdigest(), status="pending", expires_at=now_utc() + timedelta(days=7))
    db.add(invite); db.commit(); db.refresh(invite)
    return {"id": invite.id, "email": email, "role": "member", "status": invite.status, "expires_at": invite.expires_at, "token": raw_token, "invite_path": f"/?family_invite={raw_token}", "message": "Invitation created. Share this demo link with the invited person."}

@router.post("/invites/accept")
def accept_family_invite(data: FamilyInviteAcceptRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    token_hash = hashlib.sha256(data.token.encode()).hexdigest()
    invite = db.query(FamilyInvite).filter(FamilyInvite.token_hash == token_hash).first()
    if not invite or invite.status != "pending":
        raise HTTPException(400, "This family invitation is invalid or has already been used.")
    expires = invite.expires_at if invite.expires_at.tzinfo else invite.expires_at.replace(tzinfo=timezone.utc)
    if expires <= now_utc():
        invite.status = "expired"; db.commit()
        raise HTTPException(400, "This family invitation has expired.")
    if invite.invited_email.casefold() != user.email.casefold():
        raise HTTPException(403, f"Sign in as {invite.invited_email} to accept this invitation.")
    if active_membership(db, user.id):
        raise HTTPException(409, "You already belong to a family household.")
    active_count = db.query(FamilyMember).filter(FamilyMember.family_group_id == invite.family_group_id, FamilyMember.status == "active").count()
    if active_count >= MAX_FAMILY_PEOPLE:
        raise HTTPException(409, "This family household is already full.")
    db.add(FamilyMember(family_group_id=invite.family_group_id, user_id=user.id, role="member", status="active"))
    invite.status = "accepted"; db.commit()
    return {"ok": True, "message": "You joined the CineSense family household.", "group_id": invite.family_group_id}

@router.patch("/members/{member_id}/role")
def update_member_role(member_id: int, data: FamilyMemberRoleRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    group = require_owner(db, user)
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id, FamilyMember.family_group_id == group.id, FamilyMember.status == "active").first()
    if not member: raise HTTPException(404, "Family member not found.")
    if member.role == "owner": raise HTTPException(409, "The owner role cannot be changed here.")
    member.role = data.role; db.commit(); db.refresh(member)
    return member_payload(db, member)

@router.delete("/members/{member_id}")
def remove_household_member(member_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    group = require_owner(db, user)
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id, FamilyMember.family_group_id == group.id, FamilyMember.status == "active").first()
    if not member: raise HTTPException(404, "Family member not found.")
    if member.role == "owner": raise HTTPException(409, "The Family owner cannot remove themselves.")
    member.status = "removed"; db.commit()
    return {"ok": True, "message": "Family member removed."}


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
    allowed = {p.id: p for p in allowed_family_profiles(db, user)}
    profiles = [allowed[i] for i in ids if i in allowed]
    if len(profiles) != len(ids):
        raise HTTPException(400, "One or more selected profiles do not belong to this Family account.")
    order = {pid: i for i, pid in enumerate(ids)}
    return sorted(profiles, key=lambda p: order[p.id])


def session_or_404(db: Session, user, session_id: str) -> GroupSession:
    row = db.query(GroupSession).filter(GroupSession.id == session_id, GroupSession.family_id == family_owner_id(db, user)).first()
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
    require_owner(db, user)
    raise HTTPException(410, "Separate Family profiles were removed. Invite each family member with their own account.")
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
    require_owner(db, user)
    raise HTTPException(410, "Separate Family profiles were removed. Preferences belong to each member account.")
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
    require_owner(db, user)
    raise HTTPException(410, "Separate Family profiles were removed. Remove the household member instead.")
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
    raise HTTPException(410, "Profile switching was removed. The signed-in account is always the active participant.")
    require_family(user, db)
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
    require_family(user, db)
    owned_profile(db, user.id, profile_id)
    snapshot = profile_learning_snapshot(db, user.id, profile_id)
    return snapshot


@router.get("/profiles/{profile_id}/history")
def profile_history(profile_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    require_family(user, db)
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
    require_family(user, db)
    profiles = validate_profile_ids(db, user, data.profile_ids)
    session_id = uuid.uuid4().hex
    row = GroupSession(
        id=session_id, family_id=family_owner_id(db, user),
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
    snapshots = [(p, profile_learning_snapshot(db, p.user_id, p.id)) for p in profiles]

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
    require_family(user, db)
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
    require_family(user, db)
    row = session_or_404(db, user, session_id)
    ids = json.loads(row.selected_profile_ids_json or "[]")
    profiles = validate_profile_ids(db, user, ids)
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
    require_family(user, db)
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
    require_family(user, db)
    row = session_or_404(db, user, session_id)
    profile_ids = json.loads(row.selected_profile_ids_json or "[]")
    if data.profile_id not in profile_ids:
        raise HTTPException(403, "Only profiles participating in this group session can vote.")
    selected_profile = next((p for p in validate_profile_ids(db, user, profile_ids) if p.id == data.profile_id), None)
    if not selected_profile:
        raise HTTPException(403, "This participant is not available in your Family household.")
    _, membership = family_access(db, user)
    if membership.role != "owner" and selected_profile.user_id != user.id:
        raise HTTPException(403, "Family members can vote only as their own account.")
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
    require_family(user, db)
    row = session_or_404(db, user, session_id)
    return final_selection_payload(db, row)
