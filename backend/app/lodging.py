"""Lodging + reservations (M4, revised).

Rules (finalized):
- One reservation per registered user per event; no mid-event switching.
- Every room holds 1-2 *people*. "People" = the account holder + any named
  companions (spouse/child), OR two separate account holders sharing a room
  (e.g. a couple in a single/queen room, or two friends in a double).
- Nights = subset of {thu, fri, sat} (bitmask Thu=1, Fri=2, Sat=4).
- Cost = nights * $50/person (no discounts; room-sharing does not change the
  per-person rate). Companions are billed to the reserving account holder.
- Write-gating: reservations allowed only when event.registration_opens_at
  is NULL or now >= opens_at (and before closes_at, if set).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import (
    Event, Lodge, Room, User, UserStatus, Reservation,
    CommitmentStatus, PaymentStatus, BedConfig, MealRSVP,
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


def get_companions(res: Reservation):
    try:
        return json.loads(res.companions or "[]") or []
    except (ValueError, TypeError):
        return []


def room_occupants(db: DBSession, room: Room):
    """Return list of occupant dicts (account holders + companions) for a room."""
    out = []
    for x in db.query(Reservation).filter(Reservation.room_id == room.id).all():
        nights = mask_to_nights(x.nights_bitmask)
        cost = len(nights) * active_rate(db)
        out.append({
            "user_id": x.user_id, "display_name": x.user.display_name,
            "nights": nights, "commitment": x.commitment_status.value,
            "cost_cents": cost, "is_guest": False,
        })
        for name in get_companions(x):
            out.append({
                "user_id": None, "display_name": name,
                "nights": nights, "commitment": x.commitment_status.value,
                "cost_cents": cost, "is_guest": True,
            })
    return out


def active_rate(db: DBSession):
    ev = active_event(db)
    return ev.lodging_rate_per_night if ev else 5000


def room_spaces_left(db: DBSession, room: Room):
    occ = 0
    for x in db.query(Reservation).filter(Reservation.room_id == room.id).all():
        occ += 1 + len(get_companions(x))
    return room.capacity - occ


# ---------- schemas ----------
class ReserveIn(BaseModel):
    room_id: int
    nights: list[str]  # ["thu","fri","sat"]
    commitment_status: str = "committed"  # committed | maybe
    companions: list[str] = []  # names of spouse/child sharing the room


class LodgeIn(BaseModel):
    name: str
    description: str = None


class RoomIn(BaseModel):
    lodge_id: int
    label: str
    floor: str = "main"  # upstairs | main | down
    capacity: int = 2
    bed_config: str = "double"  # single | double
    notes: str = None


class RoomUpdate(BaseModel):
    label: str = None
    floor: str = None
    capacity: int = None
    bed_config: str = None
    notes: str = None


# ---------- public availability ----------
@router.get("/availability")
def availability(db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"event": None}
    rate = ev.lodging_rate_per_night
    lodges = db.query(Lodge).filter(Lodge.event_id == ev.id).all()
    FLOOR_ORDER = {"upstairs": 0, "main": 1, "down": 2}
    FLOOR_LABEL = {"upstairs": "Upstairs", "main": "Main Floor", "down": "Downstairs"}
    out = []
    for lg in lodges:
        rooms = []
        for r in sorted(db.query(Room).filter(Room.lodge_id == lg.id).all(),
                        key=lambda x: (FLOOR_ORDER.get(x.floor, 1), x.label)):
            occupants = room_occupants(db, r)
            rooms.append({
                "id": r.id, "label": r.label, "floor": r.floor,
                "floor_label": FLOOR_LABEL.get(r.floor, r.floor),
                "bed_config": r.bed_config.value if r.bed_config else None,
                "capacity": r.capacity,
                "notes": r.notes, "occupants": occupants,
                "spaces_left": room_spaces_left(db, r),
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
    nights = mask_to_nights(res.nights_bitmask)
    companions = get_companions(res)
    return {"reservation": {
        "room_id": res.room_id, "room_label": room.label if room else None,
        "nights": nights, "commitment": res.commitment_status.value,
        "payment": res.payment_status.value,
        "companions": companions,
        "cost_cents": len(nights) * ev.lodging_rate_per_night * (1 + len(companions)),
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
    # capacity: account holder (1) + companions must fit
    companions = [c.strip() for c in (payload.companions or []) if c.strip()]
    total_people = 1 + len(companions)
    if total_people > room.capacity:
        raise HTTPException(status_code=409,
                            detail=f"Room holds {room.capacity}; you'd be {total_people} (incl. companions)")
    # also can't fill a room already partly occupied by others
    if room_spaces_left(db, room) < total_people:
        raise HTTPException(status_code=409, detail="Room doesn't have enough space left")
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
        companions=json.dumps(companions),
    )
    db.add(res)
    db.commit()
    return {"status": "ok", "nights": payload.nights,
            "companions": companions,
            "cost_cents": len(payload.nights) * ev.lodging_rate_per_night * total_people}


@router.delete("/reserve")
def cancel_reservation(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    res = db.query(Reservation).filter(Reservation.event_id == ev.id, Reservation.user_id == user.id).first()
    if not res:
        raise HTTPException(status_code=404, detail="No reservation to cancel")
    db.delete(res)
    # releasing a room also releases this user's meal selections (they're not attending)
    db.query(MealRSVP).filter(MealRSVP.user_id == user.id).delete()
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
    r = Room(lodge_id=lg.id, event_id=lg.event_id, label=payload.label, floor=payload.floor,
             capacity=payload.capacity, bed_config=payload.bed_config, notes=payload.notes)
    db.add(r)
    db.commit()
    return {"status": "ok", "room_id": r.id}


@admin_router.patch("/room/{room_id}")
def update_room(room_id: int, payload: RoomUpdate, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    r = db.query(Room).filter(Room.id == room_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Room not found")
    if payload.label is not None:
        r.label = payload.label
    if payload.floor is not None:
        r.floor = payload.floor
    if payload.capacity is not None:
        r.capacity = payload.capacity
    if payload.bed_config is not None:
        r.bed_config = BedConfig(payload.bed_config)
    if payload.notes is not None:
        r.notes = payload.notes
    db.commit()
    return {"status": "ok", "room_id": r.id, "label": r.label}
