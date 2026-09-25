from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.deps import get_storage
from app.routers import auth, leads


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Create the resumes bucket on first boot, so a fresh `make up` needs no manual setup.
    # Resolved through dependency_overrides so tests using `with TestClient(app)` never touch MinIO.
    storage = app.dependency_overrides.get(get_storage, get_storage)()
    storage.ensure_bucket()
    yield


app = FastAPI(title="Leads API", lifespan=lifespan)
app.include_router(leads.router)
app.include_router(auth.router)


@app.get("/health", operation_id="health")
def health() -> dict[str, str]:
    return {"status": "ok"}
