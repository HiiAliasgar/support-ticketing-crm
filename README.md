# SupportTick — Customer Support Ticketing CRM

A full-stack help-desk application for creating, searching, filtering, and
resolving customer support tickets — built as a production-grade capstone.

**Live URL:** https://support-ticketing-crm-production-1ba5.up.railway.app  
**Repository:** https://github.com/HiiAliasgar/support-ticketing-crm  
**Stack:** FastAPI (Python) · SQLite · React (Vite + Tailwind) · Docker

![stack](https://img.shields.io/badge/backend-FastAPI%20%2F%20SQLite-0fa669)
![stack](https://img.shields.io/badge/frontend-React%20%2B%20Tailwind-61dafb)

---

## Why this stack

* **FastAPI** — modern, async-ready Python framework with automatic OpenAPI docs
  (`/api/docs`) and first-class request/response validation via Pydantic.
* **SQLite** — zero-friction, file-based database that needs no external service.
  The schema keeps the assignment's "2 tables only" spirit (`tickets`, `notes`).
* **React + Vite + Tailwind** — fast, componentized UI with a clean, responsive,
  mobile-friendly design.
* **Single-service deploy** — FastAPI serves the built React app as static files,
  so one Docker image contains the whole product. No separate hosting needed.

## Features

| # | Requirement | Where |
|---|-------------|-------|
| 1 | **Create tickets** — customer name/email, title, description; auto `TKT-XXXX` ID + timestamp | `POST /api/tickets` · `/new` |
| 2 | **List all tickets** — ID, name, title, status, date | `GET /api/tickets` · home page |
| 3 | **Search** — as-you-type across name, email, ID, subject, description | `GET /api/tickets?search=` |
| 4 | **Filter by status** — Open / In Progress / Closed | `GET /api/tickets?status=` |
| 5 | **View & update** — full detail view, status changes, internal notes | `GET/PUT /api/tickets/{id}`, `POST .../notes` |

### Stand-out addition: operational dashboard
A real support team watching hundreds of tickets a day needs a pulse on the
queue, not just a list. The home page includes:
* live counts by status (Total / Open / In progress / Closed),
* tickets created per day over the last 7 days,
* most-recent note activity.

**Tradeoffs made:** the dashboard queries are aggregate `COUNT/GROUP BY`
statements over one small table (fast at this scale, no materialization needed);
activity only shows ticket notes, deliberately not every status change, to keep
the schema at two tables as the spec asks.

---

## Quick start (local)

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env            # optional
uvicorn app.main:app --reload --port 8000
```

API runs at `http://localhost:8000`, interactive docs at
`http://localhost:8000/api/docs`. A fresh database is auto-seeded with 15 demo
tickets (set `AUTO_SEED_DEMO=0` to disable).

### 2. Frontend (dev mode)

```bash
cd frontend
npm install
npm run dev
```

Vite (`http://localhost:5173`) proxies `/api` to the backend on port 8000.

### Build the frontend for production (served by FastAPI)

```bash
cd frontend && npm run build
cd .. && cd backend && uvicorn app.main:app --port 8000
# open http://localhost:8000 — the React app is served at the root
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/api/tickets` | Create a ticket → `{ ticket_id, created_at }` |
| `GET` | `/api/tickets` | List, with optional `?status=` and `?search=` |
| `GET` | `/api/tickets/{ticket_id}` | Full detail incl. notes |
| `PUT` | `/api/tickets/{ticket_id}` | Update status and/or add a note |
| `POST` | `/api/tickets/{ticket_id}/notes` | Add a note with author |
| `GET` | `/api/dashboard` | Status counts + 7-day volume + recent activity |

### Data model

```sql
tickets (id PK, ticket_id UNIQUE "TKT-0001", customer_name, customer_email,
         subject, description, status, created_at, updated_at)
notes   (id PK, ticket_id FK → tickets.ticket_id, note_text, author, created_at)
```

## Tests

```bash
cd backend
python -m pytest -q          # API unit/integration tests (isolated temp DB)
python ../scripts/smoke_test.py   # boots a real server, exercises API + SPA serving
```

## Deployment (Railway)

The repo contains a `Dockerfile` (multi-stage: builds the frontend, installs
Python deps, runs uvicorn) and `railway.json`.

1. Push this repo to GitHub.
2. In [Railway](https://railway.app) → **New Project → Deploy from GitHub repo**.
3. Railway auto-detects the Dockerfile and sets a `PORT`. Done.
   * For a persistent database across redeploys, add a **Volume** mounted at
     `/data` (the app stores SQLite there via `DATABASE_URL`).

No other platform config is required. Because the built frontend is served by
FastAPI, the API **and** UI live at the same URL.

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, routes, static serving
│   │   ├── database.py      # engine / session
│   │   ├── models.py        # SQLAlchemy models (tickets, notes)
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── seed.py          # demo data
│   ├── tests/               # pytest suite
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── api.js           # API client
│   │   ├── components/      # StatusBadge, TicketTable, DashboardCards…
│   │   └── pages/           # Home, NewTicket, TicketDetail
│   └── (Vite + Tailwind config)
├── scripts/smoke_test.py    # end-to-end smoke test
├── Dockerfile               # multi-stage build
├── railway.json
└── .env.example
```

## Demo video

A 3–5 minute walkthrough covering: the app in action (create → search → filter →
update → notes), the code layout, why the stack was chosen, and the dashboard
stand-out feature.