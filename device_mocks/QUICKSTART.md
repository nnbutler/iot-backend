# Quick Start: Mock Device Simulator

Get mock devices running in seconds.

## 1. Single Device (Simplest)

```bash
cd device_mocks
pip install paho-mqtt requests

# Run a device that sends metrics every 10 seconds
python3 mock_device.py --device-id my-device-001
```

Watch the output:
```
✓ Device registered. API Key: ...
✓ Connected to MQTT broker
💓 Heartbeat sent. throughput=1621, cycle_time=2.53s, error_rate=0.21%, error=none
```

✅ Now open http://localhost:8080 and see your device in the dashboard!

## 2. Multiple Devices (Testing)

```bash
# Spawn 5 devices in separate threads
python3 mock_device.py --device-id load-test --num-devices 5
```

✅ Dashboard now shows 5 devices with varying metrics and occasional errors.

## 3. Docker (Production-like)

**First**: Start the main backend stack:
```bash
docker compose up -d
```

**Then** (in another terminal): Run mock device in Docker:
```bash
docker compose -f device_mocks/docker-compose.yml up device-single
```

✅ Device running in isolated container, just like real hardware.

## 4. Device Farm (Load Test)

**First**: Start the main backend stack:
```bash
docker compose up -d
```

**Then** (in another terminal): Start 4 mock devices (1 default + 3 farm):
```bash
docker compose -f device_mocks/docker-compose.yml --profile farm up
```

✅ Watch how the dashboard performs with 4 devices!

## Testing Checklist

### Device Registration ✓
- [ ] Run a mock device
- [ ] Check dashboard: does device appear?
- [ ] Check device list API: `curl https://localhost:8443/api/devices`

### Metrics Collection ✓
- [ ] Run a mock device for 30 seconds
- [ ] Check device detail page: see throughput, cycle_time, error_rate?
- [ ] Run `/api/devices/{id}/metrics` endpoint

### Error Simulation ✓
- [ ] Run a mock device for 2+ minutes
- [ ] Does it randomly show errors?
- [ ] Does it recover automatically?
- [ ] Check repair actions appear in dashboard?

### Commands ✓
- [ ] Open a device detail page
- [ ] Send a "reboot_device" command
- [ ] Check device logs: does device receive it? (look for "📨 Received command")
- [ ] Does dashboard show command as "success"?

### Logs ✓
- [ ] Run a device for 1 minute
- [ ] Check device detail page: see logs appearing?

## Troubleshooting

### "Failed to register: Connection refused"
```bash
# Backend not running. Start it:
docker compose up -d
```

### "Failed to register: 409 Conflict"
```bash
# Device already exists. Use a different ID:
python3 mock_device.py --device-id my-device-$(date +%s)
```

### "Failed to connect to MQTT"
```bash
# Mosquitto not running. Check:
docker compose ps | grep mosquitto
# Should see: iot-mqtt ... mosquitto:2 ... Up
```

### No metrics appearing on dashboard
- Check device is actually running: look for "💓 Heartbeat sent" logs
- Refresh dashboard (F5)
- Check InfluxDB connectivity (check backend logs)

## Common Commands

```bash
# Run 1 device, 10-second heartbeat
python3 mock_device.py

# Run 3 devices, 5-second heartbeat
python3 mock_device.py --num-devices 3 --heartbeat-interval 5

# Run device for a specific customer
python3 mock_device.py --customer "Acme Inc" --location "Factory A"

# Run with custom backend URL (for remote testing)
python3 mock_device.py --backend-url https://my-backend.com

# Run multiple devices, each with 3-second heartbeat (high traffic)
python3 mock_device.py --num-devices 10 --heartbeat-interval 3
```

## What the Device Does

Every heartbeat (default 10 seconds):
- ✓ Reports current state: online, firmware version
- ✓ Sends metrics: throughput (1000-2000 items/hr), cycle_time (1-3 sec), error_rate (0-5%)
- ✓ Randomly (5% chance) triggers an error, recovers with 30% chance per heartbeat
- ✓ 20% chance to publish a log message
- ✓ Listens for commands, executes them (95% success rate)

## Next Steps

See [README.md](README.md) for:
- More detailed configuration options
- Custom device behavior modifications
- Multi-device load testing scenarios
- Debugging tips
