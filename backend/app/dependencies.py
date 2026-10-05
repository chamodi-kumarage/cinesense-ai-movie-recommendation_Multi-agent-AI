from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .models import User
from .security import decode_access_token

def get_current_user(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    user_id = decode_access_token(access_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User account not found.")
    return user

def get_optional_user(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User | None:
    """Return the cookie user when available, keeping public catalogue browsing anonymous."""
    if not access_token:
        return None
    user_id=decode_access_token(access_token)
    return db.get(User,user_id) if user_id else None

def require_consent(user: User = Depends(get_current_user)) -> User:
    if not user.consented:
        raise HTTPException(status_code=403, detail="Please review and accept the AI/privacy notice first.")
    return user


def require_admin(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    from .models import AdminAccount
    admin = db.get(AdminAccount, user.id)
    if not admin or not admin.active:
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user
