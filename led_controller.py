#!/usr/bin/env python3
"""
LED Controller for Road Watcher
Handles GPIO output for visual alerts.
"""

import time
import threading
import logging

logger = logging.getLogger(__name__)

# Try to import RPi.GPIO, fall back to mock for development
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available - running in simulation mode")


class MockGPIO:
    """Mock GPIO for development/testing on non-Pi systems."""
    BCM = "BCM"
    OUT = "OUT"
    HIGH = 1
    LOW = 0

    @staticmethod
    def setmode(mode):
        logger.debug(f"[MOCK] GPIO mode set to {mode}")

    @staticmethod
    def setup(pin, mode):
        logger.debug(f"[MOCK] GPIO pin {pin} set to {mode}")

    @staticmethod
    def output(pin, state):
        state_str = "HIGH" if state else "LOW"
        logger.debug(f"[MOCK] GPIO pin {pin} -> {state_str}")

    @staticmethod
    def cleanup():
        logger.debug("[MOCK] GPIO cleanup")


class LEDController:
    """Controls an LED connected to a GPIO pin."""

    def __init__(self, pin: int = 17):
        self.pin = pin
        self.gpio = GPIO if GPIO_AVAILABLE else MockGPIO()
        self._alert_thread = None
        self._stop_alert = threading.Event()

        # Initialize GPIO
        self.gpio.setmode(self.gpio.BCM)
        self.gpio.setup(self.pin, self.gpio.OUT)
        self.off()

        logger.info(f"LED controller initialized on GPIO {pin}")

    def on(self):
        """Turn LED on."""
        self.gpio.output(self.pin, self.gpio.HIGH)

    def off(self):
        """Turn LED off."""
        self.gpio.output(self.pin, self.gpio.LOW)

    def blink(self, times: int = 3, interval: float = 0.3):
        """Blink the LED."""
        for _ in range(times):
            if self._stop_alert.is_set():
                break
            self.on()
            time.sleep(interval)
            self.off()
            time.sleep(interval)

    def alert(self, duration: float = 5.0, pattern: str = "solid"):
        """
        Trigger an alert for the specified duration.

        Args:
            duration: How long to keep the alert active (seconds)
            pattern: "solid" for constant on, "blink" for blinking
        """
        # Stop any existing alert
        self._stop_alert.set()
        if self._alert_thread and self._alert_thread.is_alive():
            self._alert_thread.join(timeout=1.0)

        self._stop_alert.clear()

        def _run_alert():
            start_time = time.time()
            if pattern == "blink":
                while time.time() - start_time < duration:
                    if self._stop_alert.is_set():
                        break
                    self.blink(times=1, interval=0.2)
            else:  # solid
                self.on()
                while time.time() - start_time < duration:
                    if self._stop_alert.is_set():
                        break
                    time.sleep(0.1)
            self.off()

        self._alert_thread = threading.Thread(target=_run_alert, daemon=True)
        self._alert_thread.start()

    def stop_alert(self):
        """Stop the current alert."""
        self._stop_alert.set()
        self.off()

    def cleanup(self):
        """Clean up GPIO resources."""
        self.stop_alert()
        if self._alert_thread:
            self._alert_thread.join(timeout=1.0)
        self.gpio.cleanup()
        logger.info("LED controller cleaned up")


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    led = LEDController(pin=17)

    print("Testing LED - solid for 2 seconds")
    led.alert(duration=2.0, pattern="solid")
    time.sleep(3)

    print("Testing LED - blink for 3 seconds")
    led.alert(duration=3.0, pattern="blink")
    time.sleep(4)

    led.cleanup()
    print("Test complete")
