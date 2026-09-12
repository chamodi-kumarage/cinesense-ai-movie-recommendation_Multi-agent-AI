import hashlib, hmac, json, math, time
from datetime import datetime, timezone
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from ..db import get_db
from ..dependencies import get_current_user
from ..models import Subscription, BillingProfile
from ..schemas import CheckoutRequest, SimulatedBillingProfileRequest, SimulatedSubscribeRequest
from ..config import get_settings
from ..security import encrypt_text, decrypt_text

router=APIRouter(prefix="/api/billing",tags=["billing"]); settings=get_settings()


def _price_id(plan): return settings.stripe_premium_price_id if plan=="premium" else settings.stripe_family_price_id

def _upsert(db,user_id,plan,status,customer_id="",subscription_id="",cancel=False):
    row=db.query(Subscription).filter(Subscription.user_id==user_id).first()
    if not row: row=Subscription(user_id=user_id); db.add(row)
    row.plan=plan; row.status=status; row.provider_customer_id=customer_id or row.provider_customer_id
    row.provider_subscription_id=subscription_id or row.provider_subscription_id; row.cancel_at_period_end=cancel
    db.commit(); return row

@router.get("/status")
def status(db:Session=Depends(get_db),user=Depends(get_current_user)):
    row=db.query(Subscription).filter(Subscription.user_id==user.id).first()
    return {"plan":user.plan,"provider":"stripe" if row else None,"status":row.status if row else "none","cancel_at_period_end":row.cancel_at_period_end if row else False,"configured":bool(settings.stripe_secret_key and settings.stripe_webhook_secret)}

@router.post("/checkout")
async def checkout(data:CheckoutRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    if not settings.stripe_secret_key: raise HTTPException(503,"Stripe is not configured. Set STRIPE_SECRET_KEY and price IDs.")
    price_id=_price_id(data.plan)
    if not price_id: raise HTTPException(503,f"Stripe price ID for {data.plan} is not configured.")
    form=[("mode","subscription"),("success_url",settings.public_app_url+"/?billing=success"),("cancel_url",settings.public_app_url+"/?billing=cancelled"),("client_reference_id",str(user.id)),("customer_email",user.email),("line_items[0][price]",price_id),("line_items[0][quantity]","1"),("metadata[user_id]",str(user.id)),("metadata[plan]",data.plan),("subscription_data[metadata][user_id]",str(user.id)),("subscription_data[metadata][plan]",data.plan)]
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.post("https://api.stripe.com/v1/checkout/sessions",data=form,headers={"Authorization":f"Bearer {settings.stripe_secret_key}"})
    if r.status_code>=300: raise HTTPException(502,"Payment provider rejected checkout creation.")
    payload=r.json(); return {"checkout_url":payload.get("url"),"session_id":payload.get("id")}

@router.post("/cancel")
async def cancel(db:Session=Depends(get_db),user=Depends(get_current_user)):
    row=db.query(Subscription).filter(Subscription.user_id==user.id).first()
    if not row or not row.provider_subscription_id: raise HTTPException(404,"No active Stripe subscription was found.")
    if not settings.stripe_secret_key: raise HTTPException(503,"Stripe is not configured.")
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.post(f"https://api.stripe.com/v1/subscriptions/{row.provider_subscription_id}",data={"cancel_at_period_end":"true"},headers={"Authorization":f"Bearer {settings.stripe_secret_key}"})
    if r.status_code>=300: raise HTTPException(502,"Cancellation request failed at the payment provider.")
    row.cancel_at_period_end=True; row.status="active"; db.commit(); return {"ok":True,"cancel_at_period_end":True}


def _verify_signature(raw:bytes,header:str):
    if not settings.stripe_webhook_secret: return False
    parts={}
    for item in (header or "").split(","):
        if "=" in item:
            k,v=item.split("=",1); parts.setdefault(k,[]).append(v)
    ts=(parts.get("t") or [""])[0]; signatures=parts.get("v1") or []
    try:
        if abs(time.time()-int(ts))>300:return False
    except Exception:return False
    expected=hmac.new(settings.stripe_webhook_secret.encode(),ts.encode()+b"."+raw,hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected,s) for s in signatures)

