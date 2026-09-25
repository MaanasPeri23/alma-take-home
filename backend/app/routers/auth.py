from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import SESSION_COOKIE, get_current_attorney
from app.models.attorney import Attorney
from app.schemas.auth import AttorneyOut, LoginRequest
from app.schemas.errors import UNAUTHORIZED
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

CurrentAttorney = Annotated[Attorney, Depends(get_current_attorney)]


@router.post("/login", response_model=AttorneyOut, responses=UNAUTHORIZED, operation_id="login")
def login(
    body: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]
) -> AttorneyOut:
    """Checks the password and sets the `session` httpOnly cookie. Wrong email or password: 401."""
    attorney = auth_service.authenticate(db, body.email, body.password)
    if attorney is None:
        # Same message either way, so the response doesn't reveal which emails have accounts.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        auth_service.create_session_token(attorney.id),
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,  # page JavaScript can't read it, so an XSS bug can't steal the session
        samesite="lax",  # not sent on cross-site POST/PATCH
        secure=settings.cookie_secure,
        path="/",
    )
    return AttorneyOut.model_validate(attorney)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, operation_id="logout")
def logout(response: Response) -> None:
    """Always clears the session cookie, even if it's expired or invalid, and always returns 204.

    The cookie is httpOnly, so the web app can't delete a stale one itself; without this, a dead
    cookie could bounce an attorney between /login and the dashboard. Clearing a cookie grants
    nothing, so it doesn't need a valid session."""
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=get_settings().cookie_secure
    )


@router.get("/me", response_model=AttorneyOut, responses=UNAUTHORIZED, operation_id="me")
def me(attorney: CurrentAttorney) -> AttorneyOut:
    return AttorneyOut.model_validate(attorney)
