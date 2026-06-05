# Device Logs Scalability Analysis

## Executive Summary

**Current architecture risk level: 🟡 MODERATE** 

The current PostgreSQL-based logging system will **hit limitations at 100K+ devices or >1M logs/day**. This document identifies bottlenecks and recommends solutions.

---

## Baseline: Current Architecture

```
Device → MQTT → Backend (single-threaded MQTT handler) → PostgreSQL → REST API → Frontend
```

**Limitations:**
- PostgreSQL: good for transactions, **poor for time-series append-only data**
- MQTT handler: processes logs sequentially (single message loop)
- No log rotation or retention policy
- No sampling or rate limiting
- All logs live indefinitely in one table

---

## Growth Projections

### Scenario 1: Modest Scale (10-50 devices, normal logging)

| Metric | Value | Impact |
|--------|-------|--------|
| Devices | 50 | Low |
| Logs per device per day | 100 | ~5K logs/day total |
| Annual rows | 1.8M | ~2 GB storage |
| Query time (50 newest logs) | <10ms | ✅ Acceptable |
| Disk I/O | Low | ✅ Fine |

**Status:** ✅ **No issues.** Current architecture works fine.

---

### Scenario 2: Growth Phase (100-500 devices, moderate-verbose logging)

| Metric | Value | Impact |
|--------|-------|--------|
| Devices | 500 | Medium |
| Logs per device per day | 500 | ~250K logs/day total |
| Annual rows | 91M | ~100 GB storage |
| Query time (50 newest logs) | 50-200ms | ⚠️ Noticeable |
| Insert rate | ~3/sec avg, 10/sec peak | ⚠️ Manageable but tight |
| Disk I/O | Medium | ⚠️ Noticeable |
| Index size | ~20 GB | ⚠️ Increases cache misses |

**Status:** 🟡 **Approaching limits.** Querying becomes slower. Storage grows. Need monitoring.

**Pain points:**
- Pagination queries on millions of rows get slower (even with cursor pagination)
- Database backups take longer (100 GB takes hours)
- Disk space management becomes a concern

---

### Scenario 3: Heavy Scale (1000+ devices, verbose logging)

| Metric | Value | Impact |
|--------|-------|--------|
| Devices | 1000+ | High |
| Logs per device per day | 1000+ | ~1M+ logs/day total |
| Annual rows | 365M+ | ~400+ GB storage |
| Insert rate | ~12/sec avg, 50/sec peak | 🔴 **Problematic** |
| Query latency | 500ms - 2s | 🔴 **Unacceptable** |
| MQTT bottleneck | Sequential handler | 🔴 **Overloaded** |
| Disk I/O saturation | Yes | 🔴 **System stress** |

**Status:** 🔴 **CRITICAL ISSUES.**

**What breaks:**
1. **MQTT Handler Bottleneck** — processes messages one-at-a-time. If 50 logs/sec arrive, they queue.
2. **PostgreSQL Insert Contention** — single-threaded handler can't leverage DB concurrency.
3. **Query Slowness** — scanning 365M rows even with indices is slow.
4. **Storage** — 400 GB/year is expensive (disk, backup bandwidth, recovery time).
5. **Retention Policy Missing** — logs accumulate forever → disk fills → system crashes.

---

## Critical Issues

### Issue 1: MQTT Handler is Single-Threaded

**File:** `backend/app/services/mqtt.py`

```python
self.client.loop_start()  # Single background thread processes ALL messages
```

**Problem:** 
- All MQTT messages processed sequentially in one thread
- Each message waits for previous DB insert to complete
- 50 concurrent logs/sec = queue backlog

**Symptom:** Device sends log, but it appears in DB 5+ seconds later (lag).

---

### Issue 2: PostgreSQL Not Optimized for Time-Series Logs

**Current approach:**
- Generic relational DB
- Single `device_logs` table grows unbounded
- Indices help but don't solve fundamental problem

**Why it's wrong:**
- Log data is **append-only** (never updated)
- Logs are **time-series** (constant stream of new rows)
- PostgreSQL's B-tree indices become inefficient at 100M+ rows
- Table bloat from continuous INSERTs (needs VACUUM)

