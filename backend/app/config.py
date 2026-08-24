"""Config portal (M8): event settings, photo uploads, admin user management, announcements.

Photos are stored on a local volume (/app/uploads) and served as static files
at /uploads/<filename>. (Object storage like S3 swaps in at Phase 1.)
"""
import os
import uuid
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import (
    Event, User, UserStatus, Announcement, Photo, GameSession, Reservation,
)
from .auth import get_current_user
from .lodging import active_event

router = APIRouter(prefix="/api", tags=["config"])
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------- event config (admin) ----------
class EventConfigIn(BaseModel):
    name: str = None
    resort_name: str = None
    event_start: str = None  # ISO
    event_end: str = None
    registration_opens_at: str = None  # ISO
    registration_closes_at: str = None
    lodging_rate_per_night_cents: int = None
    meal_price_per_service_cents: int = None
    announcement_text: str = None


@router.put("/admin/event/config")
def set_event_config(payload: EventConfigIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    if payload.name is not None:
        ev.name = payload.name
    if payload.resort_name is not None:
        ev.resort_name = payload.resort_name
    if payload.event_start is not None:
        ev.event_start = datetime.fromisoformat(payload.event_start)
    if payload.event_end is not None:
        ev.event_end = datetime.fromisoformat(payload.event_end)
    if payload.registration_opens_at is not None:
        ev.registration_opens_at = datetime.fromisoformat(payload.registration_opens_at)
    if payload.registration_closes_at is not None:
        ev.registration_closes_at = datetime.fromisoformat(payload.registration_closes_at)
    if payload.lodging_rate_per_night_cents is not None:
        ev.lodging_rate_per_night = payload.lodging_rate_per_night_cents
    if payload.meal_price_per_service_cents is not None:
        ev.meal_price_per_service = payload.meal_price_per_service_cents
    if payload.announcement_text is not None:
        db.add(Announcement(event_id=ev.id, author_id=user.id, body=payload.announcement_text))
    db.commit()
    return {"status": "ok", "event": {"name": ev.name, "year": ev.year}}


@router.get("/event/config")
def get_event_config(db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"event": None}
    return {
        "event": {
            "id": ev.id, "year": ev.year, "name": ev.name, "resort_name": ev.resort_name,
            "event_start": ev.event_start.isoformat() if ev.event_start else None,
            "event_end": ev.event_end.isoformat() if ev.event_end else None,
            "opens_at": ev.registration_opens_at.isoformat() if ev.registration_opens_at else None,
            "closes_at": ev.registration_closes_at.isoformat() if ev.registration_closes_at else None,
            "lodging_rate_per_night_cents": ev.lodging_rate_per_night,
            "meal_price_per_service_cents": ev.meal_price_per_service,
        }
    }


# ---------- photo upload (any logged-in user; tagged w/ attendees + games) ----------
@router.post("/photos")
async def upload_photo(file: UploadFile = File(...), caption: str = Form(None),
                       attendees: str = Form("[]"), games: str = Form("[]"),
                       user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    ext = (file.filename or "bin").split(".")[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
        raise HTTPException(status_code=422, detail="Unsupported image type")
    fname = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(await file.read())
    url = f"/uploads/{fname}"
    try:
        att = json.loads(attendees or "[]")
        gid = json.loads(games or "[]")
    except (ValueError, TypeError):
        att, gid = [], []
    db.add(Photo(event_id=ev.id, url=url, caption=caption, uploaded_by=user.id,
                 attendee_ids=json.dumps(att), game_ids=json.dumps(gid)))
    db.commit()
    return {"status": "ok", "url": url}


@router.get("/photos")
def list_photos(db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"photos": []}
    photos = db.query(Photo).filter(Photo.event_id == ev.id).order_by(Photo.created_at.desc()).all()
    out = []
    for p in photos:
        att_ids = json.loads(p.attendee_ids or "[]")
        g_ids = json.loads(p.game_ids or "[]")
        att_names = [u.display_name for u in db.query(User).filter(User.id.in_(att_ids)).all()] if att_ids else []
        g_titles = [g.title for g in db.query(GameSession).filter(GameSession.id.in_(g_ids)).all()] if g_ids else []
        out.append({"id": p.id, "url": p.url, "caption": p.caption,
                    "attendees": att_names, "games": g_titles,
                    "uploaded_by": p.uploaded_by, "created_at": p.created_at.isoformat() if p.created_at else None})
    return {"photos": out}


@router.delete("/photos/{photo_id}")
def delete_photo(photo_id: int, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    p = db.query(Photo).filter(Photo.id == photo_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Photo not found")
    # remove the file from the uploads volume
    try:
        fname = p.url.split("/")[-1]
        path = os.path.join(UPLOAD_DIR, fname)
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
    db.delete(p)
    db.commit()
    return {"status": "ok", "photo_id": photo_id}


@router.get("/photos/export")
def export_photos(ids: str = "", user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    """Download selected photos as a zip archive (any logged-in user)."""
    import io, zipfile
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not id_list:
        raise HTTPException(status_code=422, detail="No photo ids provided")
    ev = active_event(db)
    photos = db.query(Photo).filter(Photo.id.in_(id_list)).all() if ev else []
    if ev:
        photos = [p for p in photos if p.event_id == ev.id]
    if not photos:
        raise HTTPException(status_code=404, detail="No matching photos")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in photos:
            fname = p.url.split("/")[-1]
            path = os.path.join(UPLOAD_DIR, fname)
            if os.path.exists(path):
                arcname = f"{p.id}_{fname}"
                if p.caption:
                    arcname = f"{p.id}_{p.caption[:40].replace('/', '_')}_{fname}"
                z.write(path, arcname)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=tregocon_photos.zip"})


@router.get("/people")
def list_people(db: DBSession = Depends(get_db)):
    """Attendee picker for photo tagging (any logged-in user)."""
    ev = active_event(db)
    if not ev:
        return {"people": []}
    # everyone with a reservation for the event, plus admins
    reserved = db.query(Reservation.user_id).filter(Reservation.event_id == ev.id).all()
    ids = {r.user_id for r in reserved}
    admins = db.query(User).filter(User.status == UserStatus.admin).all()
    ids.update({a.id for a in admins})
    users = db.query(User).filter(User.id.in_(ids)).order_by(User.display_name).all() if ids else []
    return {"people": [{"id": u.id, "name": u.display_name} for u in users]}


# ---------- admin user management ----------
@router.get("/admin/users")
def list_users(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    users = db.query(User).order_by(User.status, User.email).all()
    return {"users": [{"id": u.id, "email": u.email, "display_name": u.display_name, "status": u.status.value} for u in users]}


class UserMgmtIn(BaseModel):
    status: str  # pending | approved | admin


@router.post("/admin/users/{user_id}")
def set_user_status(user_id: int, payload: UserMgmtIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        target.status = UserStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status")
    db.commit()
    return {"status": "ok", "user_id": user_id, "new_status": target.status.value}


# ---------- announcements ----------
class AnnounceIn(BaseModel):
    body: str


@router.post("/announcements")
def post_announcement(payload: AnnounceIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        raise HTTPException(status_code=404, detail="No active event")
    a = Announcement(event_id=ev.id, author_id=user.id, body=payload.body)
    db.add(a)
    db.commit()
    return {"status": "ok", "id": a.id}


@router.get("/announcements")
def list_announcements(db: DBSession = Depends(get_db)):
    ev = active_event(db)
    if not ev:
        return {"announcements": []}
    items = db.query(Announcement).filter(Announcement.event_id == ev.id).order_by(Announcement.created_at.desc()).all()
    return {"announcements": [{"id": a.id, "body": a.body, "created_at": a.created_at.isoformat()} for a in items]}


# static file serving for uploads (mounted in main.py)
def mount_static(app):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
