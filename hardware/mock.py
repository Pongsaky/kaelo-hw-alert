#!/usr/bin/env python3
import time, math, threading, signal, sys, logging
import gpiod

# --------- Config ---------
chip_name: str = "gpiochip0"

red_pin: int = 17
green_pin: int = 27
blue_pin: int = 22
buzzer_pin: int = 24

led_pwm_freq: int = 500  # Hz
common_anode: bool = False  # True if KY-009 common pin tied to 3.3V
# --------------------------

RUNNING = True

# ---- Setup logger ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("RGBBuzzer")


def clamp01(x):
    return max(0.0, min(1.0, float(x)))


def logical_levels():
    if common_anode:
        return 0, 1  # low=on, high=off
    else:
        return 1, 0  # high=on, low=off


# ---- GPIO wrapper (v1/v2) ----
class GPIO:
    def __init__(self, chip_name):
        self.v2 = hasattr(gpiod, "LineSettings")
        self.chip = gpiod.Chip(chip_name)
        log.info("Using libgpiod %s API", "v2" if self.v2 else "v1")

        if self.v2:
            self.requests = {}  # pin -> LinesRequest
        else:
            self.lines = {}  # pin -> Line

    def request_output(self, pin, initial=0, consumer="app"):
        log.info("Requesting pin %d as output (initial=%d)", pin, initial)
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

    def set_level(self, pin, value: int):
        v = 1 if value else 0
        if self.v2:
            self.requests[pin].set_values({pin: v})
        else:
            self.lines[pin].set_value(v)

    def close(self):
        log.info("Releasing GPIO resources")
        try:
            if self.v2:
                for req in self.requests.values():
                    req.release()
            else:
                for line in self.lines.values():
                    line.release()
        finally:
            self.chip.close()


# ---- Software PWM ----
class SoftPWM:
    def __init__(self, gpio: GPIO, pin: int, freq_hz: int, initial: float, anode: bool):
        self.gpio = gpio
        self.pin = pin
        self.period = 1.0 / max(1, int(freq_hz))
        self._duty = clamp01(initial)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self.on_level, self.off_level = (0, 1) if anode else (1, 0)

    def start(self):
        log.info("Starting PWM on pin %d", self.pin)
        self._thr.start()

    def stop(self):
        log.info("Stopping PWM on pin %d", self.pin)
        self._stop.set()
        self._thr.join(timeout=1.0)
        self.gpio.set_level(self.pin, self.off_level)

    def set_duty(self, duty):
        with self._lock:
            self._duty = clamp01(duty)

    def _run(self):
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


# ---- Helpers ----
def smooth_color(t):
    r = 0.5 + 0.5 * math.sin(2 * math.pi * (t / 3 + 0 / 3))
    g = 0.5 + 0.5 * math.sin(2 * math.pi * (t / 3 + 1 / 3))
    b = 0.5 + 0.5 * math.sin(2 * math.pi * (t / 3 + 2 / 3))
    return r, g, b


def set_rgb(pwm_r, pwm_g, pwm_b, r, g, b):
    log.debug("Setting RGB duty: R=%.2f G=%.2f B=%.2f", r, g, b)
    pwm_r.set_duty(r)
    pwm_g.set_duty(g)
    pwm_b.set_duty(b)


def beep(gpio: GPIO, pin: int, on_sec=0.2, off_sec=0.2, times=2):
    log.info("Beeping %d times (%.2fs on / %.2fs off)", times, on_sec, off_sec)
    for _ in range(times):
        gpio.set_level(pin, 1)
        time.sleep(on_sec)
        gpio.set_level(pin, 0)
        time.sleep(off_sec)


# ---- Main ----
def main():
    global RUNNING

    def handle_sig(sig, frame):
        global RUNNING
        log.warning("Signal %s received, stopping...", sig)
        RUNNING = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    on_level, off_level = logical_levels()
    gpio = GPIO(chip_name)

    try:
        # Request outputs
        gpio.request_output(red_pin, initial=off_level, consumer="rgb-red")
        gpio.request_output(green_pin, initial=off_level, consumer="rgb-green")
        gpio.request_output(blue_pin, initial=off_level, consumer="rgb-blue")
        gpio.request_output(buzzer_pin, initial=0, consumer="buzzer")

        # Start PWM
        pwm_r = SoftPWM(gpio, red_pin, led_pwm_freq, 0.0, common_anode)
        pwm_g = SoftPWM(gpio, green_pin, led_pwm_freq, 0.0, common_anode)
        pwm_b = SoftPWM(gpio, blue_pin, led_pwm_freq, 0.0, common_anode)
        pwm_r.start()
        pwm_g.start()
        pwm_b.start()

        # Solid color demo
        log.info("Cycling solid colors...")
        for r, g, b in [
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 1, 0),
            (0, 1, 1),
            (1, 0, 1),
            (1, 1, 1),
            (0, 0, 0),
        ]:
            set_rgb(pwm_r, pwm_g, pwm_b, r, g, b)
            time.sleep(0.6)

        beep(gpio, buzzer_pin, 0.15, 0.15, 3)

        # Smooth rainbow
        log.info("Rainbow cycle for 10s...")
        t0 = time.time()
        while RUNNING and time.time() - t0 < 10:
            r, g, b = smooth_color(time.time() - t0)
            set_rgb(pwm_r, pwm_g, pwm_b, r, g, b)
            time.sleep(0.02)

        # End
        set_rgb(pwm_r, pwm_g, pwm_b, 0, 0, 0)
        beep(gpio, buzzer_pin, 0.1, 0.1, 2)

        pwm_r.stop()
        pwm_g.stop()
        pwm_b.stop()
    finally:
        gpio.close()
        log.info("Clean exit.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("Error: %s", e)
        sys.exit(1)
