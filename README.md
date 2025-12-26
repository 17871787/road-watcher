# Road Watcher

Vehicle detection system for blind corners. Uses a Raspberry Pi camera to detect approaching vehicles and triggers an LED alert.

## Hardware Required

- Raspberry Pi 4 (or 3B+, Zero 2 W)
- Pi Camera Module or USB webcam
- LED + 330 ohm resistor
- Weatherproof enclosure (for outdoor mounting)

## Wiring

```
GPIO 17 ---[330 ohm]--- LED (+) --- LED (-) --- GND
```

## Installation

```bash
# Clone the repo
git clone https://github.com/17871787/road-watcher.git
cd road-watcher

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config.json` to tune the detection:

| Setting | Description | Default |
|---------|-------------|---------|
| `camera_index` | Camera device index | 0 |
| `led_pin` | GPIO pin for LED | 17 |
| `min_contour_area` | Minimum motion size to trigger | 5000 |
| `detection_cooldown` | Seconds between alerts | 2.0 |
| `alert_duration` | How long LED stays on | 5.0 |
| `roi` | Region of interest `[x, y, w, h]` | null (full frame) |
| `save_detections` | Save detection images | false |

## Usage

```bash
# Run the detector
python detector.py

# Test LED only
python led_controller.py
```

## Running on Boot

Create a systemd service:

```bash
sudo nano /etc/systemd/system/road-watcher.service
```

```ini
[Unit]
Description=Road Watcher Vehicle Detection
After=multi-user.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/road-watcher
ExecStart=/home/pi/road-watcher/venv/bin/python detector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable road-watcher
sudo systemctl start road-watcher
```

## Mounting Tips

1. Mount camera with clear view of approaching traffic
2. Angle slightly down to reduce sky/tree motion false positives
3. Use `roi` config to focus on just the road area
4. Start with higher `min_contour_area` and reduce if missing detections
