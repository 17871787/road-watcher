#!/usr/bin/env python3
"""
Road Watcher - Vehicle Detection System
Detects vehicles approaching a blind corner and triggers an LED alert.
"""

import cv2
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from led_controller import LEDController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VehicleDetector:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.led = LEDController(self.config["led_pin"])
        self.camera = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.config["bg_history"],
            varThreshold=self.config["var_threshold"],
            detectShadows=True
        )
        self.last_detection_time = 0
        self.detection_log = []

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        else:
            logger.warning(f"Config not found, using defaults")
            return self._default_config()

    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            "camera_index": 0,
            "frame_width": 640,
            "frame_height": 480,
            "fps": 30,
            "led_pin": 17,
            "min_contour_area": 5000,
            "detection_cooldown": 2.0,
            "alert_duration": 5.0,
            "bg_history": 500,
            "var_threshold": 50,
            "roi": None,  # Region of interest: [x, y, width, height]
            "save_detections": False,
            "detections_dir": "detections"
        }

    def start_camera(self):
        """Initialize the camera."""
        self.camera = cv2.VideoCapture(self.config["camera_index"])
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["frame_width"])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["frame_height"])
        self.camera.set(cv2.CAP_PROP_FPS, self.config["fps"])

        if not self.camera.isOpened():
            raise RuntimeError("Failed to open camera")

        logger.info("Camera started successfully")
        # Allow camera to warm up
        time.sleep(2)

    def stop_camera(self):
        """Release the camera."""
        if self.camera:
            self.camera.release()
            logger.info("Camera stopped")

    def detect_motion(self, frame) -> tuple:
        """
        Detect motion in frame using background subtraction.
        Returns (detected: bool, contours: list)
        """
        # Apply region of interest if configured
        roi = self.config.get("roi")
        if roi:
            x, y, w, h = roi
            frame = frame[y:y+h, x:x+w]

        # Convert to grayscale and blur
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)

        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(blurred)

        # Remove shadows (marked as gray in MOG2)
        _, fg_mask = cv2.threshold(fg_mask, 250, 255, cv2.THRESH_BINARY)

        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter by minimum area
        significant_contours = [
            c for c in contours
            if cv2.contourArea(c) > self.config["min_contour_area"]
        ]

        return len(significant_contours) > 0, significant_contours

    def handle_detection(self, frame, contours):
        """Handle a positive detection."""
        current_time = time.time()

        # Check cooldown
        if current_time - self.last_detection_time < self.config["detection_cooldown"]:
            return

        self.last_detection_time = current_time
        timestamp = datetime.now().isoformat()

        logger.info(f"Vehicle detected at {timestamp}")

        # Turn on LED alert
        self.led.alert(duration=self.config["alert_duration"])

        # Log detection
        self.detection_log.append({
            "timestamp": timestamp,
            "contour_count": len(contours)
        })

        # Optionally save detection image
        if self.config.get("save_detections"):
            self._save_detection(frame, contours, timestamp)

    def _save_detection(self, frame, contours, timestamp):
        """Save detection image with bounding boxes."""
        detections_dir = Path(self.config["detections_dir"])
        detections_dir.mkdir(exist_ok=True)

        # Draw bounding boxes
        frame_copy = frame.copy()
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame_copy, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # Save image
        filename = detections_dir / f"detection_{timestamp.replace(':', '-')}.jpg"
        cv2.imwrite(str(filename), frame_copy)
        logger.info(f"Saved detection image: {filename}")

    def run(self):
        """Main detection loop."""
        logger.info("Starting vehicle detection...")
        self.start_camera()

        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to read frame")
                    continue

                detected, contours = self.detect_motion(frame)

                if detected:
                    self.handle_detection(frame, contours)

                # Small delay to reduce CPU usage
                time.sleep(0.033)  # ~30 FPS

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.stop_camera()
            self.led.cleanup()


def main():
    detector = VehicleDetector()
    detector.run()


if __name__ == "__main__":
    main()
