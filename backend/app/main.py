from fastapi import FastAPI

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.commands import router as commands_router
from app.routes.devices import router as devices_router
from app.routes.errors import router as errors_router
from app.routes.health import router as health_router

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(errors_router)
app.include_router(commands_router)


@app.on_event("startup")
async def startup_event():
    """Run on startup."""
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown."""
    pass
