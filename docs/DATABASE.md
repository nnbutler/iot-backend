# Database Schema Documentation

**Database:** PostgreSQL 15  
**Schema:** `public`  
**Last Updated:** June 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Summary](#entity-relationship-summary)
3. [Tables](#tables)
   - [users](#users)
   - [devices](#devices)
   - [error_types](#error_types)
   - [repair_actions](#repair_actions)
   - [repair_outcomes](#repair_outcomes)
   - [device_error_history](#device_error_history)
   - [commands](#commands)
   - [device_logs](#device_logs)
   - [mqtt_credentials](#mqtt_credentials)
4. [Indexes](#indexes)
5. [Seed Data](#seed-data)
6. [Design Decisions](#design-decisions)

---

## Overview

The database serves three purposes:

- **Device registry** — tracks every field device, its current state, and credentials
- **Knowledge base** — stores known error types and ranked repair actions learned over time
- **Audit trail** — records every command sent, error that occurred, repair attempted, and log emitted

---

## Entity Relationship Summary

```
users
  (no FK relations — auth is separate from device ownership)

devices ──────────────────────────────────────────┐
  │                                               │
  ├── commands (device_id → devices.device_id)    │
  ├── mqtt_credentials (device_id → unique)       │
  ├── device_logs (device_id → loose ref)         │
  └── device_error_history (device_id → loose ref)│
                                                  │
error_types ──────────────────────────────────────┘
  │
  ├── repair_actions (error_id → error_types.id)
  ├── repair_outcomes (error_id → error_types.id)
  └── device_error_history (error_id → error_types.id)

repair_actions
  └── repair_outcomes (repair_action_id → repair_actions.id)
```

> Note: `device_id` in `device_logs`, `device_error_history`, and `repair_outcomes` is stored
> as a plain `VARCHAR` rather than a hard foreign key. This allows log/history records to survive
> even if a device record is deleted or re-provisioned.

---

## Tables

---

### `users`

Stores dashboard and support staff accounts. Phase 1 uses hardcoded credentials; this table is the foundation for proper RBAC in Phase 2.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `username` | VARCHAR(100) | NOT NULL | — | Unique login name |
| `password_hash` | VARCHAR(255) | NOT NULL | — | bcrypt hash — never store plaintext |
| `email` | VARCHAR(100) | NULL | — | Optional contact email |
| `role` | VARCHAR(50) | NOT NULL | `'support'` | One of: `support`, `developer`, `admin` |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Record creation time |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Last modification time |

**Roles:**
| Role | Access |
|---|---|
| `support` | Read devices, record repair outcomes, view history |
| `developer` | All of support + send commands, add error types |
| `admin` | Full access including user management |

**Indexes:** `idx_users_username` on `username`

---

### `devices`

The central registry of every field device. One row per physical unit. Updated each time a device checks in.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `device_id` | VARCHAR(100) | NOT NULL | — | Human-readable unique ID, e.g. `plc-001` |
| `api_key` | VARCHAR(255) | NOT NULL | — | SHA256-hashed API key used for device auth |
| `device_type` | VARCHAR(100) | NULL | — | e.g. `plc`, `sensor_hub` |
| `location` | VARCHAR(255) | NULL | — | Physical location, e.g. `"Phoenix, AZ"` |
| `customer_name` | VARCHAR(255) | NULL | — | Customer this device belongs to |
| `online` | BOOLEAN | NOT NULL | `FALSE` | Whether the device is currently reachable |
| `last_seen` | TIMESTAMPTZ | NULL | — | Timestamp of last successful heartbeat |
| `last_error` | VARCHAR(255) | NULL | — | Most recent error code reported |
| `last_error_timestamp` | TIMESTAMPTZ | NULL | — | When the most recent error occurred |
| `state` | VARCHAR(100) | NULL | — | Current device state machine state |
| `firmware_version` | VARCHAR(50) | NULL | — | Running firmware version |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When device was first registered |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Last time this record was modified |

**Notes:**
- `api_key` is hashed before storage — the raw key is only known at provisioning time
- `online` is set to `FALSE` by the backend when a heartbeat is missed (configurable timeout)
- `last_error` stores the `error_code` string, not the `error_types.id` integer, for fast display without a join

**Indexes:** `idx_devices_device_id`, `idx_devices_online`, `idx_devices_customer`

---

### `error_types`

The knowledge base of known failure modes. Each row defines a category of error that a device can report, along with how it should be described to different audiences.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `error_code` | VARCHAR(100) | NOT NULL | — | Machine-readable code, e.g. `sensor_disconnected` |
| `display_name` | VARCHAR(255) | NOT NULL | — | Short human name shown in the dashboard |
| `description` | TEXT | NULL | — | Internal description for support/developers |
| `severity` | VARCHAR(20) | NULL | — | One of: `low`, `medium`, `high`, `critical` |
| `customer_visible_message` | TEXT | NULL | — | Plain-English message safe to show or read to the customer |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Seeded error types:**
| `error_code` | `display_name` | `severity` |
|---|---|---|
| `sensor_disconnected` | Sensor Disconnected | medium |
| `photoeye_misaligned` | Photoeye Not Detecting | high |
| `internet_down` | Internet Connectivity Lost | critical |
| `state_machine_stuck` | Unit In Stuck State | high |
| `unknown_error` | Unknown Error | medium |

**Indexes:** `idx_error_types_code` on `error_code`

---

### `repair_actions`

Ordered steps for resolving a specific error type. Steps are ranked by `success_rate`, which is updated automatically each time a `repair_outcome` is recorded. This is how the system learns over time.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `error_id` | INTEGER | NOT NULL | — | FK → `error_types.id` (CASCADE delete) |
| `step_order` | INTEGER | NOT NULL | — | Display order within the error's steps |
| `action` | TEXT | NOT NULL | — | Short instruction shown to the user |
| `description` | TEXT | NULL | — | Expanded explanation of how to perform the step |
| `estimated_time_minutes` | INTEGER | NULL | — | Approximate time to complete |
| `success_rate` | FLOAT | NOT NULL | `0.5` | Fraction of attempts that resolved the error (0.0–1.0) |
| `occurrences` | INTEGER | NOT NULL | `0` | Total times this action has been attempted |
| `successful_occurrences` | INTEGER | NOT NULL | `0` | Times it worked; used to recalculate `success_rate` |
| `created_by` | VARCHAR(100) | NULL | — | Username who added this action |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |
| `updated_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | — |

**Constraints:** `UNIQUE(error_id, step_order)` — no duplicate step numbers per error

**Success rate calculation:**
```
success_rate = successful_occurrences / occurrences
```
Updated on every `repair_outcome` insert. The API sorts repair actions by `success_rate DESC` so the most effective steps surface to the top.

**Indexes:** `idx_repair_actions_error` on `error_id`

---

### `repair_outcomes`

A log of every repair attempt. Written by support staff after trying a repair action. Drives the learning loop — each new row recalculates `repair_actions.success_rate`.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `device_id` | VARCHAR(100) | NOT NULL | — | Device the repair was performed on (loose ref) |
| `error_id` | INTEGER | NOT NULL | — | FK → `error_types.id` |
| `repair_action_id` | INTEGER | NULL | — | FK → `repair_actions.id` (NULL if ad-hoc action) |
| `worked` | BOOLEAN | NOT NULL | — | Did this action resolve the error? |
| `notes` | TEXT | NULL | — | Free-text notes from the support person |
| `time_spent_minutes` | INTEGER | NULL | — | How long the repair took |
| `attempted_by` | VARCHAR(100) | NULL | — | Username of support person |
| `attempted_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When the attempt was made |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Record creation time |

**Notes:**
- `repair_action_id` can be NULL when support tries something not yet in the knowledge base — the outcome is still recorded, and a developer can later add it as a formal action
- Each insert triggers a recalculation of the linked `repair_action.success_rate`

**Indexes:** `idx_repair_outcomes_device`, `idx_repair_outcomes_error`, `idx_repair_outcomes_attempted_at`

---

### `device_error_history`

A timestamped record of every error event on every device. Tracks when errors start and when they are resolved, giving a full incident timeline per device.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `device_id` | VARCHAR(100) | NOT NULL | — | Device this error occurred on (loose ref) |
| `error_id` | INTEGER | NULL | — | FK → `error_types.id` (NULL if unrecognised error) |
| `error_message` | TEXT | NULL | — | Raw error message from the device |
| `occurred_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When the error was first detected |
| `resolved_at` | TIMESTAMPTZ | NULL | — | When the error was cleared (NULL = still active) |
| `resolution_notes` | TEXT | NULL | — | How it was resolved |
| `resolved_by` | VARCHAR(100) | NULL | — | Username who marked it resolved |

**Notes:**
- An open incident has `resolved_at = NULL`
- `error_id` can be NULL when the device reports an error code not yet in `error_types` — these are escalation candidates
- This table is the source for Joe (field tech) and Leroy (sales) to understand a device's recent history

**Indexes:** `idx_device_error_history_device`, `idx_device_error_history_occurred`

---

### `commands`

A log of every command sent to a field device via MQTT. Tracks the full lifecycle from sent → executing → success/failed.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `device_id` | VARCHAR(100) | NOT NULL | — | FK → `devices.device_id` (CASCADE delete) |
| `command_type` | VARCHAR(100) | NOT NULL | — | One of: `restart_plc`, `reset_state_machine`, `reboot_device`, `clear_error_log` |
| `status` | VARCHAR(50) | NOT NULL | `'sent'` | One of: `sent`, `executing`, `success`, `failed` |
| `result` | TEXT | NULL | — | Response payload from the device |
| `error_message` | TEXT | NULL | — | Failure reason if status is `failed` |
| `sent_by` | VARCHAR(100) | NULL | — | Username who triggered the command |
| `sent_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When the command was published to MQTT |
| `executed_at` | TIMESTAMPTZ | NULL | — | When the device acknowledged execution |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | Record creation time |

**Command lifecycle:**
```
sent → (device picks up from MQTT) → executing → success
                                              └──→ failed
```

**Supported command types:**
| `command_type` | Effect |
|---|---|
| `restart_plc` | Restarts the PLC process on the device |
| `reset_state_machine` | Clears a stuck state machine |
| `reboot_device` | Full OS reboot |
| `clear_error_log` | Clears the device-side error log |

**Indexes:** `idx_commands_device`, `idx_commands_status`, `idx_commands_created`

---

### `device_logs`

A stream of log messages emitted by devices — errors, warnings, and info events. Used for debugging and incident investigation.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `device_id` | VARCHAR(100) | NOT NULL | — | Device that emitted this log (loose ref) |
| `level` | VARCHAR(20) | NULL | — | One of: `ERROR`, `WARNING`, `INFO` |
| `message` | TEXT | NULL | — | Log message text |
| `timestamp` | TIMESTAMPTZ | NOT NULL | `NOW()` | When the event occurred on the device |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When this record was written to the DB |

**Notes:**
- `timestamp` reflects device-side time; `created_at` reflects backend ingestion time — they may differ if the device was offline and batching logs
- High-volume table; consider a retention policy (e.g. purge logs older than 90 days) before scaling to 200+ devices

**Indexes:** `idx_device_logs_device`, `idx_device_logs_level`, `idx_device_logs_timestamp`

---

### `mqtt_credentials`

Stores per-device MQTT credentials generated at device login. Rotated on each authentication. One row per device.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | SERIAL | NOT NULL | auto | Primary key |
| `device_id` | VARCHAR(100) | NOT NULL | — | Unique — one credential set per device |
| `username` | VARCHAR(100) | NOT NULL | — | MQTT username (typically same as `device_id`) |
| `password_hash` | VARCHAR(255) | NOT NULL | — | Hashed MQTT password |
| `expires_at` | TIMESTAMPTZ | NULL | — | When this credential expires (NULL = no expiry) |
| `created_at` | TIMESTAMPTZ | NOT NULL | `NOW()` | When credentials were last rotated |

**Notes:**
- Credentials are generated at `POST /api/auth/device-login` and returned in plaintext once — only the hash is stored
- `UNIQUE` on `device_id` — a new login upserts this row, rotating the password
- `expires_at` aligns with the JWT expiry so both tokens go stale together

**Indexes:** `idx_mqtt_credentials_device` on `device_id`

---

## Indexes

| Index | Table | Column(s) | Reason |
|---|---|---|---|
| `idx_users_username` | users | username | Login lookup |
| `idx_devices_device_id` | devices | device_id | Every device query uses this |
| `idx_devices_online` | devices | online | Dashboard filter (online/offline) |
| `idx_devices_customer` | devices | customer_name | Filter devices by customer |
| `idx_error_types_code` | error_types | error_code | Lookup by code string from device reports |
| `idx_repair_actions_error` | repair_actions | error_id | Fetch all actions for an error |
| `idx_repair_outcomes_device` | repair_outcomes | device_id | Device repair history |
| `idx_repair_outcomes_error` | repair_outcomes | error_id | Outcomes per error type |
| `idx_repair_outcomes_attempted_at` | repair_outcomes | attempted_at DESC | Recent outcomes first |
| `idx_device_error_history_device` | device_error_history | device_id | Incident timeline per device |
| `idx_device_error_history_occurred` | device_error_history | occurred_at DESC | Recent incidents first |
| `idx_commands_device` | commands | device_id | Command history per device |
| `idx_commands_status` | commands | status | Filter pending/failed commands |
| `idx_commands_created` | commands | created_at DESC | Recent commands first |
| `idx_device_logs_device` | device_logs | device_id | Logs per device |
| `idx_device_logs_level` | device_logs | level | Filter by severity |
| `idx_device_logs_timestamp` | device_logs | timestamp DESC | Chronological log view |
| `idx_mqtt_credentials_device` | mqtt_credentials | device_id | Credential lookup at auth |

---

## Seed Data

The following data is inserted on first run via `scripts/init-db.sql`.

**Error types (5):** `sensor_disconnected`, `photoeye_misaligned`, `internet_down`, `state_machine_stuck`, `unknown_error`

**Repair actions (10 total):**
| Error | Steps |
|---|---|
| `sensor_disconnected` | Check cable → Power cycle sensor → Power cycle unit |
| `photoeye_misaligned` | Check reflector alignment → Clean lens |
| `internet_down` | Check network cable → Power cycle router → Check router with customer |
| `state_machine_stuck` | Power cycle unit → Check sensor readings |
| `unknown_error` | *(none seeded — requires developer investigation)* |

---

## Design Decisions

**`device_id` as VARCHAR foreign key, not integer ID**
Commands, logs, and history reference `device_id` (the string `"plc-001"`) rather than the integer `devices.id`. This makes logs human-readable without a join and allows log records to survive device re-provisioning. The tradeoff is that renaming a device requires updating multiple tables.

**Loose references for logs and history**
`device_logs`, `device_error_history`, and `repair_outcomes` use `device_id VARCHAR` without a hard `REFERENCES` constraint. This is intentional: these are append-only audit records. A device being deleted should not cascade-delete its history.

**`success_rate` stored, not computed**
`repair_actions.success_rate` is a stored float rather than a computed column. This avoids an expensive aggregation on every API read. It is updated on each `repair_outcomes` insert via application logic.

**TIMESTAMPTZ everywhere**
All timestamps use `TIMESTAMPTZ` (timezone-aware) rather than `TIMESTAMP`. Field devices may be in different time zones, and the backend runs in UTC. This prevents ambiguity during incident investigations.
