from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime

from models import HardwareAlertRequest, AlertResponse
from hardware_controller import HardwareController
from logger_config import StructuredLogger

# Global instances
hardware_controller = None
structured_logger = StructuredLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global hardware_controller

    # Startup
    structured_logger.logger.info(
        "Starting Hardware Alert API",
        extra={"event_type": "app_startup", "timestamp": datetime.now().isoformat()},
    )

    hardware_controller = HardwareController(
        red_pin=17,
        green_pin=27,
        blue_pin=22,
        buzzer_pin=24,
        pwm_freq=500,
        common_anode=False,  # Set to True if using common anode RGB LED
    )
    await hardware_controller.start_queue_processor()

    yield

    # Shutdown
    structured_logger.logger.info(
        "Shutting down Hardware Alert API",
        extra={"event_type": "app_shutdown", "timestamp": datetime.now().isoformat()},
    )

    if hardware_controller:
        hardware_controller.cleanup()


# FastAPI app with lifespan
app = FastAPI(
    title="Hardware Alert API",
    description="IoT Hardware Alert System with RGB LED and Buzzer for Raspberry Pi",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Hardware Alert API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    queue_size = hardware_controller.alert_queue.qsize() if hardware_controller else 0

    return {
        "status": "healthy",
        "hardware_active": hardware_controller.is_active
        if hardware_controller
        else False,
        "queue_size": queue_size,
        "gpiod_available": hardware_controller.gpio is not None
        if hardware_controller
        else False,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/v1/hardware-alert", response_model=AlertResponse)
async def hardware_alert(request: HardwareAlertRequest, http_request: Request):
    """
    Process hardware alert and trigger appropriate PWM RGB LED effects

    Severity levels:
    - critical: Fast RED pulsing (5Hz) + continuous buzzer (10s)
    - high: ORANGE breathing effect (1Hz) + 3 sharp beeps (5s)
    - medium: Slow BLUE fade (0.5Hz) - gentle (5s, no buzzer)
    - low: Soft GREEN glow - steady (2s, no buzzer)
    """

    try:
        # Get client information
        client_ip = http_request.client.host
        user_agent = http_request.headers.get("user-agent")

        # Log incoming request
        structured_logger.log_request(
            method="POST",
            endpoint="/api/v1/hardware-alert",
            payload=request.dict(),
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Queue the alert for processing (always use critical severity)
        # Original severity from request: request.severity (kept for logging)
        alert_id = await hardware_controller.queue_alert(
            severity="critical",  # Always use critical severity
            alert_type=request.alert_type,
            device_id=request.sensor_data.device_id,
        )

        # Log alert queued (log the original requested severity for tracking)
        queue_size = hardware_controller.alert_queue.qsize()
        structured_logger.log_alert_queued(alert_id, request.severity, queue_size)

        return AlertResponse(
            status="success",
            message="Alert received and queued for processing",
            alert_id=alert_id,
            queued=True,
        )

    except Exception as e:
        # Log error
        structured_logger.log_error(
            error_type="alert_processing_error",
            error_message=str(e),
            context={
                "severity": request.severity,
                "alert_type": request.alert_type,
                "device_id": request.sensor_data.device_id,
            },
        )

        raise HTTPException(
            status_code=500, detail=f"Failed to process alert: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""

    structured_logger.log_error(
        error_type="unhandled_exception",
        error_message=str(exc),
        context={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat(),
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to False for production
        log_level="info",
    )
