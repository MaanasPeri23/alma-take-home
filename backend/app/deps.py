"""Shared FastAPI dependencies. Tests swap these out with `app.dependency_overrides`."""

from functools import lru_cache
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.email.base import EmailSender
from app.email.smtp import SmtpEmailSender
from app.models.attorney import Attorney
from app.services import auth_service
from app.storage.base import StorageBackend
from app.storage.s3 import S3Storage


@lru_cache
def get_storage() -> StorageBackend:
    return S3Storage(get_settings())


@lru_cache
def get_email_sender() -> EmailSender:
    return SmtpEmailSender(get_settings())


SESSION_COOKIE = "session"


def get_current_attorney(
    db: Annotated[Session, Depends(get_db)],
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Attorney:
    """Every internal route depends on this. It's the real auth check; the web app's redirect
    to /login only makes the pages behave nicely."""
    attorney = auth_service.attorney_from_token(db, session)
    if attorney is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return attorney
