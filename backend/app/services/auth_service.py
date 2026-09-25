import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.attorney import Attorney

JWT_ALGORITHM = "HS256"

# bcrypt only uses the first 72 bytes of a password, and bcrypt 5 raises on anything longer.
MAX_PASSWORD_BYTES = 72

# Checked against when the email doesn't exist, so a wrong email takes as long as a wrong
# password and response times don't reveal which addresses have accounts.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Passwords can be at most {MAX_PASSWORD_BYTES} bytes.")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        # No stored password can be this long. Still do one bcrypt check so timing matches.
        bcrypt.checkpw(b"x", _DUMMY_HASH.encode())
        return False
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def authenticate(db: Session, email: str, password: str) -> Attorney | None:
    attorney = db.scalar(select(Attorney).where(func.lower(Attorney.email) == email.lower()))
    if attorney is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return attorney if verify_password(password, attorney.password_hash) else None


def create_session_token(attorney_id: uuid.UUID, now: datetime | None = None) -> str:
    settings = get_settings()
    issued = now or datetime.now(UTC)
    claims = {
        "sub": str(attorney_id),
        "iat": issued,
        "exp": issued + timedelta(minutes=settings.session_ttl_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def attorney_from_token(db: Session, token: str | None) -> Attorney | None:
    """The attorney a session token belongs to, or None if the token is missing, forged,
    expired, malformed, or points at an attorney that no longer exists."""
    if not token:
        return None
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[JWT_ALGORITHM],  # pinned: rejects "alg: none" and algorithm swaps
            options={"require": ["exp", "iat", "sub"]},  # a token without exp never expires
        )
        attorney_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return db.get(Attorney, attorney_id)
