import asyncio
import logging
import threading
import time
import math
from typing import Literal
from datetime import datetime
import uuid

try:
    import gpiod

    GPIOD_AVAILABLE = True
except ImportError:
    GPIOD_AVAILABLE = False
    logging.warning("gpiod not available. Running in simulation mode.")


def clamp01(x):
    """Clamp value between 0.0 and 1.0"""
    return max(0.0, min(1.0, float(x)))


class GPIO:
    """Enhanced GPIO wrapper supporting both gpiod v1/v2 APIs"""

    def __init__(self, chip_name: str = "gpiochip0"):
        self.v2 = hasattr(gpiod, "LineSettings")
        self.chip = gpiod.Chip(chip_name)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Using libgpiod %s API", "v2" if self.v2 else "v1")

        if self.v2:
            self.requests = {}  # pin -> LinesRequest
        else:
            self.lines = {}  # pin -> Line

    def request_output(self, pin: int, initial: int = 0, consumer: str = "app"):
        """Request a pin as output with initial value"""
        self.logger.info("Requesting pin %d as output (initial=%d)", pin, initial)
        if self.v2:
            ls = gpiod.LineSettings()
            ls.direction = gpiod.LineDirection.OUTPUT
            ls.output_value = int(initial)
            req = self.chip.request_lines(consumer=consumer, config={pin: ls})
            self.requests[pin] = req
        else:
            line = self.chip.get_line(pin)
            line.request(
                consumer=consumer, type=gpiod.LINE_REQ_DIR_OUT, default_val=int(initial)
            )
            self.lines[pin] = line

    def set_level(self, pin: int, value: int):
        """Set pin level (0 or 1)"""
        v = 1 if value else 0
        if self.v2:
            self.requests[pin].set_values({pin: v})
        else:
            self.lines[pin].set_value(v)

    def close(self):
        """Release all GPIO resources"""
        self.logger.info("Releasing GPIO resources")
        try:
            if self.v2:
                for req in self.requests.values():
                    req.release()
            else:
                for line in self.lines.values():
                    line.release()
        finally:
            self.chip.close()


