"""SQLAlchemy models for TregoCon (Event-scoped domain model, finalized).

Lodging: $50 per person per night. Nights = subset of {Thu, Fri, Sat}.
One room per user per event; no mid-event switching. Room capacity 1-2.
Meals: 5 fixed services, headcount-first, price default $0 (admin-config).
"""
from datetime import date, datetime
from enum import Enum
import enum

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, ForeignKey,
    Table, UniqueConstraint, Enum as SAEnum,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class UserStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    admin = "admin"


class CommitmentStatus(str, enum.Enum):
    committed = "committed"
    maybe = "maybe"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    paid_cash = "paid_cash"
    paid_venmo = "paid_venmo"
    paid_other = "paid_other"


class TimeBox(str, enum.Enum):
    now = "now"
    after_breakfast = "after_breakfast"
    noon = "noon"
    evening = "evening"
    specific_time = "specific_time"


class GameStatus(str, enum.Enum):
    open = "open"
    full = "full"
    played = "played"
    cancelled = "cancelled"


class SignupInterest(str, enum.Enum):
    in_ = "in"
    maybe = "maybe"


class BedConfig(str, enum.Enum):
    single = "single"
    double = "double"


# The 5 fixed meal services for the standard Thu PM -> Sun AM event.
MEAL_SERVICES = [
    "thu_dinner",
    "fri_breakfast",
    "fri_dinner",
    "sat_breakfast",
    "sat_dinner",
]


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False, unique=True)
    name = Column(String, nullable=False, default="TregoCon")
    resort_name = Column(String, default="Edgewood Resort")
    # Registration window (write-gating happens at request time, no cron).
    registration_opens_at = Column(DateTime, nullable=True)
    registration_closes_at = Column(DateTime, nullable=True)
    # Meal pricing (tentative; default $0 — headcount-first).
    meal_price_per_service = Column(Integer, default=0)  # cents
    lodging_rate_per_night = Column(Integer, default=5000)  # cents ($50)
    created_at = Column(DateTime, default=datetime.utcnow)

    lodges = relationship("Lodge", back_populates="event", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="event", cascade="all, delete-orphan")
    meal_options = relationship("MealOption", back_populates="event", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="event", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="event", cascade="all, delete-orphan")


class Lodge(Base):
    __tablename__ = "lodges"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    photo_url = Column(String)
    event = relationship("Event", back_populates="lodges")
    rooms = relationship("Room", back_populates="lodge", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    lodge_id = Column(Integer, ForeignKey("lodges.id"), nullable=False)
    label = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False, default=2)  # 1 or 2
    bed_config = Column(SAEnum(BedConfig), default=BedConfig.double)
    notes = Column(String)
    event = relationship("Event", back_populates="rooms")
    lodge = relationship("Lodge", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    status = Column(SAEnum(UserStatus), default=UserStatus.pending)
    reset_token = Column(String)
    reset_token_expires = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Nights as a bitmask over [Thu, Fri, Sat] (bits 0,1,2).
    nights_bitmask = Column(Integer, nullable=False, default=0)
    commitment_status = Column(SAEnum(CommitmentStatus), default=CommitmentStatus.committed)
    payment_status = Column(SAEnum(PaymentStatus), default=PaymentStatus.unpaid)
    event = relationship("Event", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_user"),)


class MealOption(Base):
    __tablename__ = "meal_options"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    service = Column(String, nullable=False)  # one of MEAL_SERVICES
    price = Column(Integer, default=0)  # cents
    event = relationship("Event", back_populates="meal_options")
    rsvps = relationship("MealRSVP", back_populates="meal_option", cascade="all, delete-orphan")


class MealRSVP(Base):
    __tablename__ = "meal_rsvps"
    id = Column(Integer, primary_key=True)
    meal_option_id = Column(Integer, ForeignKey("meal_options.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    meal_option = relationship("MealOption", back_populates="rsvps")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("meal_option_id", "user_id", name="uq_meal_user"),)


class GameSession(Base):
    __tablename__ = "game_sessions"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    proposed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    time_box = Column(SAEnum(TimeBox), default=TimeBox.now)
    scheduled_at = Column(DateTime, nullable=True)
    location_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    status = Column(SAEnum(GameStatus), default=GameStatus.open)
    event = relationship("Event", back_populates="game_sessions")
    signups = relationship("GameSignup", back_populates="game_session", cascade="all, delete-orphan")


class GameSignup(Base):
    __tablename__ = "game_signups"
    id = Column(Integer, primary_key=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    interest = Column(SAEnum(SignupInterest), default=SignupInterest.in_)
    game_session = relationship("GameSession", back_populates="signups")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("game_session_id", "user_id", name="uq_game_user"),)


class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    url = Column(String, nullable=False)
    caption = Column(String)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    user = relationship("User")
