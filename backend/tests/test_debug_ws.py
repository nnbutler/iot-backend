"""Tests for the WebSocket MQTT debug endpoint."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.routes.debug import broadcast, _clients
from app.utils.security import create_access_token


def _valid_token():
    return create_access_token("support")


# ── broadcast() ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_broadcast_no_clients_is_noop():
    # Should return early without error when no clients connected
    _clients.clear()
    await broadcast("devices/test/heartbeat", '{"online": true}')  # no exception


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_clients():
    _clients.clear()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    _clients.add(ws1)
    _clients.add(ws2)
    try:
        await broadcast("test/topic", '{"key": "value"}')
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
        msg = ws1.send_json.call_args[0][0]
        assert msg["topic"] == "test/topic"
        assert msg["payload"] == '{"key": "value"}'
        assert "timestamp" in msg
    finally:
        _clients.clear()


@pytest.mark.asyncio
async def test_broadcast_removes_dead_clients():
    _clients.clear()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = Exception("connection closed")
    _clients.add(dead_ws)
    try:
        await broadcast("topic", "payload")
        assert dead_ws not in _clients
    finally:
        _clients.clear()


# ── WebSocket endpoint ────────────────────────────────────────────────────────

def test_websocket_rejects_invalid_token(client):
    # Server closes before accepting — __enter__ itself raises
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/mqtt-debug?token=bad.token.here"):
            pass


def test_websocket_accepts_valid_token(client):
    token = _valid_token()
    with client.websocket_connect(f"/api/ws/mqtt-debug?token={token}") as ws:
        # Connection accepted — client is in _clients set
        assert len(_clients) >= 1
    # Cleanup happens asynchronously; just verify connection was accepted above
