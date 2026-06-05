# Device Logs Architecture

This document describes how logs flow from devices to the database and then to the user interface.

## Overview

```
┌──────────────┐
│   Device     │
└──────┬───────┘
       │ MQTT publish
       │ Topic: devices/{device_id}/logs
       │ Payload: {"level": "INFO", "message": "..."}
       │
       ▼
┌──────────────────────────────────┐
│  MQTT Broker (Mosquitto)         │
│  - Receives from devices         │
│  - Forwards to backend           │
└──────┬───────────────────────────┘
       │ MQTT subscribe
       │ Topic: devices/+/logs
       │
       ▼
┌──────────────────────────────────┐
│  Backend Service (FastAPI)       │
│  - MQTT handler processes logs   │
│  - Validates device exists       │
│  - Stores in PostgreSQL          │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│  PostgreSQL Database             │
│  - device_logs table             │
│  - Indexed by device_id, level   │
│  - Created with auto-incrementing id
└──────┬───────────────────────────┘
       │ REST API query
       │ GET /api/devices/{device_id}/logs?level=ERROR&limit=50&before_id={cursor}
       │
       ▼
┌──────────────────────────────────┐
│  Frontend (React)                │
│  - DeviceLogs component          │
│  - Filter by severity            │
│  - Cursor-based pagination       │
│  - Display in table              │
└──────────────────────────────────┘
```

## Device → MQTT: Publishing Logs

**What the device sends:**

```json
{
  "level": "INFO",
  "message": "Cycle complete"
}
```

**MQTT Topic:** `devices/{device_id}/logs`

**Severity Levels:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Example flow in `device_mocks/mock_device.py`:**

```python
# Device publishes a log message
mqtt_client.publish(
    f"devices/{device_id}/logs",
    json.dumps({"level": "ERROR", "message": "Sensor disconnected"})
)
```

## MQTT → Backend: Receiving and Processing

**File:** `backend/app/services/mqtt.py`

1. **Subscription**
   - Backend subscribes to `devices/+/logs` during startup
   - `+` is a wildcard matching any device_id

2. **Message Handler** (`_handle_logs` method)
   - Validates device exists in database
   - Extracts `level` and `message` from JSON payload
   - Creates `DeviceLog` record with:
     - `device_id`: from MQTT topic
     - `level`: from payload (defaults to "INFO")
     - `message`: from payload
     - `timestamp`: auto-set to current time
   - Commits to PostgreSQL

3. **Error Handling**
   - Invalid JSON: logs warning, skips
   - Unknown device: logs warning, skips
   - Database error: logs error, skips (doesn't crash backend)

## Database: Storage

**Table:** `device_logs`

```sql
CREATE TABLE device_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR NOT NULL,
    level VARCHAR NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(device_id),
    INDEX (device_id, id DESC),
    INDEX (device_id, level, id DESC)
);
```

**Indices:**
- `(device_id, id DESC)` — speeds up queries filtered by device, ordered newest-first
- `(device_id, level, id DESC)` — speeds up level-filtered queries

**Ordering:** Logs are stored with auto-incrementing `id`, so newer logs have higher IDs. The REST API always orders by `id DESC` (newest first).

## Backend → Frontend: REST API

**Endpoint:** `GET /api/devices/{device_id}/logs`

**File:** `backend/app/routes/logs.py`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | null | Filter by severity: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `limit` | int | 50 | Number of logs to return (max 200) |
| `before_id` | int | null | Cursor-based pagination: return logs with id < before_id |

**Response:**

```json
{
  "device_id": "my-device-001",
  "logs": [
    {
      "id": 42,
      "level": "ERROR",
      "message": "Sensor disconnected",
      "timestamp": "2026-06-05T14:30:00.000000"
    },
    {
      "id": 41,
      "level": "INFO",
      "message": "Cycle complete",
      "timestamp": "2026-06-05T14:25:00.000000"
    }
  ],
  "has_more": true,
  "next_before_id": 41
}
```

**Pagination:**
- Always returns logs ordered newest-first
- `has_more: true` if exactly `limit` logs returned (more may exist)
- `next_before_id`: use this value as the `before_id` parameter for the next page
- To fetch all logs across pages, loop: request, check `has_more`, fetch with `before_id`, repeat

## Frontend: Display

**Component:** `frontend/src/components/DeviceLogs.jsx`

**Features:**

1. **Severity Filtering**
   - Button row: `ALL | ERROR | WARNING | INFO | DEBUG | CRITICAL`
   - Clicking a level re-fetches logs for that severity
   - `ALL` shows logs of any severity

2. **Cursor-Based Pagination**
   - Displays logs in paginated chunks (default 50 per page)
   - "Load more" button visible when `has_more: true`
   - Clicking appends next page to the table

3. **Table Display**
   - Columns: Timestamp | Level Badge | Message
   - Level badges color-coded by severity
   - Timestamps formatted in user's local time

## Testing

**Unit Tests:** `backend/tests/test_logs.py`

- 16 tests covering:
  - Basic retrieval (all logs, ordering, response shape)
  - Severity filtering (each level + case-insensitive)
  - Invalid input handling (404 for unknown device, 422 for invalid level)
  - Pagination (limit, has_more flag, cursor behavior)

**Manual Testing:**

```bash
# 1. Start the stack
docker compose up -d

# 2. Start a mock device (generates logs)
cd device_mocks
python3 mock_device.py --device-id test-device

# 3. Open browser
# https://localhost:8443/devices/test-device

# 4. Verify:
# - Logs appear in the "Device Logs" section
# - Filter buttons work (click ERROR, WARNING, etc.)
# - Load more button works when >50 logs exist
```

## Performance Notes

- Logs are indexed for fast filtering by device_id + severity
- Cursor pagination avoids expensive OFFSET queries
- Newest logs are fetched first (users want recent info)
- Single query per page fetch (no N+1 problems)
- Database auto-increments IDs for reliable cursor position

## Future Enhancements

- Export logs to CSV/JSON
- Full-text search on message content
- Log aggregation/rotation (delete logs older than N days)
- Real-time log streaming (WebSocket instead of polling)
- Structured logging (JSON fields instead of flat message string)
