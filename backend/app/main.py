import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI

from app.config import settings
from app.database import SessionLocal
from app.models.device import Device
from app.routes.auth import router as auth_router
from app.routes.commands import router as commands_router
from app.routes.debug import router as debug_router
from app.routes.devices import router as devices_router
from app.routes.errors import router as errors_router
from app.routes.health import router as health_router
from app.routes.logs import router as logs_router
from app.routes.metrics import router as metrics_router
from app.services.influxdb_metrics import metrics_db
from app.services.mqtt import mqtt_manager

HEARTBEAT_TIMEOUT_SECONDS = 30

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
app.include_router(logs_router)
app.include_router(metrics_router)
app.include_router(debug_router)


async def _offline_watchdog():
    """Mark devices offline if they haven't sent a heartbeat within the timeout."""
    while True:
        await asyncio.sleep(10)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
        db = SessionLocal()
        try:
            stale = (
                db.query(Device)
                .filter(Device.online == True, Device.last_seen < cutoff)
                .all()
            )
            for device in stale:
                device.online = False
                device.online_since = None
            if stale:
                db.commit()
        finally:
            db.close()


@app.on_event("startup")
async def startup_event():
    """Connect to MQTT broker and InfluxDB on startup."""
    print("=== APP STARTUP EVENT ===", flush=True)
    mqtt_manager.set_event_loop(asyncio.get_running_loop())
    mqtt_manager.connect()
    print("MQTT connected, now connecting to InfluxDB...", flush=True)
    metrics_db.connect()
    asyncio.create_task(_offline_watchdog())
    print("=== STARTUP COMPLETE ===", flush=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from MQTT broker and InfluxDB on shutdown."""
    mqtt_manager.disconnect()
    metrics_db.disconnect()