**Time-series DBs** (InfluxDB, TimescaleDB, Clickhouse) are designed exactly for this:
- Compression: 10-100x better than relational DBs
- Fast inserts: optimize for write-heavy workloads
- Fast range queries: get "logs from 9am-10am" instantly
- Automatic retention: delete old data cleanly

---

### Issue 3: No Log Retention Policy

**Current:**
- Logs stored indefinitely
- Disk will eventually fill
- No way to reclaim space

**Risk:**
- Disk fills → PostgreSQL errors → entire system down
- Unplanned downtime trying to delete old logs

---

### Issue 4: No Rate Limiting or Sampling

**Current:**
- Device can send unlimited logs
- A chatty device floods the system

**Risk:**
- One broken device producing 1000 logs/sec crashes the MQTT handler
- System has no protection

---

### Issue 5: REST API Scalability

**Endpoint:** `GET /api/devices/{device_id}/logs`

**Current:**
- Cursor pagination helps, but still queries PostgreSQL
- Large device_ids table scan still expensive

**Risk:**
- 100 simultaneous users on the page = 100 DB queries
- Under heavy load, API becomes slow

---

## Recommended Solutions

### Solution 1: Move Logs to InfluxDB (RECOMMENDED)

**Status:** 🟢 **Best fit** — we already have InfluxDB running.

**How:**
1. Keep PostgreSQL for relational data (devices, commands, errors)
2. Move **logs to InfluxDB time-series storage**
3. Send logs to both MQTT and InfluxDB in the backend

**Implementation:**

```python
# In backend/app/services/mqtt.py _handle_logs()
db.add(DeviceLog(device_id=device_id, level=level, message=message))  # Keep for compatibility
metrics_db.store_log(device_id, level, message)  # NEW: also store in InfluxDB
```

**InfluxDB Schema:**

```python
# Measurement: device_log
# Tags: device_id, level (searchable)
# Fields: message (text)
# Timestamp: auto

# Example line protocol:
# device_log,device_id=my-device,level=ERROR message="Sensor disconnected" 1717594200000000000
```

**Benefits:**
- ✅ Compression: 100x smaller storage
- ✅ Fast queries: get last 50 ERROR logs in milliseconds
- ✅ Built-in retention: automatically delete logs older than 30 days
- ✅ Scales to billions of logs
- ✅ No table bloat or VACUUM needed

**Drawbacks:**
- Need to migrate REST API queries from PostgreSQL to InfluxDB Flux
- InfluxDB Flux syntax is different (but we already use it for metrics)
- Can keep PostgreSQL as backup/audit trail, migrate gradually

---

### Solution 2: Implement Log Rotation + TTL (GOOD, SHORT-TERM)

**Status:** 🟠 **Good interim fix** — implement immediately while planning InfluxDB migration.

**How:**
1. Add retention policy: keep logs for N days (e.g., 30 days)
2. Auto-delete logs older than retention window

**Implementation in `backend/app/models/device.py`:**

```python
class DeviceLog(Base):
    __tablename__ = "device_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), nullable=False, index=True)
    level = Column(String(20))
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_device_timestamp', 'device_id', 'timestamp'),
    )
```

**Create a background job in `backend/app/services/log_cleanup.py`:**

```python
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

LOG_RETENTION_DAYS = 30  # configurable

def cleanup_old_logs(db: Session):
    """Delete logs older than retention window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)
    deleted = db.query(DeviceLog).filter(DeviceLog.timestamp < cutoff).delete()
    db.commit()
    logger.info(f"Cleaned up {deleted} old logs")
```

**Run daily via Celery or APScheduler:**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.log_cleanup import cleanup_old_logs

scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_logs, 'interval', days=1, args=[db_session])
scheduler.start()
```

**Benefits:**
- ✅ Disk doesn't fill up
- ✅ Queries stay fast (no 365M row table)
- ✅ Quick to implement (few hours)

**Drawbacks:**
- ⚠️ Old logs lost after 30 days (compliance risk if you need audit trail)
- ⚠️ Doesn't solve insert bottleneck at high scale
- ⚠️ Still not optimized for time-series workload

---

### Solution 3: Add Rate Limiting

**Status:** 🟢 **Must do** — protect system from runaway devices.

**Implementation in `backend/app/services/mqtt.py`:**

```python
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# Track log counts per device per minute
log_counters = defaultdict(list)
MAX_LOGS_PER_MINUTE = 100  # per device

