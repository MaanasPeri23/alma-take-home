from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Every env var the API reads. docker-compose supplies them from .env.

    Secrets have no defaults, so a missing value fails at startup instead of
    silently signing cookies or talking to storage with a known key.
    """

    database_url: str = "postgresql+psycopg://leads:leads@db:5432/leads"

    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "resumes"

    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    email_from: str = "leads@example.com"
    attorney_email: str = "attorney@example.com"

    # Signs session tokens. HS256 needs at least 32 bytes to be safe, so shorter keys fail startup.
    jwt_secret: str = Field(min_length=32)
    session_ttl_minutes: int = 8 * 60
    # True in production (HTTPS only). False locally, where everything runs over plain http.
    cookie_secure: bool = False

    # Used only by scripts/seed_attorneys.py.
    seed_attorney_email: str | None = None
    seed_attorney_password: str | None = None

    # Where the web app lives, for links in emails.
    public_base_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
