# Hardware Alert API

FastAPI-based IoT hardware alert system for Raspberry Pi with LED and buzzer control.

## Features

- **FastAPI REST API** with `/api/v1/hardware-alert` endpoint
- **GPIO Control** for LED (GPIO 18) and KY-012 buzzer (GPIO 24)
- **Queue System** to prevent hardware conflicts from concurrent requests
- **Structured JSON Logging** with industry standards
- **Severity-based Alerts**:
  - **Critical**: Fast LED blink + continuous buzzer (10s)
  - **High**: Medium LED blink + 3 buzzer beeps (5s)
  - **Medium**: Slow LED blink (5s, no buzzer)
  - **Low**: LED on (2s, no buzzer)

## Quick Setup

1. **Install dependencies**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Run the API**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Usage

### Endpoint: `POST /api/v1/hardware-alert`

**Example Request**:
```json
{
  "sensor_data": {
    "device_id": "DEV-001",
    "temperature_dht": 28.5,
    "humidity": 65.2,
    "gas_quality": "poor",
    "acceleration": {
      "x": 0.12,
      "y": -0.05,
      "z": 9.78
    },
    "gyroscope": {
      "x": 2.1,
      "y": -0.3,
      "z": 1.4
    },
    "flame_detected": true,
    "timestamp": "2025-08-29T01:55:58.123456+07:00",
    "temperature_mpu": 27.8
  },
  "severity": "critical",
  "alert_type": "overheat"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Alert received and queued for processing",
  "alert_id": "a1b2c3d4",
  "queued": true
}
```

## Production Deployment

### Option 1: Systemd Service (Recommended)

1. **Create service**:
   ```bash
   python3 systemd_service.py create
   ```

2. **Start service**:
   ```bash
   sudo systemctl start hardware-alert-api
   ```

3. **Check status**:
   ```bash
   sudo systemctl status hardware-alert-api
   ```

4. **View logs**:
   ```bash
   sudo journalctl -u hardware-alert-api -f
   ```

### Option 2: Manual Run

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Hardware Connections

- **LED**: GPIO 18 (Pin 12) → LED → 220Ω resistor → GND
- **KY-012 Buzzer**: GPIO 24 (Pin 18) → Buzzer VCC, GND → Pi GND

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /api/v1/hardware-alert` - Process hardware alert
- `GET /docs` - Swagger API documentation

## Development

The project includes simulation mode when `RPi.GPIO` is not available, allowing development on non-Pi systems.

## Logging

Structured JSON logs include:
- HTTP request details
- Alert processing status
- Hardware control events
- Error tracking with context
