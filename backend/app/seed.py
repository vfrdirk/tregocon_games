"""Seed CLI: create a new Event from a template (the yearly "blank slate" mechanism).

Usage:
    python -m app.seed --year 2027 --name "TregoCon 2027" --open 2027-01-15
"""
import argparse
from datetime import datetime

from .db import SessionLocal, init_db
from .models import Event, Lodge, Room, MealOption, MEAL_SERVICES


# Template lodges/rooms carried forward each year (details TBD by admin later).
TEMPLATE_LODGES = [
    {"name": "Black Bear Reunion Lodge", "rooms": [
        {"label": "Bear 1", "capacity": 2, "bed_config": "double"},
        {"label": "Bear 2", "capacity": 2, "bed_config": "double"},
        {"label": "Bear 3", "capacity": 1, "bed_config": "single"},
    ]},
    {"name": "Second Cabin", "rooms": [
        {"label": "Cabin A", "capacity": 2, "bed_config": "double"},
        {"label": "Cabin B", "capacity": 2, "bed_config": "double"},
    ]},
]


def seed_event(year: int, name: str, opens_at: str = None, lodge_rate_cents: int = 5000):
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Event).filter(Event.year == year).first()
        if existing:
            print(f"Event {year} already exists (id={existing.id}). Aborting.")
            return existing

        ev = Event(
            year=year,
            name=name,
            lodging_rate_per_night=5000,
            meal_price_per_service=0,
        )
        if opens_at:
            ev.registration_opens_at = datetime.fromisoformat(opens_at)
        db.add(ev)
        db.flush()

        for lt in TEMPLATE_LODGES:
            lodge = Lodge(event_id=ev.id, name=lt["name"])
            db.add(lodge)
            db.flush()
            for rt in lt["rooms"]:
                db.add(Room(
                    event_id=ev.id, lodge_id=lodge.id,
                    label=rt["label"], capacity=rt["capacity"],
                    bed_config=rt["bed_config"],
                ))

        for svc in MEAL_SERVICES:
            db.add(MealOption(event_id=ev.id, service=svc, price=0))

        db.commit()
        print(f"Seeded Event {year} (id={ev.id}) with {len(TEMPLATE_LODGES)} lodges, "
              f"{sum(len(l['rooms']) for l in TEMPLATE_LODGES)} rooms, {len(MEAL_SERVICES)} meal options.")
        return ev
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--name", type=str, default=None)
    p.add_argument("--open", type=str, default=None, help="ISO open datetime e.g. 2027-01-15")
    args = p.parse_args()
    seed_event(args.year, args.name or f"TregoCon {args.year}", opens_at=args.open)
