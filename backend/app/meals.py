"""Meals + ledger (M6).

Meals are HEADCOUNT-FIRST (who's eating what); cost is tentative ($0 default,
admin-configurable). Per-user balance = lodging (nights x $50 x people) + meals
(selected services x price). Payment status is marked by the coordinator (Evan)
to reconcile cash/Venmo offline.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import (
    Event, MealOption, MealRSVP, User, UserStatus,
    Reservation, PaymentStatus,
)
from .auth import get_current_user
from .lodging import active_event  # reuse

router = APIRouter(prefix="/api/meals", tags=["meals"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin-meals"])


# ---------- public meal list + headcounts ----------
@router.get("")
def meal_list(db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"event": None, "services": []}
    opts = db.query(MealOption).filter(MealOption.event_id == ev.id).all()
    out = []
    for m in opts:
        rows = db.query(MealRSVP).filter(MealRSVP.meal_option_id == m.id).all()
        cnt = sum(1 + len(json.loads(r.companions or "[]") or []) for r in rows)
        out.append({"id": m.id, "service": m.service, "price_cents": m.price, "headcount": cnt})
    return {"event": {"year": ev.year, "meal_price_per_service_cents": ev.meal_price_per_service}, "services": out}


# ---------- user RSVP (toggle set of services) ----------
class RsvpIn(BaseModel):
    services: list[str]  # list of service names, e.g. ["thu_dinner","fri_breakfast"]
    companions: list[str] = []  # named spouse/child also eating these meals


@router.get("/my")
def my_meals(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"rsvps": []}
    opts = db.query(MealOption).filter(MealOption.event_id == ev.id).all()
    by_service = {m.service: m.id for m in opts}
    mine = db.query(MealRSVP).join(MealOption).filter(
        MealRSVP.user_id == user.id, MealOption.event_id == ev.id).all()
    seen = set()
    companions = []
    for m in mine:
        for c in (json.loads(m.companions or "[]") or []):
            if c not in seen:
                seen.add(c); companions.append(c)
    return {"rsvps": [m.meal_option.service for m in mine], "companions": companions}


@router.post("/rsvp")
def set_rsvp(payload: RsvpIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    opts = db.query(MealOption).filter(MealOption.event_id == ev.id).all()
    by_service = {m.service: m.id for m in opts}
    # clear existing (flush so the INSERT below can't collide on the unique key)
    existing = db.query(MealRSVP).join(MealOption).filter(
        MealRSVP.user_id == user.id, MealOption.event_id == ev.id).all()
    for r in existing:
        db.delete(r)
    db.flush()
    # add selected (each with the same companion list)
    companions = json.dumps([c.strip() for c in (payload.companions or []) if c.strip()])
    for svc in payload.services:
        if svc not in by_service:
            raise HTTPException(status_code=422, detail=f"Unknown meal service: {svc}")
        db.add(MealRSVP(meal_option_id=by_service[svc], user_id=user.id, companions=companions))
    db.commit()
    return {"status": "ok", "rsvps": payload.services, "companions": json.loads(companions)}


# ---------- per-user ledger ----------
@router.get("/ledger/me")
def my_ledger(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"total_cents": 0}
    res = db.query(Reservation).filter(Reservation.event_id == ev.id, Reservation.user_id == user.id).first()
    lodging_cents = 0
    nights = 0
    if res:
        people = 1 + len(json.loads(res.companions or "[]") or [])
        nights = bin(res.nights_bitmask).count('1')
        lodging_cents = nights * ev.lodging_rate_per_night * people
    mine = db.query(MealRSVP).join(MealOption).filter(
        MealRSVP.user_id == user.id, MealOption.event_id == ev.id).all()
    meal_ids = [m.meal_option_id for m in mine]
    meals = db.query(MealOption).filter(MealOption.id.in_(meal_ids)).all()
    # each RSVP row covers the user + their companions for that service
    meals_cents = sum(m.price * (1 + len(json.loads(m_row.companions or "[]") or [])) for m_row in mine for m in meals if m.id == m_row.meal_option_id)
    return {
        "lodging_cents": lodging_cents, "nights": nights,
        "meals_cents": meals_cents, "meal_services": [m.service for m in meals],
        "total_cents": lodging_cents + meals_cents,
    }


# ---------- admin: payment marking + meal price ----------
class PaymentIn(BaseModel):
    user_id: int
    status: str  # unpaid | paid_cash | paid_venmo | paid_other


class MealPriceIn(BaseModel):
    price_cents: int


@admin_router.post("/payment")
def mark_payment(payload: PaymentIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    res = db.query(Reservation).filter(Reservation.event_id == ev.id, Reservation.user_id == payload.user_id).first()
    if not res:
        raise HTTPException(status_code=404, detail="User has no reservation for this event")
    try:
        res.payment_status = PaymentStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid payment status")
    db.commit()
    return {"status": "ok", "user_id": payload.user_id, "payment": res.payment_status.value}


@admin_router.post("/meal-price")
def set_meal_price(payload: MealPriceIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    ev.meal_price_per_service = payload.price_cents
    # apply to all meal options this event
    for m in db.query(MealOption).filter(MealOption.event_id == ev.id).all():
        m.price = payload.price_cents
    db.commit()
    return {"status": "ok", "meal_price_per_service_cents": payload.price_cents}


@admin_router.get("/meals/summary")
def meals_summary(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = active_event(db)
    if not ev:
        return {"event": None}
    opts = db.query(MealOption).filter(MealOption.event_id == ev.id).all()
    out = []
    total_owed = 0
    for m in opts:
        rows = db.query(MealRSVP).filter(MealRSVP.meal_option_id == m.id).all()
        cnt = sum(1 + len(json.loads(r.companions or "[]") or []) for r in rows)
        out.append({"service": m.service, "headcount": cnt, "price_cents": m.price, "collected_cents": cnt * m.price})
        total_owed += cnt * m.price
    return {"event": {"year": ev.year}, "services": out, "meal_total_owed_cents": total_owed}
