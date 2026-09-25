from functools import lru_cache

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

    jwt_secret: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
