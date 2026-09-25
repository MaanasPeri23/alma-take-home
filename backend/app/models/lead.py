import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LeadState(StrEnum):
    # Stored as a plain varchar, so adding a state is a code change, not a migration.
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    # Not unique: a prospect may submit more than once.
    email: Mapped[str] = mapped_column(String(320))

    resume_key: Mapped[str] = mapped_column(String(64))
    resume_filename: Mapped[str] = mapped_column(String(255))
    resume_content_type: Mapped[str] = mapped_column(String(100))
    resume_size_bytes: Mapped[int] = mapped_column(Integer)

    state: Mapped[str] = mapped_column(String(32), default=LeadState.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["LeadStateEvent"]] = relationship(
        back_populates="lead", order_by="LeadStateEvent.created_at"
    )


# Serves the dashboard list: filter by state, newest first, stable tiebreak on id.
Index("ix_leads_state_created_id", Lead.state, Lead.created_at.desc(), Lead.id.desc())


class LeadStateEvent(Base):
    """One row per state change, written in the same transaction as the change itself."""

    __tablename__ = "lead_state_events"
    __table_args__ = (Index("ix_lead_state_events_lead_created", "lead_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    from_state: Mapped[str] = mapped_column(String(32))
    to_state: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attorneys.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="events")
