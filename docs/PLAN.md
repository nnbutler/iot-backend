# Phase 1 Implementation Plan: Device Manager Backend

**Last Updated:** June 2026  
**Status:** Ready for Development  
**Duration:** 5 weeks (8 weeks dev @ 50% + 8 weeks trial + 4 weeks kiosk)  
**Primary Developer Bandwidth:** 2 developers @ 50%

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Architecture Overview](#architecture-overview)
4. [Technology Stack](#technology-stack)
5. [Database Schema](#database-schema)
6. [API Specification](#api-specification)
7. [File Structure](#file-structure)
8. [Week-by-Week Breakdown](#week-by-week-breakdown)
9. [Testing Strategy](#testing-strategy)
10. [Deployment](#deployment)
11. [Common Pitfalls](#common-pitfalls)
12. [Key Decisions & Rationale](#key-decisions--rationale)

---

## Executive Summary

Build a centralized management system for Linux-based field devices (PLC systems and kiosks) deployed at customer sites. The system enables non-technical support staff to diagnose and resolve issues without developer intervention. Phase 1 focuses on:

- Real-time device monitoring and command execution
- Error/repair action knowledge base (database-driven)
- Support team empowerment through intuitive UI
- Scalability from 20 to 220 devices
- Production-ready on Day 1 with Nginx + FastAPI + PostgreSQL

---

## Problem Statement

The recycling company has 20+ Linux-based field devices deployed at customer sites. When customers experience downtime, they lose revenue. Currently:

1. Customer calls Sales
2. Sales has no tools to investigate
3. Sales calls a Developer
4. Developer VPNs in and manually fixes it
5. No knowledge is captured or reused

**This is inefficient and unsustainable.**

Common issues:
- Bad sensor values (reflector fallen off, sensor disconnected/faulty)
- Internet connectivity down
- Device stuck in strange state machine state
- Customers power cycle before root cause found

**Goal:** Empower all team members (non-developers) to diagnose and resolve customer issues through a knowledge-based system and real-time monitoring dashboard.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│         Public Internet / Field Devices               │
│  (Kiosks, PLC Systems, all Linux-based)              │
└──────────┬───────────────────────────────────────────┘
           │
           │ HTTPS + Certificate Pinning
           │ API Key Authentication
           │
┌──────────▼───────────────────────────────────────────┐
│              Nginx (Port 443)                         │
│  ✓ Rate limiting: 10/min (auth), 100/min (api)      │
│  ✓ TLS/HTTPS with Let's Encrypt                     │
│  ✓ Security headers (HSTS, CSP, etc.)               │
│  ✓ X-Forwarded-For handling                         │
│  ✓ Gzip compression                                 │
└──────────┬───────────────────────────────────────────┘
           │
           │ HTTP/1.1 to FastAPI:8000
           │
┌──────────▼───────────────────────────────────────────┐
│          FastAPI Application (Port 8000)             │
│  ✓ Authentication (JWT, API Keys)                   │
│  ✓ Device commands & status                         │
│  ✓ Error/repair action CRUD                         │
│  ✓ Metrics collection                               │
│  ✓ Health checks                                    │
└──────────┬───────────────────────────────────────────┘
           │
    ┌──────┴──────┬──────────┬──────────┐
    │             │          │          │
┌───▼──┐  ┌──────▼──┐  ┌───▼──────┐  ┌─▼──────────┐
│  DB  │  │InfluxDB │  │Mosquitto │  │  Telegraf  │
│  PG  │  │ metrics │  │  MQTT    │  │MQTT→Influx │
│      │  │         │  │ Port 8883│  │            │
└──────┘  └─────────┘  └──────────┘  └────────────┘
```

---

## Technology Stack

| Layer | Technology | Justification |
|-------|-----------|----------------|
| **Reverse Proxy** | Nginx (Alpine) | Rate limiting, TLS, security at infrastructure level |
| **Web Framework** | FastAPI 0.104+ | Async, fast, great for IoT, type hints |
| **Language** | Python 3.11+ | Single language across stack, easy for non-devs to understand |
| **Database** | PostgreSQL 15 | Structured data, ACID, JSONB for flexibility |
| **Metrics** | InfluxDB 2.x | Time-series data, built for IoT metrics |
| **Message Broker** | Mosquitto 2.x | MQTT standard, lightweight, TLS support |
| **Metrics Bridge** | Telegraf | MQTT subscriber → InfluxDB writer |
| **Orchestration** | Docker Compose | Single file, easy deployment, development-to-prod parity |
| **Testing** | pytest 7.4+ | Industry standard, async support |
| **CI/CD** | Jenkins | Specified by client |
| **Deployment** | DigitalOcean droplet | $6-12/month, manual docker-compose deploy |

---

## Database Schema

### Complete SQL Schema

```sql
-- =============================================================================
-- USER MANAGEMENT (Phase 1: Hardcoded, Phase 2: Proper RBAC)
-- =============================================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(50) DEFAULT 'support',  -- support, developer, admin
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);

-- =============================================================================
-- DEVICE MANAGEMENT
-- =============================================================================

CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) UNIQUE NOT NULL,  -- "kiosk-001", "plc-042", etc.
    api_key VARCHAR(255) UNIQUE NOT NULL,    -- SHA256 hashed
    device_type VARCHAR(100),                 -- "kiosk", "plc", "sensor_hub", etc.
    location VARCHAR(255),
    customer_name VARCHAR(255),
    online BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP,
    last_error VARCHAR(255),
    last_error_timestamp TIMESTAMP,
    state VARCHAR(100),                       -- Current device state (if applicable)
    firmware_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_devices_device_id ON devices(device_id);
CREATE INDEX idx_devices_online ON devices(online);
CREATE INDEX idx_devices_customer ON devices(customer_name);

-- =============================================================================
-- ERROR TYPES & REPAIR ACTIONS (Knowledge Base)
-- =============================================================================

CREATE TABLE error_types (
    id SERIAL PRIMARY KEY,
    error_code VARCHAR(100) UNIQUE NOT NULL,    -- "sensor_disconnected", etc.
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20),                       -- low, medium, high, critical
    customer_visible_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_error_types_code ON error_types(error_code);

CREATE TABLE repair_actions (
    id SERIAL PRIMARY KEY,
    error_id INTEGER NOT NULL REFERENCES error_types(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    action TEXT NOT NULL,
    description TEXT,
    estimated_time_minutes INTEGER,
    success_rate FLOAT DEFAULT 0.5,            -- Calculated from outcomes
    occurrences INTEGER DEFAULT 0,             -- How many times tried
    successful_occurrences INTEGER DEFAULT 0,  -- How many times worked
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(error_id, step_order)
);

CREATE INDEX idx_repair_actions_error ON repair_actions(error_id);

CREATE TABLE repair_outcomes (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    error_id INTEGER NOT NULL REFERENCES error_types(id),
    repair_action_id INTEGER REFERENCES repair_actions(id),
    worked BOOLEAN NOT NULL,
    notes TEXT,
    time_spent_minutes INTEGER,
    attempted_by VARCHAR(100),                 -- Support person name
    attempted_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_repair_outcomes_device ON repair_outcomes(device_id);
CREATE INDEX idx_repair_outcomes_error ON repair_outcomes(error_id);
CREATE INDEX idx_repair_outcomes_attempted_at ON repair_outcomes(attempted_at DESC);

CREATE TABLE device_error_history (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    error_id INTEGER REFERENCES error_types(id),
    error_message TEXT,
    occurred_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    resolved_by VARCHAR(100)
);

CREATE INDEX idx_device_error_history_device ON device_error_history(device_id);
CREATE INDEX idx_device_error_history_occurred ON device_error_history(occurred_at DESC);

-- =============================================================================
-- COMMANDS
-- =============================================================================

CREATE TABLE commands (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    command_type VARCHAR(100) NOT NULL,        -- "restart", "reset_state_machine", etc.
    status VARCHAR(50) DEFAULT 'sent',         -- sent, executing, success, failed
    result TEXT,
    error_message TEXT,
    sent_by VARCHAR(100),
    sent_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_commands_device ON commands(device_id);
CREATE INDEX idx_commands_status ON commands(status);
CREATE INDEX idx_commands_created ON commands(created_at DESC);

-- =============================================================================
-- DEVICE LOGS (Errors, Warnings, Info)
-- =============================================================================

CREATE TABLE device_logs (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL,
    level VARCHAR(20),                        -- ERROR, WARNING, INFO
    message TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_device_logs_device ON device_logs(device_id);
CREATE INDEX idx_device_logs_level ON device_logs(level);
CREATE INDEX idx_device_logs_timestamp ON device_logs(timestamp DESC);

-- =============================================================================
-- MQTT CREDENTIALS (Generated at login, expires with JWT)
-- =============================================================================

CREATE TABLE mqtt_credentials (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mqtt_credentials_device ON mqtt_credentials(device_id);
```

### Initialization Script

```sql
-- scripts/init-db.sql

-- Create all tables
-- (See above schema)

-- Seed error types
INSERT INTO error_types (error_code, display_name, severity, customer_visible_message, description)
VALUES
    ('sensor_disconnected', 'Sensor Disconnected', 'medium', 'Sensor not responding', 
     'A connected sensor is not reporting data to the PLC'),
    ('photoeye_misaligned', 'Photoeye Not Detecting', 'high', 'Object detection failed', 
     'Photoeye reflector fallen off or misaligned'),
    ('internet_down', 'Internet Connectivity Lost', 'critical', 'Device not connected', 
     'Device cannot reach backend (no internet or network cable issue)'),
    ('state_machine_stuck', 'Unit In Stuck State', 'high', 'Device not responding', 
     'Device logic stuck in state machine, needs reset'),
    ('unknown_error', 'Unknown Error', 'medium', 'Unexpected error occurred', 
     'Generic error, needs investigation');

-- Seed repair actions for sensor_disconnected
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (1, 1, 'Check physical cable connection at sensor and PLC', 
     'Verify cable is plugged in at both ends and connector is seated properly', 5),
    (1, 2, 'Power cycle the sensor', 
     'Turn off sensor (power switch or unplug), wait 10 seconds, turn back on', 2),
    (1, 3, 'Power cycle entire unit', 
     'Perform full power cycle of the entire equipment', 3);

-- Seed repair actions for photoeye_misaligned
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (2, 1, 'Check reflector is aligned and clean', 
     'Visually inspect reflector is in correct position and not dirty', 5),
    (2, 2, 'Clean photoeye lens', 
     'Use soft cloth to gently clean the photoeye lens (front element)', 2);

-- Seed repair actions for internet_down
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (3, 1, 'Check network cable at unit', 
     'Verify Ethernet cable is connected to device network port', 1),
    (3, 2, 'Power cycle router/modem', 
     'Unplug network equipment, wait 30 seconds, plug back in', 3),
    (3, 3, 'Check router status with customer', 
     'Ask customer to describe router lights (all solid green = good)', 2);

-- Seed repair actions for state_machine_stuck
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (4, 1, 'Power cycle unit', 
     'Turn off device for 30 seconds, turn back on', 3),
    (4, 2, 'Check sensor readings', 
     'Verify sensors are giving stable readings (not flickering)', 5);
```

---

## API Specification

### Authentication Endpoint

```
POST /api/auth/kiosk-login

Request:
{
  "device_id": "kiosk-001",
  "api_key": "sk_abc123..."
}

Response (200):
{
  "jwt_token": "eyJhbGc...",
  "mqtt_username": "kiosk-001",
  "mqtt_password": "mqtt_secure_password_here",
  "mqtt_host": "mqtt.company.com",
  "mqtt_port": 8883,
  "expires_in": 3600
}

Error (401):
{
  "detail": "Invalid API key"
}

Rate Limit: 10 requests/minute per IP (Nginx)
Security: Certificate pinning required on device
```

### Device Status Endpoints

```
GET /api/devices/{device_id}/status

Request Headers:
Authorization: Bearer {jwt_token}

Response (200):
{
  "device_id": "kiosk-001",
  "online": true,
  "last_seen": "2024-01-15T14:35:22Z",
  "state": "idle",
  "metrics": {
    "throughput": 240,
    "cycle_time": 45,
    "error_count": 0
  },
  "last_error": {
    "code": "sensor_disconnected",
    "message": "Sensor X not responding",
    "occurred_at": "2024-01-15T14:00:00Z"
  },
  "troubleshooting": {
    "display_name": "Sensor Disconnected",
    "success_rate": 0.88,
    "repair_actions": [
      {
        "id": 1,
        "step": 1,
        "action": "Check physical cable connection...",
        "estimated_time": 5,
        "success_rate": 0.88
      }
    ]
  }
}

Rate Limit: 100 requests/minute per IP (Nginx)
```

```
GET /api/devices/{device_id}/metrics?hours=24

Response (200):
{
  "device_id": "kiosk-001",
  "timerange": "last 24 hours",
  "metrics": [
    {
      "timestamp": "2024-01-15T14:00:00Z",
      "throughput": 240,
      "cycle_time": 45,
      "error_rate": 0.0
    }
  ]
}

Note: Data from InfluxDB via Telegraf
Rate Limit: 600 requests/minute per IP (Nginx)
```

### Command Endpoints

```
POST /api/devices/{device_id}/commands

Request:
{
  "command_type": "restart_plc"
}

Response (200):
{
  "command_id": 12345,
  "status": "sent",
  "message": "Command sent to device"
}

Supported Commands:
- restart_plc
- reset_state_machine
- reboot_device
- clear_error_log

Rate Limit: 50 requests/minute per IP (Nginx)
```

```
GET /api/devices/{device_id}/commands

Response (200):
{
  "device_id": "kiosk-001",
  "commands": [
    {
      "id": 12345,
      "type": "restart_plc",
      "status": "success",
      "result": "PLC restarted successfully",
      "sent_by": "Sarah",
      "sent_at": "2024-01-15T14:35:00Z",
      "executed_at": "2024-01-15T14:35:05Z"
    }
  ]
}

Rate Limit: 100 requests/minute per IP (Nginx)
```

### Repair Action Management

```
GET /api/errors/{error_code}/repair-actions

Response (200):
{
  "error": {
    "code": "sensor_disconnected",
    "name": "Sensor Disconnected",
    "severity": "medium"
  },
  "repair_actions": [
    {
      "id": 1,
      "step": 1,
      "action": "Check physical cable connection at sensor and PLC",
      "estimated_time": 5,
      "success_rate": 0.88,
      "tried_count": 23,
      "successful_count": 20
    }
  ]
}
```

```
POST /api/errors/{error_code}/repair-actions

Request (Support User Only):
{
  "action": "Try power cycling the sensor",
  "description": "Power off 10 seconds then on",
  "estimated_time_minutes": 2
}

Response (200):
{
  "id": 4,
  "message": "Repair action added"
}

Auth: Support user (hardcoded list in Phase 1)
```

```
POST /api/devices/{device_id}/repair-outcome

Request (Support User Only):
{
  "error_code": "sensor_disconnected",
  "repair_action_id": 1,
  "worked": true,
  "notes": "Cable was loose at sensor end",
  "time_spent_minutes": 3
}

Response (200):
{
  "outcome_id": 567,
  "message": "Recorded: action 1 worked",
  "updated_success_rate": 0.89
}

Side Effect: Updates repair_action.success_rate calculation
```

### Dashboard Endpoints

```
GET /api/devices

Request Headers:
Authorization: Bearer {dashboard_token}

Response (200):
{
  "devices": [
    {
      "device_id": "kiosk-001",
      "customer": "Acme Recycling",
      "location": "Phoenix, AZ",
      "online": true,
      "last_seen": "2024-01-15T14:35:22Z",
      "last_error": "sensor_disconnected",
      "uptime_percent": 99.2
    }
  ]
}

Auth: Dashboard user (hardcoded credentials in Phase 1)
Rate Limit: 100 requests/minute per IP (Nginx)
```

```
GET /api/devices/{device_id}/logs?level=ERROR&limit=50

Response (200):
{
  "device_id": "kiosk-001",
  "logs": [
    {
      "timestamp": "2024-01-15T14:00:12Z",
      "level": "ERROR",
      "message": "Sensor X timeout after 5 attempts"
    }
  ]
}
```

### Health Check

```
GET /health

Response (200):
{
  "status": "ok",
  "database": "connected",
  "mqtt": "connected",
  "version": "1.0.0"
}

Rate Limit: None (Nginx access_log off)
```

---

## File Structure

```
device-manager-backend/
├── README.md                           # Project overview
├── PLAN.md                            # This file
├── .gitignore                         # Git ignore rules
├── .env.example                       # Environment template
├── requirements.txt                   # Python dependencies
│
├── docker-compose.yml                 # All services
├── Dockerfile                         # FastAPI container
│
├── nginx/
│   ├── nginx.conf                     # Nginx reverse proxy config
│   ├── letsencrypt/                   # Let's Encrypt certs (gitignore)
│   └── certs/                         # CA certs
│
├── scripts/
│   ├── setup-droplet.sh              # DigitalOcean setup
│   ├── setup-certificates.sh         # Let's Encrypt automation
│   ├── init-db.sql                   # Database initialization
│   ├── seed_db.py                    # Seed test data
│   └── reset_db.sh                   # Development reset
│
├── telegraf.conf                      # Telegraf MQTT→InfluxDB config
│
├── mosquitto/
│   ├── mosquitto.conf                # MQTT broker config
│   ├── passwd                         # MQTT username/password file
│   └── certs/                         # TLS certificates
│
├── api/
│   ├── main.py                        # FastAPI app entry point
│   ├── requirements.txt               # Python dependencies
│   ├── .env.development              # Dev environment variables
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── device.py                 # Device model
│   │   ├── error.py                  # Error & repair action models
│   │   └── command.py                # Command model
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py                   # POST /api/auth/kiosk-login
│   │   ├── devices.py                # GET /api/devices/*
│   │   ├── commands.py               # GET/POST /api/devices/*/commands
│   │   ├── errors.py                 # GET /api/errors/*
│   │   ├── repairs.py                # POST /api/devices/*/repair-outcome
│   │   └── health.py                 # GET /health
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py           # JWT, API key validation
│   │   ├── device_service.py         # Device queries
│   │   ├── command_service.py        # Command execution
│   │   ├── error_service.py          # Error/repair logic
│   │   └── mqtt_service.py           # MQTT publishing
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py             # PostgreSQL connection
│   │   ├── models.py                 # SQLAlchemy models
│   │   └── migrations.py             # Database migration helpers
│   │
│   └── utils/
│       ├── __init__.py
│       ├── security.py               # Hashing, JWT
│       ├── logger.py                 # Logging setup
│       └── validators.py             # Input validation
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_auth.py                  # Auth endpoint tests
│   ├── test_devices.py               # Device endpoint tests
│   ├── test_commands.py              # Command endpoint tests
│   ├── test_errors.py                # Error/repair tests
│   └── test_mqtt.py                  # MQTT integration tests
│
└── .github/
    └── workflows/
        └── test.yml                   # GitHub Actions CI/CD
```

---

## Week-by-Week Breakdown

### Week 1: Foundation & Database

**Goals:**
- Docker Compose running locally
- PostgreSQL with schema
- Nginx reverse proxy working
- Basic FastAPI structure

**Tasks:**

1. **Project Setup**
   - [ ] Create git repo
   - [ ] Create docker-compose.yml with all 6 services
   - [ ] Create Dockerfile for FastAPI
   - [ ] Test `docker-compose up -d` works
   - [ ] Verify all containers are healthy

2. **Database**
   - [ ] Create PostgreSQL container in docker-compose
   - [ ] Write complete schema (see Database Schema section)
   - [ ] Create init-db.sql with seed data
   - [ ] Test: `docker-compose exec postgres psql -d device_manager -c "\dt"`
   - [ ] Create database models.py (SQLAlchemy)

3. **Nginx**
   - [ ] Write nginx.conf (see provided config)
   - [ ] Test HTTP → HTTPS redirect
   - [ ] Test rate limiting zones defined
   - [ ] Test backend proxy working (localhost for now)

4. **FastAPI Structure**
   - [ ] Create main.py with basic app
   - [ ] Create models/ package structure
   - [ ] Create routes/ package (auth, devices, health)
   - [ ] Create services/ package structure
   - [ ] Create tests/ package with conftest.py

5. **Testing**
   - [ ] Write conftest.py with database fixtures
   - [ ] Create first test: `test_health.py`
   - [ ] Set up pytest with coverage reporting
   - [ ] Target: 70% coverage on new code

**Deliverable:** `docker-compose up -d` brings up working database + Nginx, FastAPI responds to /health

---

### Week 2: Authentication & Core API

**Goals:**
- JWT token generation/validation
- API key validation
- MQTT credential generation
- Core device endpoints

**Tasks:**

1. **Authentication Service**
   - [ ] Implement `auth_service.py`:
     - SHA256 API key hashing
     - JWT generation (HS256, 1-hour expiry)
     - JWT validation
     - MQTT password generation
   - [ ] Add to SecurityUtils: password hashing, random string generation

2. **Auth Endpoint**
   - [ ] Implement `POST /api/auth/kiosk-login`
   - [ ] Input validation (device_id, api_key)
   - [ ] Database lookup: match device_id + hashed api_key
   - [ ] Return: JWT + MQTT credentials
   - [ ] Error handling: 401 invalid, 404 device not found
   - [ ] Write tests: valid key, invalid key, missing device

3. **Device Endpoints**
   - [ ] Implement `GET /api/devices/{device_id}/status`
     - Requires JWT token
     - Returns device state + last error
     - Includes troubleshooting suggestions (from error_types/repair_actions)
   - [ ] Implement `GET /api/devices/{device_id}/metrics`
     - Requires JWT token
     - Query InfluxDB (or dummy data for now)
     - Return last 24 hours
   - [ ] Implement `GET /api/devices` (dashboard)
     - Requires hardcoded dashboard auth
     - Returns all devices

4. **MQTT Integration**
   - [ ] Set up Mosquitto in docker-compose
   - [ ] Create mqtt_service.py
   - [ ] Write tests for MQTT credential storage

5. **Testing**
   - [ ] Auth endpoint: 35+ test cases
   - [ ] Device endpoints: 20+ test cases
   - [ ] JWT validation: 15+ test cases
   - [ ] Target: 75% backend coverage

**Deliverable:** `curl -X POST http://localhost/api/auth/kiosk-login -d '{"device_id":"kiosk-001","api_key":"test"}' | jq` returns JWT + MQTT creds

---

### Week 3: Commands & Error Management

**Goals:**
- Command execution system
- Error/repair action CRUD
- Support user endpoints
- Repair outcome tracking

**Tasks:**

1. **Command System**
   - [ ] Implement `POST /api/devices/{device_id}/commands`
     - Validate command type
     - Create database record
     - Publish to MQTT topic: `beckhoff/{device_id}/commands`
     - Return command_id
   - [ ] Implement `GET /api/devices/{device_id}/commands`
     - Return command history
     - Include status (sent, executing, success, failed)
   - [ ] Command types: restart_plc, reset_state_machine, reboot_device, clear_error_log

2. **Error Management**
   - [ ] Implement `GET /api/errors/{error_code}/repair-actions`
     - Return sorted by success_rate (descending)
     - Include statistics (occurrences, success rate)
   - [ ] Implement `POST /api/errors/{error_code}/repair-actions`
     - Support user only
     - Validate input
     - Create new repair action
     - Auto-increment step_order

3. **Repair Outcomes**
   - [ ] Implement `POST /api/devices/{device_id}/repair-outcome`
     - Support user only
     - Link to repair_action_id
     - Record success/failure
     - Auto-update repair_action.success_rate
     - Auto-mark device error as resolved
   - [ ] Implement `GET /api/devices/{device_id}/repair-history`
     - Return last repairs on device
     - Include timestamps, outcomes, notes

4. **Testing**
   - [ ] Commands: 25+ tests
   - [ ] Errors/repairs: 35+ tests
   - [ ] Target: 75% coverage

**Deliverable:** Support can record "I tried action X, it worked" and system learns

---

### Week 4: Integration & Polish

**Goals:**
- Full end-to-end flow working
- All tests passing
- Documentation complete
- Ready for trial deployment

**Tasks:**

1. **End-to-End Testing**
   - [ ] Device flow: register → get status → send command → check history
   - [ ] Error flow: error occurs → show repair actions → support tries action → system learns
   - [ ] Test with real Docker Compose setup (not mocks)

2. **Database Migrations**
   - [ ] Create migration system (simple: alembic or home-grown)
   - [ ] Document: how to apply migrations on production

3. **Logging & Monitoring**
   - [ ] Structured logging (JSON format)
   - [ ] Log all auth attempts (success/failure)
   - [ ] Log all commands sent
   - [ ] Log all repair outcomes
   - [ ] Test: `docker-compose logs api | grep ERROR`

4. **Documentation**
   - [ ] README.md: Setup, running, testing
   - [ ] API.md: All endpoints with examples
   - [ ] DEPLOYMENT.md: How to deploy to DigitalOcean
   - [ ] LOCAL_DEV.md: Quick start for developers
   - [ ] nginx.conf: Inline comments explaining each section

5. **Code Quality**
   - [ ] Black formatter on all code
   - [ ] Flake8 linting (10 errors max)
   - [ ] Type hints on all functions
   - [ ] Docstrings on all public functions
   - [ ] Coverage report: 70%+ overall

6. **Error Handling**
   - [ ] All endpoints return proper HTTP status codes
   - [ ] Consistent error message format
   - [ ] Rate limit errors (429) with Retry-After header
   - [ ] 500 errors logged with request ID for debugging

**Deliverable:** Full Phase 1A complete, tests pass, documentation done, ready to deploy to DigitalOcean

---

### Week 5: Trial & Iteration (Phase 2)

**Goals:**
- Live on DigitalOcean
- PLC systems connected
- Real errors being captured
- Team learning from system

**Tasks:**

1. **Production Deployment**
   - [ ] Deploy to DigitalOcean droplet
   - [ ] Verify TLS certificates (Let's Encrypt)
   - [ ] Test rate limiting in production
   - [ ] Monitor: CPU, memory, disk usage
   - [ ] Backup: automated daily PostgreSQL dumps

2. **Monitoring & Observability**
   - [ ] Health checks working (dashboard shows all green)
   - [ ] Error logs visible and searchable
   - [ ] Metrics flowing into InfluxDB
   - [ ] Graphs working (if Grafana added)

3. **Team Training**
   - [ ] Support team trained on dashboard
   - [ ] Sales team trained on troubleshooting flow
   - [ ] Document: "When to try repair action vs escalate to developer"

4. **Feedback Loop**
   - [ ] Track which repairs work best
   - [ ] Identify common issues
   - [ ] Refine error messages
   - [ ] Update repair actions based on real data

**Deliverable:** System live, support team using it, learning happening

---

## Testing Strategy

### Coverage Targets

- **Backend API:** 75% coverage
- **Services:** 70% coverage
- **Database queries:** 80% coverage
- **Auth & security:** 90% coverage

### Test Categories

**Unit Tests** (60% of test suite)
- Each function tested in isolation
- Mock database, MQTT, etc.
- Fast, deterministic

**Integration Tests** (30% of test suite)
- Real PostgreSQL (in-memory sqlite for speed)
- Full API flow testing
- Command end-to-end

**Smoke Tests** (10% of test suite)
- Docker Compose starts cleanly
- Health check passes
- All containers healthy

### Required Test Files

```python
# tests/test_auth.py
- test_kiosk_login_valid_key
- test_kiosk_login_invalid_key
- test_kiosk_login_nonexistent_device
- test_jwt_token_generation
- test_jwt_token_validation
- test_jwt_token_expiry
- test_mqtt_credentials_generated
- test_mqtt_password_unique_per_login
- test_api_key_hashing (never plaintext stored)
- ... (25 total)

# tests/test_devices.py
- test_get_device_status_online
- test_get_device_status_offline
- test_get_device_status_with_error
- test_get_device_status_with_repair_suggestions
- test_get_all_devices_dashboard
- test_device_not_found_404
- ... (20 total)

# tests/test_commands.py
- test_send_command_success
- test_send_command_invalid_type
- test_get_command_history
- test_command_result_update
- ... (20 total)

# tests/test_errors.py
- test_get_repair_actions_for_error
- test_repair_actions_sorted_by_success_rate
- test_add_repair_action_support_only
- test_record_repair_outcome_success
- test_record_repair_outcome_failure
- test_success_rate_calculation
- test_device_error_marked_resolved
- ... (30 total)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v

# Run only fast tests
pytest -m "not slow"
```

---

## Deployment

### Local Development

```bash
# Clone repo
git clone https://github.com/company/device-manager-backend
cd device-manager-backend

# Create environment file
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# Run migrations
docker-compose exec api python -m alembic upgrade head

# Seed test data
docker-compose exec api python scripts/seed_db.py

# Run tests
docker-compose exec api pytest

# View logs
docker-compose logs -f api
```

### Production Deployment (DigitalOcean)

```bash
# On DigitalOcean droplet (after Ubuntu setup + Docker install)

# 1. Clone repo
git clone https://github.com/company/device-manager-backend
cd device-manager-backend

# 2. Create .env with production values
cat > .env << EOF
JWT_SECRET=$(openssl rand -hex 32)
DATABASE_URL=postgresql://postgres:$(openssl rand -hex 16)@postgres:5432/device_manager
MQTT_PASSWORD=$(openssl rand -hex 16)
EOF

# 3. Get TLS certificate
./scripts/setup-certificates.sh api.company.com

# 4. Start services
docker-compose up -d

# 5. Verify
curl https://api.company.com/health

# 6. Set up auto-renewal
cat > /etc/cron.d/certbot << EOF
0 3 * * * certbot renew --quiet && docker-compose -f /root/device-manager-backend/docker-compose.yml restart nginx
EOF
```

### GitHub Actions CI/CD (Phase 2)

```yaml
# .github/workflows/test.yml

name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=api
      - run: coverage report --fail-under=70
```

---

## Common Pitfalls

### Security

❌ **Don't:** Store API keys in plaintext  
✓ **Do:** Hash with SHA256 before storing

❌ **Don't:** Return JWT in error messages  
✓ **Do:** Log with request ID, return error code

❌ **Don't:** Skip certificate validation on production  
✓ **Do:** Require valid Let's Encrypt cert

❌ **Don't:** Hardcode secrets in code  
✓ **Do:** Use environment variables

### Database

❌ **Don't:** Create tables without indexes  
✓ **Do:** Add indexes on frequently queried columns

❌ **Don't:** Run migrations manually  
✓ **Do:** Automate with Alembic or similar

❌ **Don't:** Skip backups  
✓ **Do:** Daily automated PostgreSQL dumps

### API Design

❌ **Don't:** Return 200 for errors  
✓ **Do:** Return proper HTTP status (401, 404, 429, etc.)

❌ **Don't:** Return raw database errors to client  
✓ **Do:** Log error, return generic message

❌ **Don't:** Allow unbounded queries  
✓ **Do:** Add pagination (limit, offset)

### Testing

❌ **Don't:** Mock the database  
✓ **Do:** Use real PostgreSQL (in Docker) for integration tests

❌ **Don't:** Skip testing error paths  
✓ **Do:** Test 401, 404, 429 responses

❌ **Don't:** Ignore flaky tests  
✓ **Do:** Fix or mark with `@pytest.mark.flaky`

---

## Key Decisions & Rationale

### Why FastAPI (not Django)?

| Aspect | FastAPI | Django |
|--------|---------|--------|
| **Async support** | Native | Bolted on |
| **Speed** | Very fast | Slower |
| **API-first** | Yes | Web-first |
| **Learning curve** | Gentle | Steep |
| **IoT/real-time** | Excellent | OK |

**Decision:** FastAPI for real-time metrics, async MQTT publishing, and speed.

### Why PostgreSQL (not SQLite)?

| Aspect | PostgreSQL | SQLite |
|--------|-----------|--------|
| **Concurrency** | Excellent | Poor |
| **Scaling** | Yes | No |
| **Transactions** | Full ACID | Basic |
| **Backups** | Easy | File-based |

**Decision:** PostgreSQL for concurrent device updates and future scaling to 220 devices.

### Why Nginx (not built-in rate limiting)?

| Aspect | Nginx | FastAPI |
|--------|-------|---------|
| **Code** | Config | Python code |
| **Performance** | Fast | Slower |
| **Changeability** | Restart service | Redeploy |
| **Visibility** | Logs | App logs |

**Decision:** Nginx for infrastructure-level rate limiting, TLS, and separation of concerns.

### Why Mosquitto (not just REST)?

| Aspect | MQTT | REST only |
|--------|------|-----------|
| **Publish-subscribe** | Yes | No |
| **Bandwidth** | Low | Higher |
| **Real-time metrics** | Efficient | Polling |
| **Complexity** | More | Less |

**Decision:** MQTT for efficient metrics streaming from 220+ devices.

### Why InfluxDB (not PostgreSQL for metrics)?

| Aspect | InfluxDB | PostgreSQL |
|--------|----------|-----------|
| **Time-series** | Optimized | Generic |
| **Storage** | Compressed | Not compressed |
| **Querying speed** | Fast | Slower |
| **Retention** | Built-in | Manual |

**Decision:** InfluxDB for efficient storage and fast historical queries.

---

## Success Criteria (Phase 1 Complete)

✓ All endpoints implemented and tested (70% coverage)  
✓ Docker Compose brings up complete system  
✓ Nginx rate limiting working  
✓ TLS certificates auto-renewing  
✓ Database schema supports error/repair knowledge base  
✓ Support users can add/update repair actions via API  
✓ System tracks success rates of repair actions  
✓ Documentation complete and accurate  
✓ Deployment to DigitalOcean successful  
✓ PLC systems connecting and sending metrics  
✓ Dashboard showing real device status  

---

## Questions & Escalation

**For clarifications, ask:**
1. Where should error_id be generated on device side or backend?
2. Should MQTT credentials be stored encrypted in database?
3. Do we need audit trail of who changed what repair action?
4. Should support users have RBAC (admin vs operator)?
5. What's the max metrics retention in InfluxDB?

**Escalate if:**
- Database schema needs changes (breaking change for deployed systems)
- API contract changes (would require kiosk code changes)
- Security issue found
- Performance issue with >50 concurrent devices

---

## References

- Nginx Rate Limiting: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL: https://www.postgresql.org/docs/15/
- MQTT Spec: https://mqtt.org/mqtt-specification
- InfluxDB: https://docs.influxdata.com/influxdb/
- Let's Encrypt: https://letsencrypt.org/docs/

---

**Document Version:** 1.0  
**Last Updated:** June 2026  
**Status:** Ready for Implementation
