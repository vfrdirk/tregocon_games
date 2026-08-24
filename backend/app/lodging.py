"""Lodging + reservations (M4).

Rules (finalized):
- One room per user per event; no mid-event switching.
- Room capacity 1-2; a room may hold multiple users.
- Nights = subset of {thu, fri, sat} (bitmask Thu=1, Fri=2, Sat=4).
- Cost = nights * $50/person (room-sharing does NOT change per-person cost).
- Write-gating: reservations allowed only when event.registration_opens_at
  is NULL or now >= opens_at (and before closes_at, if set).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import (
    Event, Lodge, Room, User, UserStatus, Reservation,
    CommitmentStatus, PaymentStatus,
)
from .auth import get_current_user

router = APIRouter(prefix="/api/lodging", tags=["lodging"])

NIGHT_BITS = {"thu": 1, "fri": 2, "sat": 4}
BIT_NIGHTS = {1: "thu", 2: "fri", 4: "sat"}


def nights_to_mask(nights):
    m = 0
    for n in nights:
        if n not in NIGHT_BITS:
            raise HTTPException(status_code=422, detail=f"Invalid night: {n}")
        m |= NIGHT_BITS[n]
    return m


def mask_to_nights(mask):
    return [BIT_NIGHTS[b] for b in (1, 2, 4) if mask & b]


def active_event(db: DBSession):
    return db.query(Event).order_by(Event.year.desc()).first()


def assert_open(ev: Event):
    now = datetime.utcnow()
    if ev.registration_opens_at and now < ev.registration_opens_at:
        raise HTTPException(status_code=403, detail="Registration not open yet")
    if ev.registration_closes_at and now > ev.registration_closes_at:
        raise HTTPException(status_code=403, detail="Registration closed")


# ---------- schemas ----------
class ReserveIn(BaseModel):
    room_id: int
    nights: list[str]  # ["thu","fri","sat"]
    commitment_status: str = "committed"  # committed | maybe


class LodgeIn(BaseModel):
    name: str
    description: str = None


class RoomIn(BaseModel):
    lodge_id: int
    label: str
    capacity: int = 2
    bed_config: str = "double"  # single | double
    notes: str = None


# ---------- public availability ----------
@router.get("/availability")
def availability(db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"event": None}
    rate = ev.lodging_rate_per_night
    lodges = db.query(Lodge).filter(Lodge.event_id == ev.id).all()
    out = []
    for lg in lodges:
        rooms = []
        for r in db.query(Room).filter(Room.lodge_id == lg.id).all():
            res = db.query(Reservation).filter(Reservation.room_id == r.id).all()
            occupants = [{
                "user_id": x.user_id,
                "display_name": x.user.display_name,
                "nights": mask_to_nights(x.nights_bitmask),
                "commitment": x.commitment_status.value,
                "cost_cents": bin(x.nights_bitmask).count('1') * rate,
            } for x in res]
            rooms.append({
                "id": r.id, "label": r.label, "capacity": r.capacity,
                "bed_config": r.bed_config.value if r.bed_config else None,
                "notes": r.notes, "occupants": occupants,
                "spaces_left": r.capacity - len(res),
            })
        out.append({"id": lg.id, "name": lg.name, "description": lg.description, "rooms": rooms})
    return {
        "event": {"id": ev.id, "year": ev.year, "name": ev.name,
                  "opens_at": ev.registration_opens_at.isoformat() if ev.registration_opens_at else None,
                  "rate_per_night_cents": rate},
        "lodges": out,
    }


# ---------- user reservation ----------
@router.get("/my-reservation")
def my_reservation(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"reservation": None}
    res = db.query(Reservation).filter(Reservation.event_id == ev.id, Reservation.user_id == user.id).first()
    if not res:
        return {"reservation": None}
    room = db.query(Room).filter(Room.id == res.room_id).first()
    return {"reservation": {
        "room_id": res.room_id, "room_label": room.label if room else None,
        "nights": mask_to_nights(res.nights_bitmask),
        "commitment": res.commitment_status.value,
        "payment": res.payment_status.value,
        "cost_cents": res.nights_bitmask.bit_count() * ev.lodging_rate_per_night if hasattr(res.nights_bitmask, 'bit_count') else bin(res.nights_bitmask).count('1') * ev.lodging_rate_per_night,
    }}


@router.post("/reserve")
def reserve(payload: ReserveIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    assert_open(ev)
    room = db.query(Room).filter(Room.id == payload.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    # one room per user per event
    existing = db.query(Reservation).filter(Reservation.event_id == ev.id, Reservation.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already have a room for this event (no switching)")
    # capacity
    occ = db.query(Reservation).filter(Reservation.room_id == room.id).count()
    if occ >= room.capacity:
        raise HTTPException(status_code=409, detail="Room is full")
    try:
        mask = nights_to_mask(payload.nights)
    except HTTPException as e:
        raise e
    if mask == 0:
        raise HTTPException(status_code=422, detail="Select at least one night")
    res = Reservation(
        event_id=ev.id, room_id=room.id, user_id=user.id, nights_bitmask=mask,
        commitment_status=CommitmentStatus(payload.commitment_status),
        payment_status=PaymentStatus.unpaid,
    )
    db.add(res)
    db.commit()
    return {"status": "ok", "nights": payload.nights,
            "cost_cents": bin(mask).count('1') * ev.lodging_rate_per_night}


@router.delete("/reserve")
def cancel_reservation(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    res = db.query(Reservation).filter(Reservation.event_id == ev.id, Reservation.user_id == user.id).first()
    if not res:
        raise HTTPException(status_code=404, detail="No reservation to cancel")
    db.delete(res)
    db.commit()
    return {"status": "ok", "message": "Reservation released"}


# ---------- admin CRUD ----------
admin_router = APIRouter(prefix="/api/admin", tags=["admin-lodging"])


@admin_router.post("/lodge")
def create_lodge(payload: LodgeIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    lg = Lodge(event_id=ev.id, name=payload.name, description=payload.description)
    db.add(lg)
    db.commit()
    return {"status": "ok", "lodge_id": lg.id}


@admin_router.post("/room")
def create_room(payload: RoomIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    lg = db.query(Lodge).filter(Lodge.id == payload.lodge_id).first()
    if not lg:
        raise HTTPException(status_code=404, detail="Lodge not found")
    r = Room(lodge_id=lg.id, event_id=lg.event_id, label=payload.label,
             capacity=payload.capacity, bed_config=payload.bed_config, notes=payload.notes)
    db.add(r)
    db.commit()
    return {"status": "ok", "room_id": r.id}
