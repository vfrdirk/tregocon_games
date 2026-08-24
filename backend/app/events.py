"""Event lifecycle (M5): create-next-year from template, open/close status, admin dashboard.

The "blank slate next year" = admin creates a NEW Event by copying the
latest Event's lodges/rooms/meal-option services forward. History is
preserved (old Event stays); writes are gated by registration window.
"""
from datetime import datetime
import os
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import (
    Event, Lodge, Room, User, UserStatus, Reservation,
    MealOption, MealRSVP, PaymentStatus,
)
from .auth import get_current_user
from .lodging import active_event
from .comms import comms, tpl_event_open

router = APIRouter(prefix="/api/event", tags=["event"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin-event"])


def latest_event(db: DBSession):
    return db.query(Event).order_by(Event.year.desc()).first()


def registration_state(ev: Event) -> str:
    now = datetime.utcnow()
    if ev.registration_opens_at and now < ev.registration_opens_at:
        return "closed_not_opened"
    if ev.registration_closes_at and now > ev.registration_closes_at:
        return "closed_ended"
    return "open"


# ---------- public status ----------
@router.get("/status")
def event_status(db: DBSession = Depends(get_db)):
    ev = latest_event(db)
    if not ev:
        return {"event": None, "state": "no_event"}
    return {
        "event": {"id": ev.id, "year": ev.year, "name": ev.name,
                  "opens_at": ev.registration_opens_at.isoformat() if ev.registration_opens_at else None,
                  "closes_at": ev.registration_closes_at.isoformat() if ev.registration_closes_at else None},
        "state": registration_state(ev),
    }


# ---------- admin: create next event from latest template ----------
class CreateNextIn(BaseModel):
    year: int
    name: str = None
    opens_at: str = None  # ISO; if omitted, defaults to Jan 15 of that year
    lodging_rate_per_night_cents: int = 5000
    meal_price_per_service_cents: int = 0


@admin_router.post("/event/create-next")
def create_next_event(payload: CreateNextIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    if db.query(Event).filter(Event.year == payload.year).first():
        raise HTTPException(status_code=409, detail=f"Event {payload.year} already exists")
    src = latest_event(db)
    if not src:
        raise HTTPException(status_code=400, detail="No source event to copy from")
    opens = payload.opens_at and datetime.fromisoformat(payload.opens_at)
    if not opens:
        opens = datetime(payload.year, 1, 15)
    ev = Event(
        year=payload.year,
        name=payload.name or f"TregoCon {payload.year}",
        registration_opens_at=opens,
        lodging_rate_per_night=payload.lodging_rate_per_night_cents,
        meal_price_per_service=payload.meal_price_per_service_cents,
    )
    db.add(ev)
    db.flush()
    # Copy lodges + rooms forward
    for lg in db.query(Lodge).filter(Lodge.event_id == src.id).all():
        new_lg = Lodge(event_id=ev.id, name=lg.name, description=lg.description, photo_url=lg.photo_url)
        db.add(new_lg)
        db.flush()
        for r in db.query(Room).filter(Room.lodge_id == lg.id).all():
            db.add(Room(event_id=ev.id, lodge_id=new_lg.id, label=r.label, floor=r.floor,
                        capacity=r.capacity, bed_config=r.bed_config, notes=r.notes))
    # Copy meal-option SERVICES forward (no RSVPs)
    for m in db.query(MealOption).filter(MealOption.event_id == src.id).all():
        db.add(MealOption(event_id=ev.id, service=m.service, price=payload.meal_price_per_service_cents))
    db.commit()
    return {"status": "ok", "event_id": ev.id, "year": ev.year,
            "message": f"Created {ev.name} by copying {src.year}'s template."}


# ---------- admin dashboard summary ----------
@admin_router.post("/event/notify-open")
def notify_open(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = latest_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    if registration_state(ev) != "open":
        raise HTTPException(status_code=400, detail="Event is not open; cannot notify")
    url = os.environ.get("PUBLIC_URL", "http://localhost:8080")
    subj, body = tpl_event_open(ev.name, url)
    sent = 0
    for u in db.query(User).filter(User.status.in_([UserStatus.approved, UserStatus.admin])).all():
        if comms.send_email(u.email, subj, body):
            sent += 1
    return {"status": "ok", "notified": sent, "email_enabled": comms.email.enabled}


@admin_router.get("/event/comms-status")
def comms_status(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return {"email_enabled": comms.email.enabled, "sms_enabled": comms.sms.enabled}


# ---------- admin dashboard summary ----------
@admin_router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = latest_event(db)
    if not ev:
        return {"event": None}
    approved_users = db.query(User).filter(User.status == UserStatus.approved).count()
    admin_users = db.query(User).filter(User.status == UserStatus.admin).count()
    pending_users = db.query(User).filter(User.status == UserStatus.pending).count()
    reservations = db.query(Reservation).filter(Reservation.event_id == ev.id).all()
    rooms = db.query(Room).filter(Room.event_id == ev.id).all()
    paid = sum(1 for r in reservations if r.payment_status != PaymentStatus.unpaid)
    nights_total = 0
    for r in reservations:
        people = 1 + len(json.loads(r.companions or "[]") or [])
        nights_total += bin(r.nights_bitmask).count('1') * people
    # meal headcounts
    meal_opts = db.query(MealOption).filter(MealOption.event_id == ev.id).all()
    meal_counts = []
    for m in meal_opts:
        cnt = db.query(MealRSVP).filter(MealRSVP.meal_option_id == m.id).count()
        meal_counts.append({"service": m.service, "rsvps": cnt, "price_cents": m.price})
    return {
        "event": {"year": ev.year, "name": ev.name, "state": registration_state(ev)},
        "users": {"approved": approved_users, "admins": admin_users, "pending": pending_users},
        "lodging": {
            "reservations": len(reservations),
            "rooms_total": len(rooms),
            "rooms_filled": sum(1 for r in rooms if db.query(Reservation).filter(Reservation.room_id == r.id).count() > 0),
            "nights_booked": nights_total,
            "lodging_revenue_cents": nights_total * ev.lodging_rate_per_night,
            "paid_count": paid,
        },
        "meals": meal_counts,
    }
