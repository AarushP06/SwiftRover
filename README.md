# SwiftRover

IoT Smart Mobile Robot (Raspberry Pi) — Complete IoT system with telemetry, autonomous navigation, and **Flask web application** for remote monitoring and control.

> Organized codebase with modular structure: hardware interfaces, server modules, telemetry utilities, Flask web app, and database sync.

---

## Project Information

### Team Members

- **Mir Faiyazur Rahman** — Hardware + Software
- **Aarush Patel** — Software + Testing

### Course Info

- **Course:** 420-N55: IoT - Design and Prototyping of Connected Devices
- **Institution:** Champlain College Saint-Lambert
- **Semester:** Fall 2025

### Links

| Resource              | Link                                       |
| --------------------- | ------------------------------------------ |
| Flask Web App         | https://swiftrover.onrender.com            |
| Adafruit IO Dashboard | https://io.adafruit.com/AarushP06/feeds    |
| Neon.com Database     | https://console.neon.tech                  |
| Video Demo            | https://www.youtube.com/shorts/C6nwZ4KSzSc |

---

## 📦 Requirements & Installation

### Hardware Requirements

- Raspberry Pi 4B or Pi 5
- Freenove 4WD Robot Car Kit
- HC-SR04 Ultrasonic Sensor (Sensor 1)
- 3-Channel IR Line Sensors (Sensor 2)
- Raspberry Pi Camera Module (Sensor 3 - optional)
- Pan/Tilt Servo Mount
- WS281X LED Strip (optional)
- Buzzer (optional)

### Software Requirements

- Raspberry Pi OS (64-bit)
- Python 3.9+
- Git

---

## 🚀 Quick Start - Raspberry Pi Setup

### Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y \
    python3-venv \
    python3-pip \
    python3-smbus \
    python3-spidev \
    python3-rpi.gpio \
    python3-opencv \
    git

# Enable interfaces (run raspi-config if needed)
sudo raspi-config
# Enable: SPI, I2C, Camera (if needed)
```

### Step 2: Clone Repository

```bash
cd ~
git clone https://github.com/AarushP06/SwiftRover.git
cd SwiftRover
```

### Step 3: Create Virtual Environment & Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt

# Install additional hardware packages
pip install smbus smbus2 spidev RPi.GPIO numpy opencv-python
```

### Step 4: Configure Adafruit IO

```bash
# Create config from sample
cp config/adafruit.sample.json config/adafruit.json

# Edit with your credentials
nano config/adafruit.json
```

**Fill in your Adafruit IO credentials:**

```json
{
  "adafruit": {
    "username": "YOUR_AIO_USERNAME",
    "key": "YOUR_AIO_KEY",
    "feeds": {
      "ultrasonic_cm": "ultra-distance",
      "ir_left": "line-ir-left",
      "ir_center": "line-ir-center",
      "ir_right": "line-ir-right",
      "line_state": "line-state",
      "camera_status": "cam-status",
      "camera_thumb": "cam-thumb",
      "motor_control": "motor-control",
      "led_control": "led-control",
      "buzzer_control": "buzzer-control",
      "line_tracking": "line-tracking",
      "obstacle_avoidance": "obstacle-avoidance"
    }
  },
  "capturing_interval": 5,
  "flushing_interval": 10,
  "sync_interval": 300
}
```

### Step 5: Set Database URL (Optional - for cloud sync)

```bash
export DATABASE_URL="postgresql://user:password@host/database?sslmode=require"
```

---

## 🎮 Running the Robot

### Terminal 1: Command Listener (Required for Web Control)

```bash
cd ~/SwiftRover
source .venv/bin/activate
python3 src/command_listener.py
```

### Terminal 2: Telemetry Publisher (Required for Data Sync)

**Note:** Run telemetry with system Python (outside venv) for camera support:

```bash
cd ~/SwiftRover
# Make sure you're NOT in venv (deactivate if needed)
deactivate 2>/dev/null || true
export DATABASE_URL="your_neon_database_url"
cd src/telemetry
python3 telemetry_runner.py
```

