import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.lead import LeadState


class StateEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_state: LeadState
    to_state: LeadState
    actor_id: uuid.UUID
    actor_name: str
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    resume_filename: str
    resume_content_type: str
    resume_size_bytes: int
    state: LeadState
    created_at: datetime
    updated_at: datetime


class LeadDetail(LeadOut):
    history: list[StateEventOut]


class LeadPage(BaseModel):
    items: list[LeadOut]
    total: int
    limit: int
    offset: int


class LeadStateUpdate(BaseModel):
    state: LeadState
