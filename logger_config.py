import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """Industry standard structured JSON logger"""
    
    def __init__(self, name: str = "hardware_alert_api"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create console handler with JSON formatter
        console_handler = logging.StreamHandler()
        
        # Custom JSON formatter
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        
        console_handler.setFormatter(json_formatter)
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def log_request(self, method: str, endpoint: str, payload: dict, 
                   client_ip: str, user_agent: str = None):
        """Log incoming HTTP request with structured format"""
        log_data = {
            "event_type": "http_request",
            "method": method,
            "endpoint": endpoint,
            "client_ip": client_ip,
            "payload_size": len(str(payload)),
            "device_id": payload.get("sensor_data", {}).get("device_id"),
            "severity": payload.get("severity"),
            "alert_type": payload.get("alert_type"),
            "timestamp": datetime.now().isoformat()
        }
        
        if user_agent:
            log_data["user_agent"] = user_agent
        
        self.logger.info("Incoming hardware alert request", extra=log_data)
    
    def log_alert_queued(self, alert_id: str, severity: str, queue_size: int):
        """Log when alert is queued for processing"""
        log_data = {
            "event_type": "alert_queued",
            "alert_id": alert_id,
            "severity": severity,
            "queue_size": queue_size,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info("Alert queued for processing", extra=log_data)
    
    def log_alert_processing(self, alert_id: str, severity: str, status: str):
        """Log alert processing status"""
        log_data = {
            "event_type": "alert_processing",
            "alert_id": alert_id,
            "severity": severity,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info("Alert processing update", extra=log_data)
    
    def log_error(self, error_type: str, error_message: str, context: dict = None):
        """Log errors with structured format"""
        log_data = {
            "event_type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        if context:
            log_data["context"] = context
        
        self.logger.error("Application error occurred", extra=log_data)