class SoftPWM:
    """Software PWM implementation for smooth LED control"""

    def __init__(
        self,
        gpio: GPIO,
        pin: int,
        freq_hz: int,
        initial: float = 0.0,
        common_anode: bool = False,
    ):
        self.gpio = gpio
        self.pin = pin
        self.period = 1.0 / max(1, int(freq_hz))
        self._duty = clamp01(initial)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self.on_level, self.off_level = (0, 1) if common_anode else (1, 0)
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start PWM thread"""
        self.logger.info("Starting PWM on pin %d", self.pin)
        self._thr.start()

    def stop(self):
        """Stop PWM thread"""
        self.logger.info("Stopping PWM on pin %d", self.pin)
        self._stop.set()
        self._thr.join(timeout=1.0)
        self.gpio.set_level(self.pin, self.off_level)

    def set_duty(self, duty: float):
        """Set PWM duty cycle (0.0 to 1.0)"""
        with self._lock:
            self._duty = clamp01(duty)

    def _run(self):
        """PWM thread main loop"""
        while not self._stop.is_set():
            with self._lock:
                duty = self._duty
            if duty <= 0.0:
                self.gpio.set_level(self.pin, self.off_level)
                time.sleep(self.period)
                continue
            if duty >= 1.0:
                self.gpio.set_level(self.pin, self.on_level)
                time.sleep(self.period)
                continue
            self.gpio.set_level(self.pin, self.on_level)
            time.sleep(self.period * duty)
            self.gpio.set_level(self.pin, self.off_level)
            time.sleep(self.period * (1 - duty))


class HardwareController:
    """Enhanced RGB LED and buzzer hardware controller with PWM support"""

    def __init__(
        self,
        red_pin: int = 17,
        green_pin: int = 27,
        blue_pin: int = 22,
        buzzer_pin: int = 24,
        pwm_freq: int = 500,
        common_anode: bool = False,
        chip_name: str = "gpiochip0",
    ):
        self.red_pin = red_pin
        self.green_pin = green_pin
        self.blue_pin = blue_pin
        self.buzzer_pin = buzzer_pin
        self.pwm_freq = pwm_freq
        self.common_anode = common_anode
        self.is_active = False
        self.alert_queue = asyncio.Queue()
        self.logger = logging.getLogger(__name__)

        # Determine logical levels for LEDs
        self.led_on_level, self.led_off_level = (0, 1) if common_anode else (1, 0)

        if GPIOD_AVAILABLE:
            self.gpio = GPIO(chip_name)

            # Initialize GPIO pins
            self.gpio.request_output(
                red_pin, initial=self.led_off_level, consumer="rgb-red"
            )
            self.gpio.request_output(
                green_pin, initial=self.led_off_level, consumer="rgb-green"
            )
            self.gpio.request_output(
                blue_pin, initial=self.led_off_level, consumer="rgb-blue"
            )
            self.gpio.request_output(buzzer_pin, initial=0, consumer="buzzer")

            # Initialize PWM for smooth LED control
            self.pwm_r = SoftPWM(self.gpio, red_pin, pwm_freq, 0.0, common_anode)
            self.pwm_g = SoftPWM(self.gpio, green_pin, pwm_freq, 0.0, common_anode)
            self.pwm_b = SoftPWM(self.gpio, blue_pin, pwm_freq, 0.0, common_anode)

            # Start PWM threads
            self.pwm_r.start()
            self.pwm_g.start()
            self.pwm_b.start()

            self.logger.info(
                f"GPIO initialized - RGB: R={red_pin}, G={green_pin}, B={blue_pin}, Buzzer: {buzzer_pin}"
            )
            self.logger.info(
                f"PWM frequency: {pwm_freq}Hz, Common anode: {common_anode}"
            )
        else:
            self.gpio = None
            self.pwm_r = None
            self.pwm_g = None
            self.pwm_b = None
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

    async def queue_alert(
        self,
        severity: Literal["critical", "high", "medium", "low"],
        alert_type: str,
        device_id: str,
    ) -> str:
        """Queue an alert for processing"""
        alert_id = str(uuid.uuid4())[:8]
        alert_data = {
            "alert_id": alert_id,
            "severity": severity,
            "alert_type": alert_type,
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
        }

        await self.alert_queue.put(alert_data)
        queue_size = self.alert_queue.qsize()

        self.logger.info(
            f"Alert queued - ID: {alert_id}, Severity: {severity}, Queue size: {queue_size}"
        )
        return alert_id

    def set_rgb_color(self, r: float, g: float, b: float):
        """Set RGB LED color with PWM (0.0 to 1.0 for each channel)"""
        if GPIOD_AVAILABLE and self.pwm_r and self.pwm_g and self.pwm_b:
            self.pwm_r.set_duty(clamp01(r))
            self.pwm_g.set_duty(clamp01(g))
            self.pwm_b.set_duty(clamp01(b))
            self.logger.debug(f"Setting RGB PWM: R={r:.2f} G={g:.2f} B={b:.2f}")

    def rgb_off(self):
        """Turn off all RGB channels"""
        self.set_rgb_color(0.0, 0.0, 0.0)

    def beep(self, duration: float = 0.2, pause: float = 0.2, times: int = 1):
        """Enhanced beep function with precise timing"""
        if not GPIOD_AVAILABLE:
            return

        self.logger.info(
            f"Beeping {times} times ({duration:.2f}s on / {pause:.2f}s off)"
        )
        for i in range(times):
            self.gpio.set_level(self.buzzer_pin, 1)
            time.sleep(duration)
            self.gpio.set_level(self.buzzer_pin, 0)
            if i < times - 1:  # Don't pause after last beep
                time.sleep(pause)

    async def async_beep(
        self, duration: float = 0.2, pause: float = 0.2, times: int = 1
    ):
        """Async version of beep function"""
        if not GPIOD_AVAILABLE:
            return

        self.logger.info(
            f"Async beeping {times} times ({duration:.2f}s on / {pause:.2f}s off)"
        )
        for i in range(times):
            self.gpio.set_level(self.buzzer_pin, 1)
            await asyncio.sleep(duration)
            self.gpio.set_level(self.buzzer_pin, 0)
            if i < times - 1:  # Don't pause after last beep
                await asyncio.sleep(pause)

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
        """Critical: Fast red LED pulsing + continuous buzzer for 10 seconds"""
        duration = 10.0
        pulse_freq = 5.0  # 5Hz pulsing

        # Start continuous buzzer
        if GPIOD_AVAILABLE:
            self.gpio.set_level(self.buzzer_pin, 1)

        end_time = asyncio.get_event_loop().time() + duration
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() < end_time:
            # Pulsing red effect
            t = asyncio.get_event_loop().time() - start_time
            intensity = 0.5 + 0.5 * math.sin(2 * math.pi * pulse_freq * t)
            self.set_rgb_color(intensity, 0.0, 0.0)
            await asyncio.sleep(0.02)  # 50Hz update rate

        # Stop buzzer and turn off LED
        if GPIOD_AVAILABLE:
            self.gpio.set_level(self.buzzer_pin, 0)
        self.rgb_off()

    async def _high_alert(self):
        """High: Orange breathing effect + 3 buzzer beeps"""
        # 3 sharp beeps first
        await self.async_beep(duration=0.15, pause=0.15, times=3)
        await asyncio.sleep(0.5)

        # Orange breathing effect for 5 seconds
        duration = 5.0
        breathe_freq = 1.0  # 1Hz breathing
        end_time = asyncio.get_event_loop().time() + duration
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() < end_time:
            t = asyncio.get_event_loop().time() - start_time
            # Breathing intensity (0.2 to 1.0)
            intensity = 0.2 + 0.8 * (
                0.5 + 0.5 * math.sin(2 * math.pi * breathe_freq * t)
            )
            self.set_rgb_color(intensity, intensity * 0.5, 0.0)  # Orange
            await asyncio.sleep(0.02)

        self.rgb_off()

    async def _medium_alert(self):
        """Medium: Slow blue fade for 5 seconds (no buzzer)"""
        duration = 5.0
        fade_freq = 0.5  # 0.5Hz slow fade
        end_time = asyncio.get_event_loop().time() + duration
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() < end_time:
            t = asyncio.get_event_loop().time() - start_time
            # Gentle fade (0.1 to 0.8)
            intensity = 0.1 + 0.7 * (0.5 + 0.5 * math.sin(2 * math.pi * fade_freq * t))
            self.set_rgb_color(0.0, 0.0, intensity)  # Blue
            await asyncio.sleep(0.05)

        self.rgb_off()

    async def _low_alert(self):
        """Low: Gentle green glow for 2 seconds (no buzzer)"""
        # Gentle green glow (not full brightness)
        self.set_rgb_color(0.0, 0.6, 0.0)  # Soft green
        await asyncio.sleep(2.0)
        self.rgb_off()

    def cleanup(self):
        """Clean up GPIO resources"""
        if GPIOD_AVAILABLE and self.gpio:
            try:
                # Turn off all outputs
                self.rgb_off()
                self.gpio.set_level(self.buzzer_pin, 0)

                # Stop PWM threads
                if self.pwm_r:
                    self.pwm_r.stop()
                if self.pwm_g:
                    self.pwm_g.stop()
                if self.pwm_b:
                    self.pwm_b.stop()

                # Close GPIO
                self.gpio.close()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")

            self.logger.info("GPIO cleanup completed")
