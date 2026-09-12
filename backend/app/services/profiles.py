from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..models import Profile, ActiveProfile
from ..security import encrypt_text, decrypt_text


def ensure_default_profile(db: Session, user) -> Profile:
    """Return a stable default profile and ensure one active-profile row exists.

    Planner widgets load several endpoints in parallel. On a fresh account those
    requests can race while creating the initial ActiveProfile row. The
    user_id column is unique/primary-keyed, so the losing request previously
    raised an IntegrityError. This helper is intentionally idempotent and
    recovers from that race by rolling back and re-reading the row created by
    the other request.
    """
    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user.id)
        .order_by(Profile.id)
        .first()
    )
    if not profile:
        name = decrypt_text(user.display_name_enc) or "Primary"
        profile = Profile(user_id=user.id, name_enc=encrypt_text(name[:50]))
        db.add(profile)
        db.commit()
        db.refresh(profile)

    active = db.query(ActiveProfile).filter(ActiveProfile.user_id == user.id).first()
    if not active:
        try:
            db.add(ActiveProfile(user_id=user.id, profile_id=profile.id))
            db.commit()
        except IntegrityError:
            # Another concurrent request created the row after our SELECT.
            db.rollback()
            active = db.query(ActiveProfile).filter(ActiveProfile.user_id == user.id).first()
            if not active:
                raise
    return profile


def active_profile_id(db: Session, user) -> int:
    profile = ensure_default_profile(db, user)
    active = db.query(ActiveProfile).filter(ActiveProfile.user_id == user.id).first()
    return active.profile_id if active else profile.id


def profile_payload(profile: Profile, active_id: int | None = None):
    return {"id": profile.id, "name": decrypt_text(profile.name_enc), "active": profile.id == active_id}
