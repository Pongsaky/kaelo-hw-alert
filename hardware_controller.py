import asyncio
import logging
from typing import Literal
from datetime import datetime
import uuid

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available. Running in simulation mode.")


class HardwareController:
    """Controls LED and buzzer hardware with queue system to prevent conflicts"""
    
    def __init__(self, led_pin: int = 18, buzzer_pin: int = 24):
        self.led_pin = led_pin
        self.buzzer_pin = buzzer_pin
        self.is_active = False
        self.alert_queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)
        
        if GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.led_pin, GPIO.OUT)
            GPIO.setup(self.buzzer_pin, GPIO.OUT)
            GPIO.output(self.led_pin, GPIO.LOW)
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            self.logger.info(f"GPIO initialized - LED: {led_pin}, Buzzer: {buzzer_pin}")
        else:
            self.logger.info("Running in simulation mode - no actual GPIO control")
    
    async def start_queue_processor(self):
        """Start the alert queue processor"""
        asyncio.create_task(self._process_alert_queue())
        self.logger.info("Alert queue processor started")
    
    async def _process_alert_queue(self):
        """Process alerts from queue one by one"""
        while True:
            try:
                alert_data = await self.alert_queue.get()
                await self._execute_alert(alert_data)
                self.alert_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing alert: {e}")
    
    async def queue_alert(self, severity: Literal["critical", "high", "medium", "low"], 
                         alert_type: str, device_id: str) -> str:
        """Queue an alert for processing"""
        alert_id = str(uuid.uuid4())[:8]
        alert_data = {
            "alert_id": alert_id,
            "severity": severity,
            "alert_type": alert_type,
            "device_id": device_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.alert_queue.put(alert_data)
        queue_size = self.alert_queue.qsize()
        
        self.logger.info(f"Alert queued - ID: {alert_id}, Severity: {severity}, Queue size: {queue_size}")
        return alert_id
    
    async def _execute_alert(self, alert_data: dict):
        """Execute the actual hardware alert"""
        alert_id = alert_data["alert_id"]
        severity = alert_data["severity"]
        
        self.logger.info(f"Executing alert {alert_id} - Severity: {severity}")
        self.is_active = True
        
        try:
            if severity == "critical":
                await self._critical_alert()
            elif severity == "high":
                await self._high_alert()
            elif severity == "medium":
                await self._medium_alert()
            elif severity == "low":
                await self._low_alert()
        except Exception as e:
            self.logger.error(f"Error executing alert {alert_id}: {e}")
        finally:
            self.is_active = False
            self.logger.info(f"Alert {alert_id} completed")
    
    async def _critical_alert(self):
        """Critical: Fast LED blink + continuous buzzer for 10 seconds"""
        duration = 10.0
        blink_interval = 0.1
        
        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
        
        end_time = asyncio.get_event_loop().time() + duration
        
        while asyncio.get_event_loop().time() < end_time:
            if GPIO_AVAILABLE:
                GPIO.output(self.led_pin, GPIO.HIGH)
            await asyncio.sleep(blink_interval)
            
            if GPIO_AVAILABLE:
                GPIO.output(self.led_pin, GPIO.LOW)
            await asyncio.sleep(blink_interval)
        
        if GPIO_AVAILABLE:
            GPIO.output(self.buzzer_pin, GPIO.LOW)
            GPIO.output(self.led_pin, GPIO.LOW)
    
    async def _high_alert(self):
        """High: Medium LED blink + 3 short buzzer beeps"""
        blink_interval = 0.3
        
        # 3 buzzer beeps
        for _ in range(3):
            if GPIO_AVAILABLE:
                GPIO.output(self.buzzer_pin, GPIO.HIGH)
            await asyncio.sleep(0.2)
            
            if GPIO_AVAILABLE:
                GPIO.output(self.buzzer_pin, GPIO.LOW)
            await asyncio.sleep(0.3)
        
        # LED blink for 5 seconds
        end_time = asyncio.get_event_loop().time() + 5.0
        
        while asyncio.get_event_loop().time() < end_time:
            if GPIO_AVAILABLE:
                GPIO.output(self.led_pin, GPIO.HIGH)
            await asyncio.sleep(blink_interval)
            
            if GPIO_AVAILABLE:
                GPIO.output(self.led_pin, GPIO.LOW)
            await asyncio.sleep(blink_interval)
    
    async def _medium_alert(self):
        """Medium: Slow LED blink for 5 seconds (no buzzer)"""
        duration = 5.0
        blink_interval = 0.5
        
        end_time = asyncio.get_event_loop().time() + duration
        
        while asyncio.get_event_loop().time() < end_time:
            if GPIO_AVAILABLE:
                GPIO.output(self.led_pin, GPIO.HIGH)
            await asyncio.sleep(blink_interval)
            
            if GPIO_AVAILABLE:
                GPIO.output(self.led_pin, GPIO.LOW)
            await asyncio.sleep(blink_interval)
    
    async def _low_alert(self):
        """Low: LED on for 2 seconds (no buzzer)"""
        if GPIO_AVAILABLE:
            GPIO.output(self.led_pin, GPIO.HIGH)
        
        await asyncio.sleep(2.0)
        
        if GPIO_AVAILABLE:
            GPIO.output(self.led_pin, GPIO.LOW)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        if GPIO_AVAILABLE:
            GPIO.cleanup()
            self.logger.info("GPIO cleanup completed")
