from fastapi import APIRouter,Depends,HTTPException,Response,Request
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import (User,AdminAccount,LoginSecurityState,SecurityEvent,ChatTurn,ProfileConversationState,ConversationState,Profile,ActiveProfile,ProfileWatchEvent,ProfilePreference,FamilyProfileSafety,PlannerActivity,RecommendationFeedback,SavedPlan,WatchEvent,AIUsage,AgentTrace,Subscription,BillingProfile,CalendarConnection,CalendarBusySlot,FamilyMember,FamilyInvite,FamilyWatchlistItem,FamilyWatchlistVote,GroupVote,GroupSession,FamilyNotification,FamilyGroup)
from ..schemas import RegisterRequest,LoginRequest,ConsentRequest
from ..security import hash_password,verify_password,create_access_token,encrypt_text,decrypt_text
import hashlib
from datetime import datetime, timezone, timedelta
from ..dependencies import get_current_user
from ..config import get_settings
router=APIRouter(prefix="/api/auth",tags=["auth"]);settings=get_settings()
account_router=APIRouter(prefix="/api/account",tags=["account"])

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
    user.consented=data.accepted;db.commit();return user_payload(user,db)

@account_router.get("/export")
def export_account(db:Session=Depends(get_db),user=Depends(get_current_user)):
    """Export account-owned data as JSON; encrypted application fields remain encrypted at rest."""
    from ..models import Base
    owned = [ChatTurn,ProfileConversationState,ConversationState,Profile,ActiveProfile,ProfileWatchEvent,ProfilePreference,FamilyProfileSafety,PlannerActivity,RecommendationFeedback,SavedPlan,WatchEvent,AIUsage,AgentTrace,Subscription,BillingProfile,CalendarConnection,CalendarBusySlot]
    result={"account":{"id":user.id,"email":user.email,"display_name":decrypt_text(user.display_name_enc),"consented":user.consented,"plan":user.plan,"created_at":user.created_at.isoformat()}}
    for model in owned:
        query=db.query(model)
        if "user_id" in model.__table__.columns: query=query.filter(model.user_id==user.id)
        elif model is ProfileConversationState: query=query.filter(model.profile_id.in_(db.query(Profile.id).filter(Profile.user_id==user.id)))
        else: continue
        records=[]
        for row in query.all():
            record={}
            for column in model.__table__.columns:
                name=column.name; value=getattr(row,name)
                if name in {"access_token_enc","refresh_token_enc"}:
                    value="[redacted]" if value else ""
                elif name.endswith("_enc") and value:
                    value=decrypt_text(value)
                if hasattr(value,"isoformat"): value=value.isoformat()
                record[name]=value
            records.append(record)
        result[model.__tablename__]=records
    return result

@account_router.delete("")
def delete_account(db:Session=Depends(get_db),user=Depends(get_current_user)):
    uid=user.id
    profile_ids=[r[0] for r in db.query(Profile.id).filter(Profile.user_id==uid).all()]
    # Remove rows keyed by profiles before deleting profiles; shared family records are retained.
    if profile_ids:
        for model in (FamilyWatchlistVote,GroupVote): db.query(model).filter(model.profile_id.in_(profile_ids)).delete(synchronize_session=False)
        for model in (ProfileConversationState,ProfilePreference,FamilyProfileSafety,ActiveProfile): db.query(model).filter(model.profile_id.in_(profile_ids)).delete(synchronize_session=False)
        db.query(FamilyWatchlistItem).filter(FamilyWatchlistItem.added_by_profile_id.in_(profile_ids)).update({FamilyWatchlistItem.added_by_profile_id:None},synchronize_session=False)
    owned_groups=db.query(FamilyGroup.id).filter(FamilyGroup.owner_user_id==uid).all()
    group_ids=[r[0] for r in owned_groups]
    if group_ids:
        session_ids=[r[0] for r in db.query(GroupSession.id).filter(GroupSession.family_id==uid).all()]
        if session_ids: db.query(GroupVote).filter(GroupVote.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(GroupSession).filter(GroupSession.family_id==uid).delete(synchronize_session=False)
        db.query(FamilyNotification).filter(FamilyNotification.family_group_id.in_(group_ids)).delete(synchronize_session=False)
        db.query(FamilyWatchlistVote).filter(FamilyWatchlistVote.item_id.in_(db.query(FamilyWatchlistItem.id).filter(FamilyWatchlistItem.family_group_id.in_(group_ids)))).delete(synchronize_session=False)
        db.query(FamilyWatchlistItem).filter(FamilyWatchlistItem.family_group_id.in_(group_ids)).delete(synchronize_session=False)
        db.query(FamilyInvite).filter(FamilyInvite.family_group_id.in_(group_ids)).delete(synchronize_session=False)
        db.query(FamilyMember).filter(FamilyMember.family_group_id.in_(group_ids)).delete(synchronize_session=False)
        db.query(FamilyGroup).filter(FamilyGroup.id.in_(group_ids)).delete(synchronize_session=False)
    for model in (ChatTurn,ConversationState,ProfileWatchEvent,PlannerActivity,RecommendationFeedback,SavedPlan,WatchEvent,AIUsage,AgentTrace,Subscription,BillingProfile,CalendarConnection,CalendarBusySlot):
        db.query(model).filter(model.user_id==uid).delete(synchronize_session=False)
    db.query(FamilyInvite).filter(FamilyInvite.invited_by_user_id==uid).delete(synchronize_session=False)
    db.query(FamilyMember).filter(FamilyMember.user_id==uid).delete(synchronize_session=False)
    db.query(FamilyWatchlistItem).filter(FamilyWatchlistItem.added_by_user_id==uid).delete(synchronize_session=False)
    db.query(AdminAccount).filter(AdminAccount.user_id==uid).delete(synchronize_session=False)
    db.query(Profile).filter(Profile.user_id==uid).delete(synchronize_session=False)
    db.query(SecurityEvent).filter(SecurityEvent.user_id==uid).delete(synchronize_session=False)
    db.delete(user);db.commit()
    return Response(status_code=204)