def _handle_logs(self, device_id: str, payload: bytes):
    # Check rate limit
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=1)
    log_counters[device_id] = [
        ts for ts in log_counters[device_id] if ts > cutoff
    ]
    
    if len(log_counters[device_id]) >= MAX_LOGS_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for {device_id}")
        return  # Drop this log
    
    log_counters[device_id].append(now)
    
    # ... rest of normal processing
```

**Benefits:**
- ✅ Protects against log floods
- ✅ Prevents one device from crashing the system

---

### Solution 4: Add MQTT Handler Parallelization (ADVANCED)

**Status:** 🟠 **Advanced optimization** — use only if high scale needed.

**Idea:**
- Use thread pool to process MQTT messages concurrently
- Each log message gets a worker thread from pool

**Benefits:**
- ✅ Can handle 50+ logs/sec without queueing
- ✅ Better DB utilization

**Drawbacks:**
- ⚠️ Complex to implement safely (thread safety, connection pooling)
- ⚠️ Doesn't scale beyond 1000 logs/sec anyway
- ⚠️ InfluxDB is better solution for that scale

---

## Recommendation: Phased Approach

### Phase 1 (Immediate - This Week) 🟢
1. **Add log retention policy** (Solution 2)
   - Delete logs older than 30 days
   - Prevents disk exhaustion
   - ~4 hours of work

2. **Add rate limiting** (Solution 3)
   - Max 100 logs/device/minute
   - Protects against runaway devices
   - ~2 hours of work

3. **Monitor logging volume**
   - Add metrics: logs_per_device, logs_per_second
   - Alert if hitting thresholds
   - ~2 hours of work

### Phase 2 (Next Sprint)  🟠
1. **Create InfluxDB log storage service** (Solution 1, part 1)
   - Mirror logs to InfluxDB while keeping PostgreSQL
   - No breaking changes to API
   - ~8 hours of work

2. **Migrate REST API to query InfluxDB** (Solution 1, part 2)
   - Get logs from InfluxDB instead of PostgreSQL
   - Same REST API response format
   - ~6 hours of work

3. **Set InfluxDB retention policy**
   - Auto-delete logs older than 90 days
   - Compression saves 100x storage
   - ~2 hours of work

### Phase 3 (When needed)
1. Remove PostgreSQL DeviceLog table (after confident in InfluxDB)
2. Add advanced features: full-text search, sampling, real-time streaming

---

## Current Status & Action Items

### ✅ Already Good
- Cursor pagination (doesn't load all logs into memory)
- Severity filtering (filtered at DB level, not in app)
- Proper indices on device_id and timestamp

### 🔴 Needs Action (Next Week)
- [ ] Add log retention policy (30 days)
- [ ] Add rate limiting (100 logs/device/min)
- [ ] Add logging metrics (logs/sec, device log counts)

### 🟡 Medium-term (Next Sprint)
- [ ] Migrate logs to InfluxDB
- [ ] Update REST API to query InfluxDB

---

## Estimating Your Scale

**Quick calculation:**

```
Total logs per day = (# devices) × (# logs per device per day)
```

**Examples:**

| Scenario | Devices | Logs/Device/Day | Total/Day | Risk Level |
|----------|---------|-----------------|-----------|-----------|
| Dev/test | 5 | 100 | 500 | ✅ None |
| Small prod | 50 | 100 | 5K | ✅ None |
| Growing prod | 500 | 500 | 250K | 🟡 Monitor |
| Large scale | 2000 | 1000 | 2M | 🔴 Redesign |

**Your expected scale?** [Replace with user input]

---

## Questions to Guide Design

1. **How many devices do you expect in 1 year?** (10s? 100s? 1000s?)
2. **How verbose is typical device logging?** (1 log/min? 1 per second?)
3. **Do you need to retain logs for compliance?** (30 days? 1 year?)
4. **What's your disk budget?** (10 GB? 100 GB? 1 TB?)
5. **What query patterns matter most?** (latest logs? logs by level? logs in time range?)

Answers will inform whether Phase 1-only or full migration is needed.
