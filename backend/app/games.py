"""Games - interactive On-Deck board (M7).

Users post a game session (title + time box: now/after_breakfast/noon/
evening/specific_time + optional room). Others sign up with interest
(in | maybe). Sessions can be marked played/cancelled. A live SSE stream
pushes the board so the on-site PWA updates without manual refresh.
"""
import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import (
    Event, GameSession, GameSignup, User, UserStatus,
    TimeBox, GameStatus, SignupInterest, Room,
)
from .auth import get_current_user
from .lodging import active_event

router = APIRouter(prefix="/api/games", tags=["games"])

# In-process pub/sub for SSE (sandbox scale; swap for Redis later if needed).
_subscribers = set()


def _notify():
    for q in list(_subscribers):
        q.put_nowait(None)


# ---------- schemas ----------
class GameIn(BaseModel):
    title: str
    time_box: str = None  # optional structured hint; free-text `when_text` is preferred
    when: str = None  # free text, e.g. "ASAP", "after dinner", "8pm" (mapped to when_text)
    scheduled_at: str = None  # ISO, for specific_time
    location_room_id: int = None
    description: str = None


class SignupIn(BaseModel):
    interest: str = "in"  # in | maybe


# ---------- helpers ----------
def _serialize(ev_id, db, current_user_id=None):
    games = db.query(GameSession).filter(GameSession.event_id == ev_id).order_by(
        GameSession.time_box, GameSession.id).all()
    out = []
    for g in games:
        signups = db.query(GameSignup).filter(GameSignup.game_session_id == g.id).all()
        ins = [s for s in signups if s.interest == SignupInterest.in_]
        maybes = [s for s in signups if s.interest == SignupInterest.maybe]
        my = None
        if current_user_id:
            m = db.query(GameSignup).filter(
                GameSignup.game_session_id == g.id, GameSignup.user_id == current_user_id).first()
            my = m.interest.value if m else None
        loc = db.query(Room).filter(Room.id == g.location_room_id).first()
        out.append({
            "id": g.id, "title": g.title, "time_box": g.time_box.value if g.time_box else None,
            "when": g.when_text, "posted_at": g.posted_at.isoformat() if g.posted_at else None,
            "scheduled_at": g.scheduled_at.isoformat() if g.scheduled_at else None,
            "location": loc.label if loc else None, "description": g.description,
            "status": g.status.value, "proposed_by": g.proposed_by,
            "in": [{"user_id": s.user_id} for s in ins],
            "maybe": [{"user_id": s.user_id} for s in maybes],
            "in_count": len(ins), "maybe_count": len(maybes),
            "my_interest": my,
        })
    return out


# ---------- list + stream ----------
@router.get("")
def list_games(request: Request, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"games": []}
    return {"games": _serialize(ev.id, db, user.id)}


@router.get("/stream")
async def stream(request: Request, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    """SSE: pushes the game board as JSON every few seconds (or on change)."""
    ev = active_event(db)
    ev_id = ev.id if ev else None

    async def event_gen():
        if not ev_id:
            yield f"data: {json.dumps({'games': []})}\n\n"
            return
        queue = asyncio.Queue()
        _subscribers.add(queue)
        try:
            data = json.dumps({"games": _serialize(ev_id, db, user.id)})
            yield f"data: {data}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    await asyncio.wait_for(queue.get(), timeout=4.0)
                except asyncio.TimeoutError:
                    pass
                data = json.dumps({"games": _serialize(ev_id, db, user.id)})
                yield f"data: {data}\n\n"
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ---------- create ----------
@router.post("")
def create_game(payload: GameIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    tb = None
    if payload.time_box:
        try:
            tb = TimeBox(payload.time_box)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid time_box")
    sched = payload.scheduled_at and datetime.fromisoformat(payload.scheduled_at)
    g = GameSession(
        event_id=ev.id, proposed_by=user.id, title=payload.title, time_box=tb,
        when_text=payload.when, scheduled_at=sched, location_room_id=payload.location_room_id,
        description=payload.description, status=GameStatus.open)
    db.add(g)
    db.commit()
    _notify()
    return {"status": "ok", "game_id": g.id}


# ---------- signup ----------
@router.post("/{game_id}/signup")
def signup(game_id: int, payload: SignupIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    g = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        interest = SignupInterest(payload.interest)
    except ValueError:
        raise HTTPException(status_code=422, detail="interest must be 'in' or 'maybe'")
    existing = db.query(GameSignup).filter(
        GameSignup.game_session_id == game_id, GameSignup.user_id == user.id).first()
    if existing:
        existing.interest = interest
    else:
        db.add(GameSignup(game_session_id=game_id, user_id=user.id, interest=interest))
    db.commit()
    _notify()
    return {"status": "ok", "interest": interest.value}


@router.delete("/{game_id}/signup")
def leave(game_id: int, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    g = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    existing = db.query(GameSignup).filter(
        GameSignup.game_session_id == game_id, GameSignup.user_id == user.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        _notify()
    return {"status": "ok"}


# ---------- status (played/cancelled) ----------
class StatusIn(BaseModel):
    status: str  # open | full | played | cancelled


@router.post("/{game_id}/status")
def set_status(game_id: int, payload: StatusIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    g = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    # allow the proposer or an admin to flip status
    if user.id != g.proposed_by and user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Only the poster or an admin can change status")
    try:
        g.status = GameStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status")
    db.commit()
    _notify()
    return {"status": "ok", "game_status": g.status.value}


@router.delete("/{game_id}")
def delete_game(game_id: int, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    g = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if user.id != g.proposed_by and user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Only the poster or an admin can delete")
    db.delete(g)
    db.commit()
    _notify()
    return {"status": "ok"}
