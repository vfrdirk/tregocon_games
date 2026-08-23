from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TregoCon API", version="0.1.0")

# CORS: allow the frontend origin (Caddy-served). Tighten in prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sandbox; restrict to play.tregocon.games later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "tregocon-api", "version": "0.1.0"}


@app.get("/api/event/current")
def current_event():
    # Placeholder for Milestone 2+ (Event-scoped data model)
    return {"event": None, "message": "Event data model not yet implemented"}
