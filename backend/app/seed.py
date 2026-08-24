"""Seed CLI: create a new Event from a template (the yearly "blank slate" mechanism).

Usage:
    python -m app.seed --year 2027 --name "TregoCon 2027" --open 2027-01-15
"""
import argparse
from datetime import datetime

from .db import SessionLocal, init_db
from .models import Event, Lodge, Room, MealOption, MEAL_SERVICES


# Main Cabin layout (TregoCon at Edgewood). One lodge, three floors.
# Upstairs: 6 rooms (2 doubles + 4 queens). Main floor: 2 doubles. Downstairs: 3 queens.
# ALL rooms hold up to 2 people:
#   - "double" = two beds (good for parent/child who don't share a bed, or two friends)
#   - "single"/queen = one bed (a couple who share a bed)
# Capacity is 2 for every room; bed_config only describes the bed layout.
TEMPLATE_LODGES = [
    {"name": "Main Cabin", "floors": {
        "upstairs": [
            {"label": "Upstairs 1", "capacity": 2, "bed_config": "double"},
            {"label": "Upstairs 2", "capacity": 2, "bed_config": "double"},
            {"label": "Upstairs 3", "capacity": 2, "bed_config": "single"},
            {"label": "Upstairs 4", "capacity": 2, "bed_config": "single"},
            {"label": "Upstairs 5", "capacity": 2, "bed_config": "single"},
            {"label": "Upstairs 6", "capacity": 2, "bed_config": "single"},
        ],
        "main": [
            {"label": "Main 1", "capacity": 2, "bed_config": "double"},
            {"label": "Main 2", "capacity": 2, "bed_config": "double"},
        ],
        "down": [
            {"label": "Down 1", "capacity": 2, "bed_config": "single"},
            {"label": "Down 2", "capacity": 2, "bed_config": "single"},
            {"label": "Down 3", "capacity": 2, "bed_config": "single"},
        ],
    }},
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

        room_count = 0
        for lt in TEMPLATE_LODGES:
            lodge = Lodge(event_id=ev.id, name=lt["name"])
            db.add(lodge)
            db.flush()
            for floor, rooms in lt["floors"].items():
                for rt in rooms:
                    db.add(Room(
                        event_id=ev.id, lodge_id=lodge.id, floor=floor,
                        label=rt["label"], capacity=rt["capacity"],
                        bed_config=rt["bed_config"],
                    ))
                    room_count += 1

        for svc in MEAL_SERVICES:
            db.add(MealOption(event_id=ev.id, service=svc, price=0))

        db.commit()
        lodge_count = len(TEMPLATE_LODGES)
        print(f"Seeded Event {year} (id={ev.id}) with {lodge_count} lodge, "
              f"{room_count} rooms, {len(MEAL_SERVICES)} meal options.")
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
