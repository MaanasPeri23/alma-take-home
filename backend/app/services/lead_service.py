import logging
import uuid
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.email import templates
from app.email.base import EmailSender
from app.models.lead import Lead, LeadState
from app.services.uploads import inspect_resume, safe_filename
from app.storage.base import StorageBackend

logger = logging.getLogger(__name__)


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
