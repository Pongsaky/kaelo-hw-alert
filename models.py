from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


class SensorData(BaseModel):
    device_id: str = Field(..., description="Device identifier")
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., description="Humidity percentage")
    dust: float = Field(..., description="Dust level")
    flame: float = Field(..., description="Flame detection level")
    light: float = Field(..., description="Light intensity")
    vibration: float = Field(..., description="Vibration level")
    gas: float = Field(..., description="Gas level")
    timestamp: datetime = Field(..., description="Sensor reading timestamp")


class HardwareAlertRequest(BaseModel):
    sensor_data: SensorData
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Alert severity level")
    alert_type: str = Field(..., description="Type of alert (e.g., overheat, gas_leak)")


class AlertResponse(BaseModel):
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    alert_id: str = Field(..., description="Unique alert identifier")
    queued: bool = Field(..., description="Whether alert was queued for processing")
