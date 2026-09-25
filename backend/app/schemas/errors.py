from pydantic import BaseModel


class ErrorOut(BaseModel):
    """Body of every non-validation error (401, 404, 409): FastAPI's HTTPException shape."""

    detail: str


def error(description: str) -> dict:
    return {"model": ErrorOut, "description": description}


UNAUTHORIZED = {401: error("Not signed in, or the session expired")}
NOT_FOUND = {404: error("No lead with this id")}
CONFLICT = {409: error("That state change isn't allowed from the lead's current state")}
