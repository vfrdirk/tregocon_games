from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import get_db, init_db, engine
from .models import Event, MealOption
from . import auth
from . import lodging
from . import events
from . import meals
from . import games
from . import config

app = FastAPI(title="TregoCon API", version="0.8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sandbox; restrict to play.tregocon.games later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(lodging.router)
app.include_router(lodging.admin_router)
app.include_router(events.router)
app.include_router(events.admin_router)
app.include_router(meals.router)
app.include_router(meals.admin_router)
app.include_router(games.router)
app.include_router(config.router)
config.mount_static(app)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "tregocon-api", "version": "0.3.0"}


@app.get("/api/db/health")
def db_health(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        return {"status": "error", "db": str(e)}


@app.get("/api/event/current")
def current_event(db: Session = Depends(get_db)):
    ev = db.query(Event).order_by(Event.year.desc()).first()
    if not ev:
        return {"event": None, "message": "No event seeded yet. Run: python -m app.seed --year 2027"}
    meals = db.query(MealOption).filter(MealOption.event_id == ev.id).all()
    return {
        "event": {
            "id": ev.id,
            "year": ev.year,
            "name": ev.name,
            "lodging_rate_per_night_cents": ev.lodging_rate_per_night,
            "meal_price_per_service_cents": ev.meal_price_per_service,
            "registration_opens_at": ev.registration_opens_at.isoformat() if ev.registration_opens_at else None,
        },
        "meal_options": [{"id": m.id, "service": m.service, "price_cents": m.price} for m in meals],
    }
