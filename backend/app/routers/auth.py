from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import AttorneyOut, LoginRequest
from app.schemas.errors import UNAUTHORIZED

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Name of the httpOnly cookie holding the JWT. The frontend's signed-out redirect checks for it.
SESSION_COOKIE = "session"

NOT_IMPLEMENTED = HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented yet")


@router.post("/login", response_model=AttorneyOut, responses=UNAUTHORIZED, operation_id="login")
def login(body: LoginRequest) -> AttorneyOut:
    """Checks the password and sets the `session` httpOnly cookie. Wrong email or password: 401."""
    raise NOT_IMPLEMENTED


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=UNAUTHORIZED,
    operation_id="logout",
)
def logout() -> None:
    raise NOT_IMPLEMENTED


@router.get("/me", response_model=AttorneyOut, responses=UNAUTHORIZED, operation_id="me")
def me() -> AttorneyOut:
    raise NOT_IMPLEMENTED
