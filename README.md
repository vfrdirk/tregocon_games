# TregoCon — Tabletop gamers weekend app

Sandbox scaffold (Milestone 1). Stack:
- **Backend:** Python FastAPI (`backend/`) — `/api/health` endpoint live.
- **Frontend:** React + Vite (`frontend/`) — shell that calls the API.
- **DB:** PostgreSQL 16.
- **Proxy:** Caddy (serves SPA + proxies `/api` to backend).

## Run locally (sandbox, LAN only — no TLS)
```bash
docker compose up --build
# open http://<host-ip>:8080
```

## Status
- [x] M1 Scaffold: repo + compose + CI + health endpoint
- [ ] M2 Schema + Event-scoped migrations
- [ ] M3 Auth (register → admin approve → login)
- [ ] M4 Lodging + reservations
- [ ] M5 Event lifecycle (yearly reset)
- [ ] M6 Meals + ledger
- [ ] M7 Games (interactive On-Deck)
- [ ] M8 Config portal
- [ ] M9 Notifications (SES + Twilio)
- [ ] M10 Sandbox validation
- [ ] M11 Deploy to Lightsail + play.tregocon.games

Plan: see `/opt/data/.hermes/plans/2026-08-23_tabletop-lodging-app.md`
Live at https://play.tregocon.games (Lightsail, TLS via Caddy/Let's Encrypt)
