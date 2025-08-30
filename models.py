from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional


class AccelerationData(BaseModel):
    x: float = Field(..., description="X-axis acceleration")
    y: float = Field(..., description="Y-axis acceleration")
    z: float = Field(..., description="Z-axis acceleration")


class GyroscopeData(BaseModel):
    x: float = Field(..., description="X-axis gyroscope")
    y: float = Field(..., description="Y-axis gyroscope")
    z: float = Field(..., description="Z-axis gyroscope")


class SensorData(BaseModel):
    device_id: str = Field(..., description="Device identifier")
    temperature_dht: float = Field(
        ..., description="Temperature from DHT sensor in Celsius"
    )
    humidity: float = Field(..., description="Humidity percentage")
    gas_quality: str = Field(..., description="Gas quality level: good, moderate, poor")
    acceleration: AccelerationData = Field(..., description="Acceleration data")
    gyroscope: GyroscopeData = Field(..., description="Gyroscope data")
    flame_detected: bool = Field(..., description="Flame detection status")
    timestamp: datetime = Field(..., description="Sensor reading timestamp")

    # deprecated field but still received
    temperature_mpu: Optional[float] = Field(
        None, description="Temperature from MPU sensor (deprecated)"
    )


class HardwareAlertRequest(BaseModel):
    sensor_data: SensorData
    severity: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Alert severity level"
    )
    alert_type: str = Field(..., description="Type of alert (e.g., overheat, gas_leak)")


class AlertResponse(BaseModel):
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    alert_id: str = Field(..., description="Unique alert identifier")
    queued: bool = Field(..., description="Whether alert was queued for processing")