@router.post("/stripe/webhook")
async def webhook(request:Request,stripe_signature:str|None=Header(None,alias="Stripe-Signature"),db:Session=Depends(get_db)):
    raw=await request.body()
    if not _verify_signature(raw,stripe_signature or ""): raise HTTPException(400,"Invalid webhook signature.")
    event=json.loads(raw.decode()); obj=(event.get("data") or {}).get("object") or {}; typ=event.get("type","")
    metadata=obj.get("metadata") or {}; uid=metadata.get("user_id") or obj.get("client_reference_id")
    try: user_id=int(uid)
    except Exception: return {"received":True}
    from ..models import User
    user=db.get(User,user_id)
    if not user:return {"received":True}
    plan=metadata.get("plan") or user.plan
    if typ in {"checkout.session.completed","customer.subscription.created","customer.subscription.updated"}:
        status=obj.get("status") or "active"
        if status in {"active","trialing","complete"} and plan in {"premium","family"}: user.plan=plan
        _upsert(db,user.id,plan,status,obj.get("customer") or "",obj.get("subscription") or obj.get("id") or "",bool(obj.get("cancel_at_period_end")))
        db.commit()
    elif typ in {"customer.subscription.deleted"}:
        user.plan="free"; _upsert(db,user.id,"free","canceled",obj.get("customer") or "",obj.get("id") or "",False); db.commit()
    elif typ in {"invoice.payment_failed"}:
        row=db.query(Subscription).filter(Subscription.user_id==user.id).first()
        if row: row.status="past_due"; db.commit()
    return {"received":True}


def _card_brand(number: str) -> str:
    if number.startswith("4"): return "Visa"
    if number[:2] in {"51","52","53","54","55"}: return "Mastercard"
    return "Card"

def _billing_payload(row):
    if not row: return None
    return {
        "id": row.id,
        "cardholder_name": decrypt_text(row.cardholder_name_enc),
        "card_last4": row.card_last4,
        "card_brand": row.card_brand,
        "expiry_month": row.expiry_month,
        "expiry_year": row.expiry_year,
        "billing_address": decrypt_text(row.billing_address_enc),
        "billing_city": decrypt_text(row.billing_city_enc),
        "billing_country": decrypt_text(row.billing_country_enc),
        "updated_at": row.updated_at,
    }

@router.get("/payment-profile")
def get_payment_profile(db:Session=Depends(get_db),user=Depends(get_current_user)):
    row=db.query(BillingProfile).filter(BillingProfile.user_id==user.id).first()
    return {"payment_profile":_billing_payload(row),"simulation":True}

@router.put("/payment-profile")
def save_payment_profile(data:SimulatedBillingProfileRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    row=db.query(BillingProfile).filter(BillingProfile.user_id==user.id).first()
    if not row:
        row=BillingProfile(user_id=user.id,expiry_month=data.expiry_month,expiry_year=data.expiry_year); db.add(row)
    row.cardholder_name_enc=encrypt_text(data.cardholder_name.strip())
    row.card_last4=data.card_number[-4:]
    row.card_brand=_card_brand(data.card_number)
    row.expiry_month=data.expiry_month; row.expiry_year=data.expiry_year
    row.billing_address_enc=encrypt_text(data.billing_address.strip())
    row.billing_city_enc=encrypt_text(data.billing_city.strip())
    row.billing_country_enc=encrypt_text(data.billing_country.strip())
    # CVV and full card number are intentionally validated but never stored.
    db.commit(); db.refresh(row)
    return {"ok":True,"payment_profile":_billing_payload(row),"simulation":True}

@router.delete("/payment-profile")
def delete_payment_profile(db:Session=Depends(get_db),user=Depends(get_current_user)):
    row=db.query(BillingProfile).filter(BillingProfile.user_id==user.id).first()
    if row: db.delete(row); db.commit()
    return {"ok":True,"simulation":True}

@router.post("/simulate-subscribe")
def simulate_subscribe(data:SimulatedSubscribeRequest,db:Session=Depends(get_db),user=Depends(get_current_user)):
    profile=db.query(BillingProfile).filter(BillingProfile.user_id==user.id).first()
    if not profile: raise HTTPException(400,"Add valid billing details before subscribing.")
    user.plan=data.plan
    _upsert(db,user.id,data.plan,"active",customer_id="university-simulation",subscription_id=f"sim-{user.id}-{data.plan}")
    db.commit()
    return {"ok":True,"plan":user.plan,"status":"active","simulation":True}

@router.post("/simulate-cancel")
def simulate_cancel(db:Session=Depends(get_db),user=Depends(get_current_user)):
    user.plan="free"
    _upsert(db,user.id,"free","canceled",customer_id="university-simulation",subscription_id="")
    db.commit()
    return {"ok":True,"plan":"free","status":"canceled","simulation":True}
