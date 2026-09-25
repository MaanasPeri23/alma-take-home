from fastapi import FastAPI

from app.routers import auth, leads

app = FastAPI(title="Leads API")
app.include_router(leads.router)
app.include_router(auth.router)


@app.get("/health", operation_id="health")
def health() -> dict[str, str]:
    return {"status": "ok"}
