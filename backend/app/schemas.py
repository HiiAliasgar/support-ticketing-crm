from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import STATUSES


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_email: EmailStr
    subject: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)


class TicketListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    customer_name: str
    subject: str
    status: str
    created_at: datetime


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
    note_text: str | None = Field(default=None, min_length=1)


class UpdateResponse(BaseModel):
    success: bool
    updated_at: datetime | None = None


class DashboardResponse(BaseModel):
    total: int
    open_count: int
    in_progress_count: int
    closed_count: int
    recent_tickets: list[TicketListItem]
    recent_activity: list[NoteOut]
    tickets_by_day: list[dict[str, int | str]]