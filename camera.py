#!/usr/bin/env python3
"""
Camera abstraction for Road Watcher.
Supports Pi Camera Module 3 (picamera2) and USB/webcam (OpenCV).
"""

import logging
import time

logger = logging.getLogger(__name__)

# Try picamera2 first (for Pi Camera Module 3)
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logger.info("picamera2 not available")

# Fallback to OpenCV
import cv2


class PiCamera:
    """Pi Camera Module 3 using picamera2."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = None

    def start(self):
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"},
            controls={"FrameRate": self.fps}
        )
        self.camera.configure(config)
        self.camera.start()
        logger.info(f"Pi Camera started at {self.width}x{self.height} @ {self.fps}fps")
        time.sleep(2)  # Warm up

    def read(self):
        """Returns (success, frame) like OpenCV."""
        if self.camera is None:
            return False, None
        frame = self.camera.capture_array()
        # Convert RGB to BGR for OpenCV compatibility
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return True, frame

    def release(self):
        if self.camera:
            self.camera.stop()
            self.camera.close()
            logger.info("Pi Camera stopped")


class USBCamera:
    """USB/Webcam using OpenCV."""

    def __init__(self, index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.camera = None

    def start(self):
        self.camera = cv2.VideoCapture(self.index)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)

        if not self.camera.isOpened():
            raise RuntimeError("Failed to open USB camera")

        logger.info(f"USB Camera started at {self.width}x{self.height}")
        time.sleep(2)

    def read(self):
        return self.camera.read()

    def release(self):
        if self.camera:
            self.camera.release()
            logger.info("USB Camera stopped")


def create_camera(config: dict):
    """
    Factory function to create the appropriate camera.

    Set config["camera_type"] to "pi" or "usb".
    Defaults to "pi" if picamera2 is available, otherwise "usb".
    """
    camera_type = config.get("camera_type")

    # Auto-detect if not specified
    if camera_type is None:
        camera_type = "pi" if PICAMERA2_AVAILABLE else "usb"
        logger.info(f"Auto-detected camera type: {camera_type}")

    width = config.get("frame_width", 640)
    height = config.get("frame_height", 480)
    fps = config.get("fps", 30)

    if camera_type == "pi":
        if not PICAMERA2_AVAILABLE:
            raise RuntimeError("picamera2 not installed. Run: sudo apt install python3-picamera2")
        return PiCamera(width=width, height=height, fps=fps)
    else:
        return USBCamera(
            index=config.get("camera_index", 0),
            width=width,
            height=height,
            fps=fps
        )
