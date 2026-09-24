import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import (
    authenticate,
    create_session,
    current_user,
    get_setting,
    hash_password,
    log_action,
    require_admin,
    set_setting,
)
from .database import Base, engine, get_db
from .models import PRIORITIES, ROLES, STATUSES, User
from .seed import maybe_seed, maybe_seed_users


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    maybe_seed_users()
    if os.getenv("AUTO_SEED_DEMO", "1") != "0":
        maybe_seed()
    yield


app = FastAPI(title="SupportTick CRM API", version="2.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_http_bearer = HTTPBearer(auto_error=False)


def _ticket_from(ticket_id: str, db: Session) -> models.Ticket:
    ticket = db.scalar(select(models.Ticket).where(models.Ticket.ticket_id == ticket_id))
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


def _next_ticket_id(db: Session) -> str:
    prefix = (get_setting(db, "ticket_prefix") or "TKT").strip().upper()
    base = (db.scalar(select(func.max(models.Ticket.id))) or 0) + 1
    while True:
        candidate = f"{prefix}-{base:04d}"
        if not db.scalar(select(models.Ticket).where(models.Ticket.ticket_id == candidate)):
            return candidate
        base += 1


# --- Health / meta -----------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- Public ticket endpoints ---------------------------------------------------
@app.post("/api/tickets", response_model=schemas.TicketCreateResponse, status_code=201)
def create_ticket(payload: schemas.TicketCreate, db: Session = Depends(get_db)) -> schemas.TicketCreateResponse:
    ticket = models.Ticket(
        ticket_id=_next_ticket_id(db),
        customer_name=payload.customer_name.strip(),
        customer_email=str(payload.customer_email).strip(),
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        status="Open",
        priority=(payload.priority or "Medium").strip(),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return schemas.TicketCreateResponse(id=ticket.id, ticket_id=ticket.ticket_id, created_at=ticket.created_at)


@app.get("/api/tickets", response_model=None)
def list_tickets(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    assignee_id: Optional[int] = Query(default=None, description="Filter by assigned agent id"),
    search: Optional[str] = Query(default=None, description="Search across id, name, email, subject, description"),
    page: Optional[int] = Query(default=None, ge=1, description="Enable pagination (1-based)"),
    per_page: Optional[int] = Query(default=None, ge=1, le=100, description="Items per page (with page)"),
    db: Session = Depends(get_db),
):
    query = select(models.Ticket)
    if status:
        if status not in STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {STATUSES}")
        query = query.where(models.Ticket.status == status)
    if priority:
        if priority not in PRIORITIES:
            raise HTTPException(status_code=422, detail=f"priority must be one of {PRIORITIES}")
        query = query.where(models.Ticket.priority == priority)
    if assignee_id is not None:
        query = query.where(models.Ticket.assignee_id == assignee_id)
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

    if page is not None:
        per_page = per_page or 25
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        pages = max((total + per_page - 1) // per_page, 1)
        items = list(db.scalars(query.offset((page - 1) * per_page).limit(per_page)).all())
        return schemas.TicketPage(
            items=items, total=total, page=page, per_page=per_page, pages=pages
        )

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

    if payload.priority is not None:
        if payload.priority not in PRIORITIES:
            raise HTTPException(status_code=422, detail=f"priority must be one of {PRIORITIES}")
        ticket.priority = payload.priority

    if payload.assignee_id is not None:
        assignee = db.get(models.User, payload.assignee_id)
        if assignee is None or assignee.role != "agent" or not assignee.active:
            raise HTTPException(status_code=422, detail="Assignee must be an active agent")
        ticket.assignee_id = assignee.id

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


@app.post("/api/tickets/{ticket_id}/assign", response_model=schemas.AssignResponse)
def assign_ticket(
    ticket_id: str,
    payload: schemas.AssignRequest,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
) -> schemas.AssignResponse:
    ticket = _ticket_from(ticket_id, db)
    if payload.assignee_id is None:
        ticket.assignee_id = None
    else:
        assignee = db.get(models.User, payload.assignee_id)
        if assignee is None or assignee.role != "agent" or not assignee.active:
            raise HTTPException(status_code=422, detail="Assignee must be an active agent")
        ticket.assignee_id = assignee.id
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    log_action(db, user, "ticket.assign", ticket_id, f"assigned to user {ticket.assignee_id}")
    return schemas.AssignResponse(
        success=True,
        updated_at=ticket.updated_at,
        assignee_id=ticket.assignee_id,
        assignee_name=ticket.assignee_name,
    )


@app.get("/api/agents")
def list_agents(db: Session = Depends(get_db)) -> list[dict]:
    agents = db.scalars(select(models.User).where(models.User.role == "agent", models.User.active.is_(True))).all()
    return [
        {"id": agent.id, "username": agent.username, "display_name": agent.display_name}
        for agent in agents
    ]


@app.get("/api/dashboard", response_model=schemas.DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> schemas.DashboardResponse:
    total = db.scalar(select(func.count(models.Ticket.id))) or 0
    counts: dict[str, int] = {}
    for status in STATUSES:
        counts[status] = db.scalar(
            select(func.count(models.Ticket.id)).where(models.Ticket.status == status)
        ) or 0
    by_priority: dict[str, int] = {}
    for priority in PRIORITIES:
        by_priority[priority] = db.scalar(
            select(func.count(models.Ticket.id)).where(models.Ticket.priority == priority)
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
        by_priority=by_priority,
        recent_tickets=recent_tickets,
        recent_activity=recent_activity,
        tickets_by_day=tickets_by_day,
    )


# --- Auth ---------------------------------------------------------------------
@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    user = authenticate(db, payload.username.strip(), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session = create_session(db, user)
    return schemas.LoginResponse(token=session.token, user=schemas.UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)) -> models.User:
    return user


@app.post("/api/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(_http_bearer),
    db: Session = Depends(get_db),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    session = db.scalar(select(models.Session).where(models.Session.token == credentials.credentials))
    if session:
        db.delete(session)
        db.commit()
    return {"success": True}


# --- Admin: agents ------------------------------------------------------------
@app.get("/api/admin/agents", response_model=list[schemas.UserOut])
def admin_list_agents(
    user: models.User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[models.User]:
    return list(db.scalars(select(models.User).order_by(models.User.role, models.User.username)).all())


@app.post("/api/admin/agents", response_model=schemas.UserOut, status_code=201)
def admin_create_agent(
    payload: schemas.AgentCreate,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> models.User:
    if db.scalar(select(models.User).where(models.User.username == payload.username.strip())):
        raise HTTPException(status_code=409, detail="Username already exists")
    digest, salt, iterations = hash_password(payload.password)
    agent = models.User(
        username=payload.username.strip(),
        display_name=payload.display_name.strip(),
        role=payload.role,
        password_hash=digest,
        salt=salt,
        password_iterations=iterations,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    log_action(db, user, "agent.create", agent.username, f"created {agent.role}")
    return agent


@app.patch("/api/admin/agents/{agent_id}", response_model=schemas.UserOut)
def admin_update_agent(
    agent_id: int,
    payload: schemas.AgentUpdate,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> models.User:
    agent = db.get(models.User, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.id == user.id and payload.active is False:
        raise HTTPException(status_code=422, detail="You cannot deactivate your own account")

    changed = []
    if payload.display_name is not None:
        agent.display_name = payload.display_name.strip()
        changed.append("display_name")
    if payload.role is not None:
        if agent.id == user.id and payload.role != "admin":
            raise HTTPException(status_code=422, detail="You cannot demote your own account")
        agent.role = payload.role
        changed.append("role")
    if payload.active is not None:
        agent.active = payload.active
        changed.append("active")
    if payload.password is not None:
        digest, salt, iterations = hash_password(payload.password)
        agent.password_hash = digest
        agent.salt = salt
        agent.password_iterations = iterations
        changed.append("password")

    db.commit()
    db.refresh(agent)
    log_action(db, user, "agent.update", agent.username, f"updated: {', '.join(changed)}")
    return agent


@app.get("/api/admin/settings")
def admin_get_settings(
    user: models.User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict:
    keys = ["workspace_name", "ticket_prefix", "sla_hours", "default_note_author"]
    return {key: get_setting(db, key) for key in keys}


@app.put("/api/admin/settings")
def admin_update_settings(
    payload: schemas.SettingsUpdate,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    updates = {
        "workspace_name": payload.workspace_name,
        "ticket_prefix": payload.ticket_prefix,
        "sla_hours": str(payload.sla_hours) if payload.sla_hours is not None else None,
        "default_note_author": payload.default_note_author,
    }
    changed = []
    for key, value in updates.items():
        if value is not None:
            set_setting(db, key, value)
            changed.append(key)
    log_action(db, user, "settings.update", "", f"updated: {', '.join(changed)}")
    return {key: get_setting(db, key) for key in updates}


@app.get("/api/admin/audit", response_model=schemas.AuditPage)
def admin_audit(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=200),
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> schemas.AuditPage:
    total = db.scalar(select(func.count(models.AuditLog.id))) or 0
    pages = max((total + per_page - 1) // per_page, 1)
    items = list(
        db.scalars(select(models.AuditLog).order_by(models.AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    )
    return schemas.AuditPage(items=items, total=total, page=page, per_page=per_page, pages=pages)


@app.delete("/api/tickets/{ticket_id}", response_model=dict)
def admin_delete_ticket(
    ticket_id: str,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    ticket = _ticket_from(ticket_id, db)
    subject = ticket.subject
    db.delete(ticket)
    db.commit()
    log_action(db, user, "ticket.delete", ticket_id, f"deleted '{subject}'")
    return {"success": True}


@app.post("/api/admin/tickets/bulk-status", response_model=dict)
def admin_bulk_status(
    payload: schemas.BulkStatusUpdate,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    updated = 0
    for ticket_id in payload.ticket_ids:
        ticket = db.scalar(select(models.Ticket).where(models.Ticket.ticket_id == ticket_id))
        if ticket is not None:
            ticket.status = payload.status
            ticket.updated_at = datetime.now(timezone.utc)
            updated += 1
    db.commit()
    log_action(db, user, "ticket.bulk_status", f"{updated} ticket(s)", f"set status to {payload.status}")
    return {"success": True, "updated": updated}


@app.get("/api/admin/export")
def admin_export_csv(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    tickets = list(
        db.scalars(
            select(models.Ticket).order_by(models.Ticket.created_at.desc())
        ).all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "ticket_id", "customer_name", "customer_email", "subject", "description",
            "status", "priority", "assignee", "created_at", "updated_at", "note_count",
        ]
    )
    for ticket in tickets:
        writer.writerow(
            [
                ticket.ticket_id,
                ticket.customer_name,
                ticket.customer_email,
                ticket.subject,
                ticket.description,
                ticket.status,
                ticket.priority,
                ticket.assignee_name or "",
                ticket.created_at.isoformat() if ticket.created_at else "",
                ticket.updated_at.isoformat() if ticket.updated_at else "",
                len(ticket.notes),
            ]
        )
    log_action(db, user, "ticket.export", f"{len(tickets)} ticket(s)", "CSV export")
    return PlainTextResponse(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tickets.csv"'},
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