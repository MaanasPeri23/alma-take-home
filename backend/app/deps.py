"""Shared FastAPI dependencies. Tests swap these out with `app.dependency_overrides`."""

from functools import lru_cache

from app.config import get_settings
from app.email.base import EmailSender
from app.email.smtp import SmtpEmailSender
from app.storage.base import StorageBackend
from app.storage.s3 import S3Storage


@lru_cache
def get_storage() -> StorageBackend:
    return S3Storage(get_settings())


@lru_cache
def get_email_sender() -> EmailSender:
    return SmtpEmailSender(get_settings())
