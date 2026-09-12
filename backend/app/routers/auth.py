from fastapi import APIRouter,Depends,HTTPException,Response,Request
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User,AdminAccount,LoginSecurityState,SecurityEvent
from ..schemas import RegisterRequest,LoginRequest,ConsentRequest
from ..security import hash_password,verify_password,create_access_token,encrypt_text,decrypt_text
import hashlib
from datetime import datetime, timezone, timedelta
from ..dependencies import get_current_user
from ..config import get_settings
router=APIRouter(prefix="/api/auth",tags=["auth"]);settings=get_settings()

def user_payload(user,db=None):
    is_admin=bool(db and db.query(AdminAccount).filter(AdminAccount.user_id==user.id,AdminAccount.active==True).first())
    return {"id":user.id,"email":user.email,"display_name":decrypt_text(user.display_name_enc),"consented":user.consented,"plan":user.plan,"is_admin":is_admin}
def set_cookie(response,user):
    response.set_cookie("access_token",create_access_token(user.id),httponly=True,samesite="lax",
                        secure=settings.environment=="production",max_age=settings.access_token_minutes*60,path="/")

@router.post("/register")
def register(data:RegisterRequest,response:Response,db:Session=Depends(get_db)):
    email=data.email.lower()
    if db.query(User).filter(User.email==email).first():raise HTTPException(409,"An account with that email already exists.")
    user=User(email=email,password_hash=hash_password(data.password),display_name_enc=encrypt_text(data.display_name),consented=False,plan="free")
    db.add(user);db.commit();db.refresh(user);set_cookie(response,user);return user_payload(user,db)

@router.post("/login")
def login(data:LoginRequest,response:Response,request:Request,db:Session=Depends(get_db)):
    email=data.email.lower().strip()
    remote=(request.client.host if request.client else "unknown")
    key=hashlib.sha256(f"{remote}|{email}".encode()).hexdigest()
    state=db.get(LoginSecurityState,key)
    now=datetime.now(timezone.utc)
    if state and state.locked_until:
        locked=state.locked_until
        if locked.tzinfo is None: locked=locked.replace(tzinfo=timezone.utc)
        if locked>now:
            raise HTTPException(429,"Too many failed sign-in attempts. Try again later.")
    user=db.query(User).filter(User.email==email).first()
    if not user or not verify_password(data.password,user.password_hash):
        if not state:
            state=LoginSecurityState(key_hash=key,failures=0);db.add(state)
        state.failures+=1
        if state.failures>=settings.login_max_failures:
            state.locked_until=now+timedelta(minutes=settings.login_lock_minutes)
        db.add(SecurityEvent(category="authentication",severity="warning",detail_safe=f"failed_login:{email[:2]}***"))
        db.commit()
        raise HTTPException(401,"Email or password is incorrect.")
    if state:
        state.failures=0;state.locked_until=None
    db.add(SecurityEvent(user_id=user.id,category="authentication",severity="info",detail_safe="successful_login"))
    db.commit()
    set_cookie(response,user);return user_payload(user,db)

@router.post("/demo")
def demo(response:Response,db:Session=Depends(get_db)):
    if not settings.enable_demo_account:raise HTTPException(404,"Demo account is disabled.")
    user=db.query(User).filter(User.email=="demo@cinesense.ai").first()
    if not user:raise HTTPException(404,"Demo account is not available.")
    set_cookie(response,user);return user_payload(user,db)

@router.post("/logout")
def logout(response:Response):
    response.delete_cookie("access_token",path="/");return {"ok":True}

@router.get("/me")
def me(db:Session=Depends(get_db),user=Depends(get_current_user)):return user_payload(user,db)

@router.post("/consent")
def consent(data:ConsentRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    if not data.accepted:raise HTTPException(400,"Consent must be accepted to use AI features.")
    user.consented=True;db.commit();return user_payload(user,db)
