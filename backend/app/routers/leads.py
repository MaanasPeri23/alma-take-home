import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import EmailStr

from app.models.lead import LeadState
from app.schemas.errors import CONFLICT, NOT_FOUND, UNAUTHORIZED
from app.schemas.lead import LeadDetail, LeadOut, LeadPage, LeadStateUpdate

# Collection routes are declared as "" (no trailing slash). FastAPI's slash redirect would send the
# browser to the internal api:8000 host, which it can't reach through the Next.js proxy.
router = APIRouter(prefix="/api/leads", tags=["leads"])

NOT_IMPLEMENTED = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented yet")


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=LeadOut, operation_id="createLead"
)
def create_lead(
    first_name: Annotated[str, Form(min_length=1, max_length=100)],
    last_name: Annotated[str, Form(min_length=1, max_length=100)],
    email: Annotated[EmailStr, Form()],
    resume: Annotated[UploadFile, File(description="PDF, DOC or DOCX, up to 5 MB")],
) -> LeadOut:
    """Public. Every rejection, including a bad file type or size, is a 422 in FastAPI's standard
    validation shape, with `loc` naming the field (e.g. `["body", "resume"]`), so the form can
    show each error under the right input."""
    raise NOT_IMPLEMENTED


@router.get("", response_model=LeadPage, responses=UNAUTHORIZED, operation_id="listLeads")
def list_leads(
    state: LeadState | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LeadPage:
    """Newest first."""
    raise NOT_IMPLEMENTED


@router.get(
    "/{lead_id}",
    response_model=LeadDetail,
    responses={**UNAUTHORIZED, **NOT_FOUND},
    operation_id="getLead",
)
def get_lead(lead_id: uuid.UUID) -> LeadDetail:
    raise NOT_IMPLEMENTED


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
def download_resume(lead_id: uuid.UUID) -> StreamingResponse:
    raise NOT_IMPLEMENTED


@router.patch(
    "/{lead_id}",
    response_model=LeadDetail,
    responses={**UNAUTHORIZED, **NOT_FOUND, **CONFLICT},
    operation_id="updateLeadState",
)
def update_lead_state(lead_id: uuid.UUID, body: LeadStateUpdate) -> LeadDetail:
    """Moves the lead to `body.state` if the transition is allowed, and records who did it."""
    raise NOT_IMPLEMENTED