**Why outside venv?** The camera requires `python3-libcamera` (system package) which is only accessible outside the virtual environment. Command listener can run in venv, but telemetry needs system Python for camera support.

### Local Testing: Manual Control (car_tui.py)

```bash
cd ~/SwiftRover/src
python3 car_tui.py
```

**Controls:**

- `W/S/A/D` - Forward/Backward/Left/Right
- `SPACE` - Stop
- `L/K` - Start/Stop Line Tracking
- `O/P` - Start/Stop Obstacle Avoidance
- `U` - Toggle Ultrasonic
- `T` - Toggle LEDs
- `B` - Buzzer
- `Q` - Quit

---

## 📋 Python Dependencies (requirements.txt)

```
paho-mqtt>=1.6,<3.0
python-dateutil>=2.8.0
gpiozero>=1.6.0
Flask>=3.0.0
requests>=2.31.0
psycopg2-binary>=2.9.0
numpy>=1.24.0
```

### Additional System Packages

```bash
# Install via apt
sudo apt install python3-smbus python3-spidev python3-rpi.gpio

# Or via pip (in venv)
pip install smbus smbus2 spidev RPi.GPIO
```

---

## 🌐 Flask Web Application

### Features

- **Dashboard:** Real-time sensor data display with live camera feed
- **Sensor Data:** Historical data charts with date selection
- **Control Car:** Motor controls (Forward, Backward, Left, Right, Stop)
- **Line Tracking:** Start/Stop autonomous line following
- **Obstacle Avoidance:** Start/Stop autonomous navigation
- **Device Control:** LED and Buzzer on/off
- **Camera Feed:** Live camera thumbnail display (Sensor 3) with click-to-zoom

### Local Development

```bash
pip install Flask requests psycopg2-binary
python app.py
# Access at http://localhost:5000
```

### Deployment to Render.com

1. Push code to GitHub
2. Create Web Service on Render.com
3. Set environment variables:
   - `AIO_USERNAME` - Adafruit IO username
   - `AIO_KEY` - Adafruit IO key
   - `AIO_FEEDS` - JSON string of feed mappings
   - `DATABASE_URL` - Neon.com PostgreSQL URL

See `RENDER_DEPLOYMENT.md` for detailed deployment instructions.

---

## 📡 Adafruit IO Feeds

### Sensor Feeds (Robot → Cloud)

**Sensor 1: Ultrasonic Distance**
| Feed Name | Description | Values |
| ---------------- | ------------------- | ----------------- |
| `ultra-distance` | Ultrasonic distance | 0-400 cm |

**Sensor 2: Infrared Line Sensors**
| Feed Name | Description | Values |
| ---------------- | ------------------- | ----------------- |
| `line-ir-left` | IR Left sensor | 0 or 1 |
| `line-ir-center` | IR Center sensor | 0 or 1 |
| `line-ir-right` | IR Right sensor | 0 or 1 |
| `line-state` | Combined line state | L, M, R, LM, etc. |

**Sensor 3: Camera Feed**
| Feed Name | Description | Values |
| ---------------- | ------------------------------ | ----------------- |
| `cam-motion` | Camera thumbnail (base64 image) | JPEG image data (base64 encoded) |
| `cam-status` | Camera status | online/offline |

**Note:** The `cam-motion` feed contains the camera thumbnail as a base64-encoded JPEG image. The Flask web application automatically detects and displays this as a live camera feed on the dashboard.

### Control Feeds (Cloud → Robot)

| Feed Name            | Description        | Commands                             |
| -------------------- | ------------------ | ------------------------------------ |
| `motor-control`      | Motor commands     | forward, backward, left, right, stop |
| `led-control`        | LED commands       | on, off                              |
| `buzzer-control`     | Buzzer commands    | on, off                              |
| `line-tracking`      | Line tracking      | start, stop                          |
| `obstacle-avoidance` | Obstacle avoidance | start, stop                          |

---

## 🗄️ Database Setup (Neon.com)

1. Create account at https://neon.tech
2. Create new project
3. Copy connection string
4. Set as environment variable:

```bash
export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
```

