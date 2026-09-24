import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .models import STATUSES
from .seed import maybe_seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    if os.getenv("AUTO_SEED_DEMO", "1") != "0":
        maybe_seed()
    yield


app = FastAPI(title="SupportTick CRM API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ticket_from(ticket_id: str, db: Session) -> models.Ticket:
    ticket = db.scalar(select(models.Ticket).where(models.Ticket.ticket_id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/tickets", response_model=schemas.TicketCreateResponse, status_code=201)
def create_ticket(payload: schemas.TicketCreate, db: Session = Depends(get_db)) -> schemas.TicketCreateResponse:
    # Human-friendly ticket reference (TKT-0001, TKT-0002, ...) derived from the
    # current row count so it exists before the insert satisfies NOT NULL.
    base = (db.scalar(select(func.max(models.Ticket.id))) or 0) + 1
    candidate = f"TKT-{base:04d}"
    while db.scalar(select(models.Ticket).where(models.Ticket.ticket_id == candidate)):
        base += 1
        candidate = f"TKT-{base:04d}"

    ticket = models.Ticket(
        ticket_id=candidate,
        customer_name=payload.customer_name.strip(),
        customer_email=str(payload.customer_email).strip(),
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        status="Open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return schemas.TicketCreateResponse(id=ticket.id, ticket_id=ticket.ticket_id, created_at=ticket.created_at)


@app.get("/api/tickets", response_model=list[schemas.TicketListItem])
def list_tickets(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    search: Optional[str] = Query(default=None, description="Search across id, name, email, subject, description"),
    db: Session = Depends(get_db),
) -> list[models.Ticket]:
    query = select(models.Ticket)
    if status:
        if status not in STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {STATUSES}")
        query = query.where(models.Ticket.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                models.Ticket.ticket_id.ilike(term),
                models.Ticket.customer_name.ilike(term),
                models.Ticket.customer_email.ilike(term),
                models.Ticket.subject.ilike(term),
                models.Ticket.description.ilike(term),
            )
        )
    query = query.order_by(models.Ticket.created_at.desc())
    return list(db.scalars(query).all())


@app.get("/api/tickets/{ticket_id}", response_model=schemas.TicketDetail)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> models.Ticket:
    return _ticket_from(ticket_id, db)


@app.put("/api/tickets/{ticket_id}", response_model=schemas.UpdateResponse)
def update_ticket(
    ticket_id: str, payload: schemas.TicketUpdate, db: Session = Depends(get_db)
) -> schemas.UpdateResponse:
    ticket = _ticket_from(ticket_id, db)

    if payload.status is not None:
        if payload.status not in STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {STATUSES}")
        ticket.status = payload.status

    if payload.note_text is not None and payload.note_text.strip():
        ticket.notes.append(models.Note(ticket_id=ticket.ticket_id, note_text=payload.note_text.strip()))

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return schemas.UpdateResponse(success=True, updated_at=ticket.updated_at)


@app.post("/api/tickets/{ticket_id}/notes", response_model=schemas.NoteOut, status_code=201)
def add_note(ticket_id: str, payload: schemas.NoteCreate, db: Session = Depends(get_db)) -> models.Note:
    ticket = _ticket_from(ticket_id, db)
    note = models.Note(ticket_id=ticket.ticket_id, note_text=payload.note_text.strip(), author=payload.author.strip())
    db.add(note)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


@app.get("/api/dashboard", response_model=schemas.DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> schemas.DashboardResponse:
    total = db.scalar(select(func.count(models.Ticket.id))) or 0
    counts: dict[str, int] = {}
    for status in STATUSES:
        counts[status] = db.scalar(
            select(func.count(models.Ticket.id)).where(models.Ticket.status == status)
        ) or 0

    recent_tickets = list(
        db.scalars(select(models.Ticket).order_by(models.Ticket.created_at.desc()).limit(6)).all()
    )
    recent_activity = list(
        db.scalars(select(models.Note).order_by(models.Note.created_at.desc()).limit(8)).all()
    )

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=6)
    day_rows = db.execute(
        select(func.date(models.Ticket.created_at), func.count(models.Ticket.id))
        .where(models.Ticket.created_at >= seven_days_ago)
        .group_by(func.date(models.Ticket.created_at))
    ).all()
    by_day = {str(day): count for day, count in day_rows}
    tickets_by_day: list[dict[str, int | str]] = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).strftime("%Y-%m-%d")
        tickets_by_day.append({"date": day, "count": by_day.get(day, 0)})

    return schemas.DashboardResponse(
        total=total,
        open_count=counts["Open"],
        in_progress_count=counts["In Progress"],
        closed_count=counts["Closed"],
        recent_tickets=recent_tickets,
        recent_activity=recent_activity,
        tickets_by_day=tickets_by_day,
    )


# --- Serve the built React frontend (single-service deployment). -------------
def _find_frontend_build() -> Optional[str]:
    candidates = [
        os.getenv("STATIC_DIR"),
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"),
        os.path.join(os.path.dirname(__file__), "static"),
        "/app/frontend/dist",
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    return None


_FRONTEND_DIR = _find_frontend_build()
if _FRONTEND_DIR:
    assets_dir = os.path.join(_FRONTEND_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        index_path = os.path.join(_FRONTEND_DIR, "index.html")
        return FileResponse(index_path)