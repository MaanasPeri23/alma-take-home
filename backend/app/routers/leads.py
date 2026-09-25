import re
import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_attorney, get_email_sender, get_storage
from app.email.base import EmailSender
from app.models.attorney import Attorney
from app.models.lead import LeadState
from app.schemas.errors import CONFLICT, NOT_FOUND, UNAUTHORIZED
from app.schemas.lead import LeadDetail, LeadOut, LeadPage, LeadStateUpdate
from app.services import lead_service
from app.services.uploads import UploadRejected
from app.storage.base import StorageBackend

# Collection routes are declared as "" (no trailing slash). FastAPI's slash redirect would send the
# browser to the internal api:8000 host, which it can't reach through the Next.js proxy.
router = APIRouter(prefix="/api/leads", tags=["leads"])

LEAD_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")

DB = Annotated[Session, Depends(get_db)]
Storage = Annotated[StorageBackend, Depends(get_storage)]


def content_disposition(filename: str) -> str:
    """`attachment` with the original name. The ASCII fallback covers old clients; `filename*`
    (RFC 5987) carries the exact name, including spaces and accents."""
    # Uploads are already cleaned (B2), but strip control characters again: a CR/LF here would
    # break the header, and a name could reach the database some other way.
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    ascii_name = filename.encode("ascii", "ignore").decode().replace('"', "") or "resume"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


CurrentAttorney = Annotated[Attorney, Depends(get_current_attorney)]

# Names end up in an email subject line and a Postgres text column: no control characters
# (line breaks, NUL), and at least one visible character.
NAME_PATTERN = r"^[^\x00-\x1f\x7f]*[^\s\x00-\x1f\x7f][^\x00-\x1f\x7f]*$"


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=LeadOut, operation_id="createLead"
)
def create_lead(
    first_name: Annotated[str, Form(min_length=1, max_length=100, pattern=NAME_PATTERN)],
    last_name: Annotated[str, Form(min_length=1, max_length=100, pattern=NAME_PATTERN)],
    email: Annotated[EmailStr, Form()],
    resume: Annotated[UploadFile, File(description="PDF, DOC or DOCX, up to 5 MB")],
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> LeadOut:
    """Public. Every rejection, including a bad file type or size, is a 422 in FastAPI's standard
    validation shape, with `loc` naming the field (e.g. `["body", "resume"]`), so the form can
    show each error under the right input."""
    try:
        lead = lead_service.create_lead(
            db,
            storage,
            first_name=first_name,
            last_name=last_name,
            email=email,
            resume=resume.file,
            resume_filename=resume.filename,
        )
    except UploadRejected as exc:
        raise RequestValidationError(
            [{"loc": ("body", "resume"), "msg": str(exc), "type": "value_error"}]
        ) from exc

    # Sent after the response goes out; the lead is already saved, so a mail outage can't lose it.
    background.add_task(
        lead_service.send_new_lead_emails, lead, email_sender, get_settings().attorney_email
    )
    return LeadOut.model_validate(lead)


@router.get("", response_model=LeadPage, responses=UNAUTHORIZED, operation_id="listLeads")
def list_leads(
    _: CurrentAttorney,
    db: DB,
    state: LeadState | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LeadPage:
    """Newest first."""
    items, total = lead_service.list_leads(db, state=state, limit=limit, offset=offset)
    return LeadPage(
        items=[LeadOut.model_validate(lead) for lead in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadDetail,
    responses={**UNAUTHORIZED, **NOT_FOUND},
    operation_id="getLead",
)
def get_lead(lead_id: uuid.UUID, _: CurrentAttorney, db: DB) -> LeadDetail:
    try:
        return LeadDetail.model_validate(lead_service.get_lead(db, lead_id))
    except lead_service.LeadNotFound as exc:
        raise LEAD_NOT_FOUND from exc


@router.get(
    "/{lead_id}/resume",
    response_class=StreamingResponse,
    responses={
        200: {"description": "The resume file, streamed from storage"},
        **UNAUTHORIZED,
        **NOT_FOUND,
    },
    operation_id="downloadResume",
)
def download_resume(
    lead_id: uuid.UUID, _: CurrentAttorney, db: DB, storage: Storage
) -> StreamingResponse:
    try:
        lead, chunks = lead_service.open_resume(db, storage, lead_id)
    except lead_service.LeadNotFound as exc:
        raise LEAD_NOT_FOUND from exc
    return StreamingResponse(
        chunks,
        media_type=lead.resume_content_type,
        headers={
            "Content-Disposition": content_disposition(lead.resume_filename),
            "Content-Length": str(lead.resume_size_bytes),
            # Resumes are personal data: never let the browser guess the type or cache it.
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.patch(
    "/{lead_id}",
    response_model=LeadDetail,
    responses={**UNAUTHORIZED, **NOT_FOUND, **CONFLICT},
    operation_id="updateLeadState",
)
def update_lead_state(
    lead_id: uuid.UUID, body: LeadStateUpdate, attorney: CurrentAttorney, db: DB
) -> LeadDetail:
    """Moves the lead to `body.state` if the transition is allowed, and records who did it."""
    try:
        lead = lead_service.change_state(db, lead_id, body.state, attorney)
    except lead_service.LeadNotFound as exc:
        raise LEAD_NOT_FOUND from exc
    except lead_service.TransitionNotAllowed as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return LeadDetail.model_validate(lead)