### Database Schema

```sql
CREATE TABLE sensor_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    ultrasonic_cm REAL,
    ir_left INTEGER,
    ir_center INTEGER,
    ir_right INTEGER,
    line_state TEXT
);
```

---

## 📁 Project Structure

```
SwiftRover/
├── app.py                     # Flask web application
├── requirements.txt           # Python dependencies
├── config/
│   ├── adafruit.sample.json   # Config template
│   ├── adafruit.json          # Your config (git-ignored)
│   ├── neon.sample.json       # Neon DB config template
│   └── neon.json              # Neon DB config (git-ignored)
├── templates/                 # Flask HTML templates
│   ├── base.html
│   ├── home.html
│   ├── about.html
│   ├── sensor_data.html
│   ├── control_car.html
│   ├── line_tracking.html
│   └── obstacle_avoidance.html
├── static/
│   ├── css/style.css          # Custom styling
│   └── js/main.js
├── src/
│   ├── hardware/              # Hardware drivers
│   │   ├── motor.py
│   │   ├── ultrasonic.py
│   │   ├── infrared.py
│   │   ├── servo.py
│   │   ├── buzzer.py
│   │   ├── led.py
│   │   ├── camera.py
│   │   └── spi_ledpixel.py
│   ├── telemetry/             # Telemetry modules
│   │   ├── telemetry.py
│   │   ├── telemetry_runner.py
│   │   ├── telemetry_daemon.py
│   │   └── ultra_cache_writer.py
│   ├── command_listener.py    # MQTT command receiver
│   ├── line_follow.py         # Line tracking algorithm
│   ├── obstacle_navigator.py  # Obstacle avoidance
│   ├── car_tui.py             # Terminal UI
│   └── database_sync.py       # DB sync module
├── scripts/                   # Shell scripts
│   ├── run_telemetry.sh
│   └── tail_today.sh
└── db/                        # Local SQLite (git-ignored)
```

---

## 🔧 Troubleshooting

### GPIO Busy Error

```bash
# Kill any Python processes using GPIO
sudo pkill -9 python
sudo pkill -9 python3

# Reset GPIO
python3 -c "import RPi.GPIO as GPIO; GPIO.setwarnings(False); GPIO.setmode(GPIO.BCM); GPIO.cleanup()"
```

### Module Not Found Errors

```bash
# Ensure venv is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
pip install smbus smbus2 spidev RPi.GPIO numpy
```

### MQTT Connection Failed

- Check Adafruit IO key is valid
- Check internet connection
- Verify config/adafruit.json has correct credentials

### Database Sync Failed

- Verify DATABASE_URL is correct
- Check Neon.com project is active
- Ensure `.c-2` is in hostname (pooler URL)

### Line Tracking Issues

- Verify IR sensors are properly connected
- Check sensor readings in debug mode
- Adjust `--invert-steer` and `--invert-drive` flags if needed
- See `DEVELOPMENT_LOG.md` for known issues and fixes

### Obstacle Avoidance Issues

- Ensure ultrasonic sensor is properly mounted
- Check pan/tilt servos are calibrated
- Verify sensor readings in debug output

---

## 🎥 Video Demonstration

**YouTube:** https://www.youtube.com/shorts/C6nwZ4KSzSc

---

## 📝 Project Reflection

For this project, we successfully built a robot that meets the core requirements. What worked really well was our modular `command_listener.py` script, which handles all the sensor readings and motor controls in one place. Using a `config.json` file was also a good decision, as it kept our API keys and pins out of the main code.

The most difficult part was **calibrating the line-following algorithm** to work consistently across different lighting conditions. We spent a lot of time adjusting PID parameters and motor speeds to find the right balance. Another challenge was **setting up the MQTT telemetry system** to reliably publish sensor data without exceeding Adafruit IO's rate limits.

If we had more time, we would improve the line-following algorithm with better PID tuning and add more sophisticated obstacle avoidance.

---

## 📜 License

This project was created for educational purposes at Champlain College Saint-Lambert.

---

**SwiftRover** - IoT Smart Robot Car © 2025
