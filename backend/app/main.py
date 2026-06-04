from fastapi import FastAPI

from app.config import settings
from app.routes.health import router as health_router

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
)

app.include_router(health_router)


@app.on_event("startup")
async def startup_event():
    """Run on startup."""
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown."""
    pass
