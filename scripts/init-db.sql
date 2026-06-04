-- =============================================================================
-- USER MANAGEMENT
-- =============================================================================

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email       VARCHAR(100),
    role        VARCHAR(50) DEFAULT 'support',  -- support, developer, admin
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_users_username ON users(username);

-- =============================================================================
-- DEVICE MANAGEMENT
-- =============================================================================

CREATE TABLE devices (
    id                    SERIAL PRIMARY KEY,
    device_id             VARCHAR(100) UNIQUE NOT NULL,  -- e.g. "plc-001"
    api_key               VARCHAR(255) UNIQUE NOT NULL,  -- SHA256 hashed
    device_type           VARCHAR(100),                  -- "plc", "sensor_hub", etc.
    location              VARCHAR(255),
    customer_name         VARCHAR(255),
    online                BOOLEAN DEFAULT FALSE,
    last_seen             TIMESTAMPTZ,
    last_error            VARCHAR(255),
    last_error_timestamp  TIMESTAMPTZ,
    state                 VARCHAR(100),
    firmware_version      VARCHAR(50),
    created_at            TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at            TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_devices_device_id   ON devices(device_id);
CREATE INDEX idx_devices_online      ON devices(online);
CREATE INDEX idx_devices_customer    ON devices(customer_name);

-- =============================================================================
-- ERROR TYPES & REPAIR ACTIONS (Knowledge Base)
-- =============================================================================

CREATE TABLE error_types (
    id                       SERIAL PRIMARY KEY,
    error_code               VARCHAR(100) UNIQUE NOT NULL,
    display_name             VARCHAR(255) NOT NULL,
    description              TEXT,
    severity                 VARCHAR(20),  -- low, medium, high, critical
    customer_visible_message TEXT,
    created_at               TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at               TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_error_types_code ON error_types(error_code);

CREATE TABLE repair_actions (
    id                      SERIAL PRIMARY KEY,
    error_id                INTEGER NOT NULL REFERENCES error_types(id) ON DELETE CASCADE,
    step_order              INTEGER NOT NULL,
    action                  TEXT NOT NULL,
    description             TEXT,
    estimated_time_minutes  INTEGER,
    success_rate            FLOAT DEFAULT 0.5,
    occurrences             INTEGER DEFAULT 0,
    successful_occurrences  INTEGER DEFAULT 0,
    created_by              VARCHAR(100),
    created_at              TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at              TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(error_id, step_order)
);

CREATE INDEX idx_repair_actions_error ON repair_actions(error_id);

CREATE TABLE repair_outcomes (
    id                 SERIAL PRIMARY KEY,
    device_id          VARCHAR(100) NOT NULL,
    error_id           INTEGER NOT NULL REFERENCES error_types(id),
    repair_action_id   INTEGER REFERENCES repair_actions(id),
    worked             BOOLEAN NOT NULL,
    notes              TEXT,
    time_spent_minutes INTEGER,
    attempted_by       VARCHAR(100),
    attempted_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_at         TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_repair_outcomes_device      ON repair_outcomes(device_id);
CREATE INDEX idx_repair_outcomes_error       ON repair_outcomes(error_id);
CREATE INDEX idx_repair_outcomes_attempted_at ON repair_outcomes(attempted_at DESC);

CREATE TABLE device_error_history (
    id               SERIAL PRIMARY KEY,
    device_id        VARCHAR(100) NOT NULL,
    error_id         INTEGER REFERENCES error_types(id),
    error_message    TEXT,
    occurred_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    resolved_at      TIMESTAMPTZ,
    resolution_notes TEXT,
    resolved_by      VARCHAR(100)
);

CREATE INDEX idx_device_error_history_device   ON device_error_history(device_id);
CREATE INDEX idx_device_error_history_occurred ON device_error_history(occurred_at DESC);

-- =============================================================================
-- COMMANDS
-- =============================================================================

CREATE TABLE commands (
    id            SERIAL PRIMARY KEY,
    device_id     VARCHAR(100) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    command_type  VARCHAR(100) NOT NULL,  -- "restart_plc", "reset_state_machine", etc.
    status        VARCHAR(50) DEFAULT 'sent',  -- sent, executing, success, failed
    result        TEXT,
    error_message TEXT,
    sent_by       VARCHAR(100),
    sent_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    executed_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_commands_device  ON commands(device_id);
CREATE INDEX idx_commands_status  ON commands(status);
CREATE INDEX idx_commands_created ON commands(created_at DESC);

-- =============================================================================
-- DEVICE LOGS
-- =============================================================================

CREATE TABLE device_logs (
    id         SERIAL PRIMARY KEY,
    device_id  VARCHAR(100) NOT NULL,
    level      VARCHAR(20),   -- ERROR, WARNING, INFO
    message    TEXT,
    timestamp  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_device_logs_device    ON device_logs(device_id);
CREATE INDEX idx_device_logs_level     ON device_logs(level);
CREATE INDEX idx_device_logs_timestamp ON device_logs(timestamp DESC);

-- =============================================================================
-- MQTT CREDENTIALS
-- =============================================================================

CREATE TABLE mqtt_credentials (
    id            SERIAL PRIMARY KEY,
    device_id     VARCHAR(100) NOT NULL UNIQUE,
    username      VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_mqtt_credentials_device ON mqtt_credentials(device_id);

-- =============================================================================
-- SEED DATA
-- =============================================================================

INSERT INTO error_types (error_code, display_name, severity, customer_visible_message, description)
VALUES
    ('sensor_disconnected',  'Sensor Disconnected',        'medium',   'Sensor not responding',       'A connected sensor is not reporting data to the PLC'),
    ('photoeye_misaligned',  'Photoeye Not Detecting',     'high',     'Object detection failed',     'Photoeye reflector fallen off or misaligned'),
    ('internet_down',        'Internet Connectivity Lost', 'critical', 'Device not connected',        'Device cannot reach backend'),
    ('state_machine_stuck',  'Unit In Stuck State',        'high',     'Device not responding',       'Device logic stuck in state machine, needs reset'),
    ('unknown_error',        'Unknown Error',              'medium',   'Unexpected error occurred',   'Generic error, needs investigation');

-- Repair actions: sensor_disconnected (id=1)
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (1, 1, 'Check physical cable connection at sensor and PLC',  'Verify cable is plugged in at both ends and connector is seated properly', 5),
    (1, 2, 'Power cycle the sensor',                             'Turn off sensor, wait 10 seconds, turn back on',                          2),
    (1, 3, 'Power cycle entire unit',                            'Perform full power cycle of the entire equipment',                        3);

-- Repair actions: photoeye_misaligned (id=2)
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (2, 1, 'Check reflector is aligned and clean', 'Visually inspect reflector is in correct position and not dirty', 5),
    (2, 2, 'Clean photoeye lens',                  'Use soft cloth to gently clean the photoeye lens',               2);

-- Repair actions: internet_down (id=3)
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (3, 1, 'Check network cable at unit',         'Verify Ethernet cable is connected to device network port',              1),
    (3, 2, 'Power cycle router/modem',            'Unplug network equipment, wait 30 seconds, plug back in',               3),
    (3, 3, 'Check router status with customer',   'Ask customer to describe router lights (all solid green = good)',        2);

-- Repair actions: state_machine_stuck (id=4)
INSERT INTO repair_actions (error_id, step_order, action, description, estimated_time_minutes)
VALUES
    (4, 1, 'Power cycle unit',          'Turn off device for 30 seconds, turn back on',                      3),
    (4, 2, 'Check sensor readings',     'Verify sensors are giving stable readings (not flickering)',         5);
