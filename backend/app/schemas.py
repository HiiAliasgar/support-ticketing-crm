from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import PRIORITIES, STATUSES


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_email: EmailStr
    subject: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    priority: str | None = Field(default=None, pattern="|".join(PRIORITIES))


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    customer_name: str
    subject: str
    status: str
    priority: str
    assignee_id: int | None = None
    assignee_name: str | None = None
    created_at: datetime


class TicketPage(BaseModel):
    items: list[TicketListItem]
    total: int
    page: int
    per_page: int
    pages: int


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    note_text: str
    author: str
    created_at: datetime


class TicketDetail(TicketListItem):
    customer_email: str
    description: str
    updated_at: datetime
    notes: list[NoteOut] = []


class TicketCreateResponse(BaseModel):
    id: int
    ticket_id: str
    created_at: datetime


class NoteCreate(BaseModel):
    note_text: str = Field(min_length=1)
    author: str = Field(default="Agent", max_length=80)


class TicketUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="|".join(STATUSES))
    priority: str | None = Field(default=None, pattern="|".join(PRIORITIES))
    assignee_id: int | None = Field(default=None)
    note_text: str | None = Field(default=None, min_length=1)


class AssignRequest(BaseModel):
    assignee_id: int | None = Field(default=None)


class UpdateResponse(BaseModel):
    success: bool
    updated_at: datetime


class AssignResponse(BaseModel):
    success: bool
    updated_at: datetime
    assignee_id: int | None = None
    assignee_name: str | None = None


class DashboardResponse(BaseModel):
    total: int
    open_count: int
    in_progress_count: int
    closed_count: int
    by_priority: dict[str, int] = {}
    recent_tickets: list[TicketListItem]
    recent_activity: list[NoteOut]
    tickets_by_day: list[dict[str, int | str]]


# --- Auth ----------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    role: str
    active: bool


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# --- Admin ---------------------------------------------------------------
class AgentCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(default="", max_length=120)
    role: str = Field(default="agent", pattern="|".join(("admin", "agent")))
    password: str = Field(min_length=8, max_length=200)


class AgentUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, pattern="|".join(("admin", "agent")))
    active: bool | None = Field(default=None)
    password: str | None = Field(default=None, min_length=8, max_length=200)


class SettingsUpdate(BaseModel):
    workspace_name: str | None = Field(default=None, max_length=120)
    ticket_prefix: str | None = Field(default=None, min_length=1, max_length=8)
    sla_hours: int | None = Field(default=None, ge=1, le=720)
    default_note_author: str | None = Field(default=None, max_length=80)


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    action: str
    target: str
    detail: str
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    page: int
    per_page: int
    pages: int


class BulkStatusUpdate(BaseModel):
    status: str = Field(pattern="|".join(STATUSES))
    ticket_ids: list[str] = Field(min_length=1)