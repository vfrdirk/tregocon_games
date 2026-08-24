import sys
sys.path.insert(0, '/app')
from app.db import SessionLocal, init_db
from app.models import Event, Lodge, Room
from sqlalchemy import text

init_db()
db = SessionLocal()
try:
    # 1) add columns if missing (idempotent)
    for stmt in [
        "ALTER TABLE rooms ADD COLUMN IF NOT EXISTS floor VARCHAR DEFAULT 'main'",
        "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS companions VARCHAR DEFAULT '[]'",
    ]:
        try:
            db.execute(text(stmt))
            db.commit()
        except Exception as e:
            db.rollback()
            print("skip:", e)

    # 2) wipe demo lodging for the active event and reseed Main Cabin
    ev = db.query(Event).order_by(Event.year.desc()).first()
    print("active event:", ev.year if ev else None)
    # delete reservations + rooms + lodges for this event (raw SQL, ordered)
    db.execute(text("DELETE FROM reservations WHERE event_id = :e"), {"e": ev.id})
    db.execute(text("DELETE FROM rooms WHERE event_id = :e"), {"e": ev.id})
    db.execute(text("DELETE FROM lodges WHERE event_id = :e"), {"e": ev.id})
    db.commit()

    # 3) build Main Cabin from template
    from app.seed import TEMPLATE_LODGES
    import json
    for lt in TEMPLATE_LODGES:
        lodge = Lodge(event_id=ev.id, name=lt["name"])
        db.add(lodge); db.flush()
        for floor, rooms in lt["floors"].items():
            for rt in rooms:
                db.add(Room(event_id=ev.id, lodge_id=lodge.id, floor=floor,
                            label=rt["label"], capacity=rt["capacity"],
                            bed_config=rt["bed_config"]))
    db.commit()
    print("rebuilt Main Cabin:",
          db.query(Room).filter(Room.event_id == ev.id).count(), "rooms")
finally:
    db.close()
