# SupportTick — Customer Support Ticketing CRM

A full-stack help-desk application for creating, searching, filtering and resolving customer support tickets. It combines a FastAPI backend with a React interface and a small relational data model.

**Live application:** https://support-ticketing-crm-production-1ba5.up.railway.app  
**Source code:** https://github.com/HiiAliasgar/support-ticketing-crm

## Product workflow

1. Create a ticket with customer details, subject and description.
2. Generate a ticket identifier and timestamp.
3. Search across ticket fields.
4. Filter the queue by Open, In Progress or Closed status.
5. Open a ticket, update its status and add internal notes.
6. Review ticket counts, recent volume and note activity on the dashboard.

## Engineering highlights

- FastAPI routes with request/response validation.
- React, Vite and Tailwind frontend.
- SQLite persistence with ticket and note records.
- Search and status-filter query parameters.
- Aggregate dashboard endpoints.
- Multi-stage Docker build and Railway deployment configuration.
- Pytest API tests and a server-level smoke-test script.

## Technology

| Layer | Stack |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| Frontend | React, Vite, Tailwind CSS |
| Database | SQLite |
| Testing | pytest, smoke-test script |
| Deployment | Docker, Railway |

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend development server

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server runs on port 5173 and proxies API requests to the backend on port 8000.

### Tests

```bash
cd backend
python -m pytest -q
python ../scripts/smoke_test.py
```

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/tickets` | Create a ticket |
| GET | `/api/tickets` | List, search and filter tickets |
| GET | `/api/tickets/{ticket_id}` | Read ticket details |
| PUT | `/api/tickets/{ticket_id}` | Update ticket status/details |
| POST | `/api/tickets/{ticket_id}/notes` | Add an internal note |
| GET | `/api/dashboard` | Dashboard aggregates |

Interactive API documentation is available at `/api/docs` when the backend is running.

## Deployment

The repository includes a Dockerfile and Railway configuration. For persistent SQLite data across redeployments, configure a persistent volume and point the database path to that mounted location.

## Design trade-offs

The application uses a compact two-table model for tickets and notes. Dashboard summaries are computed with aggregate queries rather than a separate analytics store. This keeps the project easy to run locally while demonstrating common support-operations workflows.

[Open the live application](https://support-ticketing-crm-production-1ba5.up.railway.app) · [Browse the source](https://github.com/HiiAliasgar/support-ticketing-crm)
