"""WebSocket endpoint for live MQTT message debugging."""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.utils.security import decode_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ws", tags=["debug"])

# All currently connected debug WebSocket clients
_clients: set[WebSocket] = set()


async def broadcast(topic: str, payload: str) -> None:
    """Send an MQTT message to all connected debug clients."""
    if not _clients:
        return
    msg = {
        "topic": topic,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    dead = set()
    for ws in list(_clients):
        try:
            await ws.send_json(msg)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@router.websocket("/mqtt-debug")
async def mqtt_debug(websocket: WebSocket, token: str = Query(...)):
    """Stream live MQTT messages to authenticated dashboard clients."""
    try:
        decode_access_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    _clients.add(websocket)
    logger.info(f"Debug WebSocket connected ({len(_clients)} total)")
    try:
        # Keep the connection alive; client sends nothing
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
        logger.info(f"Debug WebSocket disconnected ({len(_clients)} total)")
