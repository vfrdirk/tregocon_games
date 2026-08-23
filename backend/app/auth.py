"""Auth: registration, admin approval, login (DB-backed sessions), password reset.

Email is stubbed (logged) until SES is wired in Phase 1. Sessions are
server-side DB rows keyed by a random token in an httpOnly cookie, so
logout/revoke are real (delete the row).
"""
import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from .db import get_db
from .models import User, UserStatus, Session

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "tregocon_session"
SESSION_DAYS = 30
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "dirk@guac")  # first admin / approver


# ---------- helpers ----------
def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_pw(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def make_session(db: DBSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    exp = datetime.utcnow() + timedelta(days=SESSION_DAYS)
    s = Session(token=token, user_id=user.id, expires_at=exp)
    db.add(s)
    db.commit()
    return token


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    s = db.query(Session).filter(Session.token == token).first()
    if not s or (s.expires_at and s.expires_at < datetime.utcnow()):
        raise HTTPException(status_code=401, detail="Session expired")
    user = db.query(User).filter(User.id == s.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="No user")
    return user


def _send_email(to: str, subject: str, body: str):
    # STUB until SES (Phase 1). Logs intent; no real send.
    print(f"[email stub] to={to} subject={subject}\n{body}")


# ---------- schemas ----------
class RegisterIn(BaseModel):
    email: str
    display_name: str
    password: str


class ApproveIn(BaseModel):
    user_id: int


class LoginIn(BaseModel):
    email: str
    password: str


class ResetRequestIn(BaseModel):
    email: str


class ResetConfirmIn(BaseModel):
    token: str
    new_password: str


# ---------- routes ----------
@router.post("/register")
def register(payload: RegisterIn, db: DBSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be >= 8 chars")
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_pw(payload.password),
        status=UserStatus.pending,
    )
    db.add(user)
    db.commit()
    _send_email(user.email, "TregoCon registration received",
                "Thanks! An admin will approve your account before you can log in.")
    _send_email(ADMIN_EMAIL, "New TregoCon registration pending approval",
                f"{user.display_name} ({user.email}) requested an account. Approve in the admin portal.")
    return {"status": "pending", "message": "Registration received; awaiting admin approval."}


@router.post("/login")
def login(payload: LoginIn, response: Response, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_pw(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != UserStatus.approved and user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Account not yet approved")
    token = make_session(db, user)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax",
                        max_age=SESSION_DAYS * 86400, secure=False)  # secure=True in Phase 1 prod
    return {"status": "ok", "user": {"id": user.id, "email": user.email,
                                     "display_name": user.display_name, "role": user.status.value}}


@router.post("/logout")
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.query(Session).filter(Session.token == token).delete()
        db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"status": "ok"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "display_name": user.display_name,
            "role": user.status.value}


@router.get("/pending")
def list_pending(user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    pending = db.query(User).filter(User.status == UserStatus.pending).all()
    return [{"id": u.id, "email": u.email, "display_name": u.display_name} for u in pending]


@router.post("/approve")
def approve(payload: ApproveIn, user: User = Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user.status != UserStatus.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    target = db.query(User).filter(User.id == payload.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.status = UserStatus.approved
    db.commit()
    _send_email(target.email, "Your TregoCon account is approved",
                "You can now log in at the event site.")
    return {"status": "ok", "approved": target.email}


@router.post("/reset/request")
def reset_request(payload: ResetRequestIn, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        tok = secrets.token_urlsafe(24)
        user.reset_token = tok
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        _send_email(user.email, "TregoCon password reset",
                    f"Reset link token: {tok}  (valid 1 hour)")
    # Always return ok to avoid account enumeration.
    return {"status": "ok", "message": "If that email exists, a reset link was sent."}


@router.post("/reset/confirm")
def reset_confirm(payload: ResetConfirmIn, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or (user.reset_token_expires and user.reset_token_expires < datetime.utcnow()):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be >= 8 chars")
    user.password_hash = hash_pw(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return {"status": "ok", "message": "Password updated."}
