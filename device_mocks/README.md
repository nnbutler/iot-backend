# Mock Device Simulator

Simulates real IoT devices (PLCs) for development, testing, and demonstrations.

## Features

Mock devices automatically:
- 📝 Register with the backend
- 💓 Send periodic heartbeats with realistic metrics
- 📊 Report throughput, cycle time, error rate
- 🚨 Simulate occasional errors and recovery
- 📋 Publish logs
- 📡 Receive and execute commands
- 🔄 Report command results back to backend

## Running a Single Device

### Option 1: Run Locally (Python)

```bash
cd device_mocks
pip install -r requirements.txt

# Single device
python mock_device.py --device-id my-device-001 --customer "My Company"

# With options
python mock_device.py \
  --device-id my-device-001 \
  --backend-url https://localhost:8443 \
  --mqtt-broker localhost \
  --customer "My Company" \
  --location "Factory Floor" \
  --heartbeat-interval 15
```

### Option 2: Run in Docker (with main stack)

```bash
# Start the main backend first
docker compose up -d

# Then run a mock device in a separate container
docker compose -f device_mocks/docker-compose.yml up device-single
```

## Running Multiple Devices

### Option 1: Python with Threading

```bash
python mock_device.py \
  --device-id mock-device \
  --num-devices 5 \
  --heartbeat-interval 10
```

This spawns 5 devices (`mock-device-1` through `mock-device-5`) in separate threads, each sending heartbeats.

### Option 2: Docker Compose Farm

Enable the `farm` profile to spin up 3 additional devices:

```bash
docker compose -f device_mocks/docker-compose.yml \
  --profile farm \
  up
```

This runs 4 total devices:
- `mock-plc-001` (default)
- `mock-farm-01`, `mock-farm-02`, `mock-farm-03` (farm profile)

## Device Behavior

### Heartbeat Metrics

Each heartbeat includes:

```json
{
  "online": true,
  "state": "running",
  "firmware_version": "1.2.3",
  "throughput": 1500.0,      // items/hour
  "cycle_time": 2.1,         // seconds
  "error_rate": 0.02,        // 2% errors
  "last_error": null
}
```

- **Throughput**: Random 1000-2000 items/hour
- **Cycle time**: Random 1-3 seconds per cycle
- **Error rate**: 0-5% normally; jumps to 50% on error
- **Errors**: Randomly occur (5% chance per heartbeat), randomly recover (30% chance if in error)

### Error Simulation

Devices randomly experience errors like:
- `sensor_disconnected`
- `state_machine_timeout`
- `calibration_needed`
- `temperature_high`

Recovery is automatic with a 30% chance per heartbeat.

### Command Execution

When the backend sends a command (e.g., `reboot_device`), the mock device:
1. Receives the command on `devices/{device_id}/commands` MQTT topic
2. Simulates 1-3 seconds of work
3. Reports success (95% chance) or failure
4. Publishes result to `devices/{device_id}/command-result/{command_id}`

### Logs

Devices occasionally (20% chance per heartbeat) publish INFO logs.

## Command-Line Options

```
--device-id           Device ID (default: mock-device-001)
--backend-url         Backend URL (default: https://localhost:8443)
--mqtt-broker         MQTT broker host (default: localhost)
--mqtt-port          MQTT broker port (default: 1883)
--customer            Customer name (default: Test Customer)
--location            Device location (default: Test Lab)
--heartbeat-interval  Seconds between heartbeats (default: 10)
--num-devices        Number of devices to spawn (default: 1)
```

## Testing Scenarios

### 1. Dashboard Test

```bash
# Spawn 5 devices, watch the dashboard fill with devices
python mock_device.py --num-devices 5

# Open http://localhost:8080/devices
# Devices appear in real-time with status, metrics
```

### 2. Error Handling Test

```bash
# Watch errors occur and recover automatically
python mock_device.py --device-id error-test-01

# Backend dashboard shows errors appearing/resolving
# Repair actions can be tested
```

### 3. Command Test

```bash
# Send a command from the dashboard while device is running
python mock_device.py --device-id cmd-test-01

# Command received → device executes → result reported
# Check command history in device detail view
```

### 4. Load Test

```bash
# Spawn 20 devices to test dashboard/API performance
python mock_device.py --device-id load-test --num-devices 20

# Monitor:
# - Device list response time
# - Dashboard rendering speed
# - MQTT message throughput
```

## Troubleshooting

### Device Registration Fails

```
Error: Failed to register device: Failed to connect to https://localhost:8443
```

**Solution**: Ensure the backend is running:
```bash
docker compose up -d
```

### MQTT Connection Fails

```
Error: Failed to connect to MQTT
```

**Solution**: Ensure Mosquitto is running:
```bash
docker compose ps | grep mosquitto
```

### No Heartbeats Appearing

Check the mock device logs:
```bash
# If running in Docker
docker logs iot-mock-device-001

# Look for lines like:
# ✓ Device registered
# ✓ Connected to MQTT broker
# 💓 Heartbeat sent
```

## Development

### Adding Custom Device Behavior

Edit `mock_device.py` to customize:
- `_simulate_workload()` - Change metric ranges
- `_simulate_error()` - Add/remove error types
- `_handle_command()` - Add command handlers
- `send_log()` - Change log frequency/content

### Example: Always Report High Throughput

```python
def _simulate_workload(self):
    self.throughput = 3000  # Always high
    self.cycle_time = random.uniform(1.0, 2.0)
    self.error_rate = 0.0
```

### Example: Never Have Errors

```python
def _simulate_error(self):
    self.last_error = None
    self.error_rate = 0.0
```

## Architecture

```
Mock Device
├── Register with Backend
│   └── Get API Key
├── Connect to MQTT
│   └── Subscribe to commands/{device_id}
└── Main Loop (every N seconds)
    ├── Simulate metrics
    ├── Send heartbeat (REST or MQTT)
    ├── Maybe send log
    └── Check for commands, execute them
```

The device can use either REST API (simpler) or MQTT (more realistic) for heartbeats. It automatically falls back if one fails.
