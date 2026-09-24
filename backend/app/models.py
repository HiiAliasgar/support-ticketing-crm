from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

STATUSES = ("Open", "In Progress", "Closed")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    notes: Mapped[list["Note"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Note.created_at",
    )


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), index=True, nullable=False
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(80), default="Agent", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="notes")