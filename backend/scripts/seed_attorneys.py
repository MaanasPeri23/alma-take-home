"""Create the attorney account from SEED_ATTORNEY_EMAIL and SEED_ATTORNEY_PASSWORD (`make seed`).

Safe to run repeatedly: an existing account gets its password reset to the configured one.
There's no public signup; this script is the only way accounts are made."""

import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models.attorney import Attorney
from app.services.auth_service import hash_password


def seed(db: Session, email: str, password: str, name: str = "Demo Attorney") -> Attorney:
    attorney = db.scalar(select(Attorney).where(func.lower(Attorney.email) == email.lower()))
    if attorney is None:
        attorney = Attorney(email=email.lower(), name=name, password_hash=hash_password(password))
        db.add(attorney)
    else:
        attorney.password_hash = hash_password(password)
    db.commit()
    return attorney


if __name__ == "__main__":
    settings = get_settings()
    if not settings.seed_attorney_email or not settings.seed_attorney_password:
        sys.exit("Set SEED_ATTORNEY_EMAIL and SEED_ATTORNEY_PASSWORD in .env first.")
    with SessionLocal() as session:
        seeded = seed(session, settings.seed_attorney_email, settings.seed_attorney_password)
        # Never print the password.
        print(f"Attorney ready: {seeded.email} (password from SEED_ATTORNEY_PASSWORD in .env)")
