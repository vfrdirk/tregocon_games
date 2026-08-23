"""Database engine + session setup (Postgres via DATABASE_URL)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://tregocon:tregocon_dev@127.0.0.1:5432/tregocon",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. For sandbox/MVP; Alembic added when migrations matter."""
    Base.metadata.create_all(bind=engine)
