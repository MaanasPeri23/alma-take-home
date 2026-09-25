import logging
import uuid
from collections.abc import Iterator
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.email import templates
from app.email.base import EmailSender
from app.models.attorney import Attorney
from app.models.lead import Lead, LeadState, LeadStateEvent
from app.services.uploads import inspect_resume, safe_filename
from app.storage.base import ObjectNotFound, StorageBackend

logger = logging.getLogger(__name__)

# Every allowed state change, in one place. Anything not listed is a 409.
# Adding a state later (e.g. REJECTED) means adding it to LeadState and one entry here.
ALLOWED: dict[LeadState, set[LeadState]] = {
    LeadState.PENDING: {LeadState.REACHED_OUT},
    LeadState.REACHED_OUT: {LeadState.PENDING},  # undo
}


class LeadNotFound(Exception):
    pass


class TransitionNotAllowed(Exception):
    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"Can't move a lead from {current} to {requested}")


def create_lead(
    db: Session,
    storage: StorageBackend,
    *,
    first_name: str,
    last_name: str,
    email: str,
    resume: BinaryIO,
    resume_filename: str | None,
) -> Lead:
    """Validate the resume, store it, and save the lead. Raises UploadRejected for a bad file.

    The file is stored first so the lead never points at a missing resume. If saving the lead
    fails, the stored file is deleted again so nothing is left orphaned."""
    info = inspect_resume(resume)
    key = f"resumes/{uuid.uuid4()}"
    storage.put(key, resume, info.content_type)

    lead = Lead(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        resume_key=key,
        resume_filename=safe_filename(resume_filename, info.ext),
        resume_content_type=info.content_type,
        resume_size_bytes=info.size_bytes,
        state=LeadState.PENDING,
    )
    try:
        db.add(lead)
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage.delete(key)
        except Exception as cleanup_exc:
            logger.error("Could not delete orphaned resume %s: %s", key, type(cleanup_exc).__name__)
        raise
    db.refresh(lead)
    return lead


def send_new_lead_emails(lead: Lead, sender: EmailSender, attorney_email: str) -> None:
    """Runs after the response is sent. A failure is logged and never affects the saved lead.
    Logs carry the lead id only, never names or email addresses."""
    for recipient, (subject, body) in (
        (lead.email, templates.prospect_confirmation(lead)),
        (attorney_email, templates.attorney_notification(lead)),
    ):
        try:
            sender.send(recipient, subject, body)
        except Exception as exc:
            # Only the error type: SMTP errors can quote the recipient address.
            logger.error(
                "Failed to send new-lead email for lead %s: %s", lead.id, type(exc).__name__
            )


def list_leads(
    db: Session, *, state: LeadState | None, limit: int, offset: int
) -> tuple[list[Lead], int]:
    """Newest first. The order matches the (state, created_at DESC, id DESC) index."""
    query = select(Lead)
    count = select(func.count()).select_from(Lead)
    if state is not None:
        query = query.where(Lead.state == state)
        count = count.where(Lead.state == state)
    items = db.scalars(
        query.order_by(Lead.created_at.desc(), Lead.id.desc()).limit(limit).offset(offset)
    ).all()
    return list(items), db.scalar(count) or 0


def get_lead(db: Session, lead_id: uuid.UUID) -> Lead:
    """The lead with its full history and who made each change, loaded up front."""
    lead = db.scalar(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(selectinload(Lead.events).selectinload(LeadStateEvent.actor))
    )
    if lead is None:
        raise LeadNotFound
    return lead


def change_state(db: Session, lead_id: uuid.UUID, new_state: LeadState, actor: Attorney) -> Lead:
    """Move a lead to `new_state` if ALLOWED permits it, and record who did it.

    The row is locked (SELECT ... FOR UPDATE), so two attorneys clicking at the same moment
    can't both apply the same change. The state update and its history row commit together."""
    lead = db.scalar(select(Lead).where(Lead.id == lead_id).with_for_update())
    if lead is None:
        raise LeadNotFound
    current = LeadState(lead.state)
    if new_state not in ALLOWED.get(current, set()):
        db.rollback()  # release the lock
        raise TransitionNotAllowed(current, new_state)

    lead.state = new_state
    db.add(LeadStateEvent(lead_id=lead.id, from_state=current, to_state=new_state, actor=actor))
    db.commit()
    db.expire_all()  # reload history and updated_at below
    return get_lead(db, lead_id)


def open_resume(
    db: Session, storage: StorageBackend, lead_id: uuid.UUID
) -> tuple[Lead, Iterator[bytes]]:
    """The lead and a stream of its resume. Raises LeadNotFound before any bytes are sent if
    either the lead or its file is missing."""
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise LeadNotFound
    try:
        return lead, storage.open(lead.resume_key)
    except ObjectNotFound as exc:
        logger.error("Resume object missing for lead %s", lead.id)
        raise LeadNotFound from exc
