# SwiftRover IoT Robot

This is our smart mobile robot built on a Raspberry Pi 4B. We created this for our "IoT: Design and Prototyping of Connected Devices" (420-N55) course at Champlain College Saint-Lambert.

Our robot follows a black line using IR sensors, avoids objects in its path with an ultrasonic sensor, and sends all its live data to a cloud dashboard on Adafruit IO.

## Team Members

- Mir Faiyazur Rahman
- Aarush Patel

---

## Project Submission Links

Here are the links for our Milestone 2 submission.

### 1. Video Demonstration

This video shows our system overview, a walkthrough of the code, how to run it, and a live demo of the robot, and sending data to the dashboard.

**Link: [...]**

---

## Project Reflection

For this project, we successfully built a robot that meets the core requirements. What worked really well was our modular `car_tui.py` script, which handles all the sensor readings and motor controls in one place. Using a `config.json` file was also a good decision, as it kept our API keys and pins out of the main code.

The most difficult part was **calibrating the line-following algorithm** to work consistently across different lighting conditions. We spent a lot of time adjusting PID parameters and motor speeds to find the right balance. Another challenge was **setting up the MQTT telemetry system** to reliably publish sensor data without exceeding Adafruit IO's rate limits.

If we had more time, we would improve the line-following algorithm with better PID tuning and add more sophisticated obstacle avoidance.

---

## System Overview

- **Controller:** Raspberry Pi 4B

- **Sensors:**

  - 3x IR Line Sensors (for line following)
  - 1x HC-SR04 Ultrasonic Sensor (for obstacle avoidance)

- **Actuators:**

  - 2x DC Motors
  - 1x PCA9685 Motor Driver

- **Cloud:** Adafruit IO

  - **Telemetry:** We publish live ultrasonic distance and line sensor states.
  - **Remote Control:** We subscribe to feeds to get commands like "start", "stop", or change mode.

- **Logging:** The robot saves all sensor data to a local .csv file in the `logs/` directory and creates a new file every day.

---

## Repository Structure

```
SwiftRover/
├── config/              # Configuration files (API keys, settings)
├── docs/                # Documentation and screenshots
├── logs/                # Daily CSV log files (git-ignored)
├── scripts/             # Shell scripts for running telemetry
├── src/                 # Source code
│   ├── hardware/        # Hardware interfaces (sensors, motors)
│   ├── server/          # TCP server for remote control
│   ├── telemetry/       # MQTT client and data publishing
│   ├── utils/           # Utility functions
│   ├── car_tui.py       # Main terminal UI for manual control
│   ├── line_follow.py   # Autonomous line following
│   └── main.py          # PyQt GUI server application
├── requirements.txt
└── README.md
```

---

## Code Structure

**Main Loop:** Runs in `car_tui.py` or `line_follow.py`, continuously reading sensor data and sending commands to actuators.

**Modules:**

- `hardware/`: Hardware interfaces for sensors and actuators
- `telemetry/`: MQTT client and telemetry publishing to Adafruit IO
- `server/`: TCP server for remote control and PyQt GUI

**MQTT Client:** `telemetry/telemetry.py` connects to Adafruit IO and publishes sensor data. Reads from cache files (`/tmp/ir_lmr.txt`, `/tmp/ultra_cm.txt`) to avoid GPIO conflicts.

**Logging:** CSV logs written daily with ISO timestamps. Files named `YYYY-MM-DD_robot_telemetry.csv`.

---

## How to Run

### Start the Robot

```bash
cd src
python3 car_tui.py
```

**Controls:** `W`/`S` - Forward/Backward | `A`/`D` - Turn | `L` - Line Follow | `O` - Obstacle Navigator | `Q` - Quit

### Start Telemetry (separate terminal)

```bash
./scripts/run_telemetry.sh
```

This publishes sensor data to Adafruit IO and logs to CSV files.

---

## Installation

```bash
# Clone repository
git clone https://github.com/AarushP06/SwiftRover.git
cd SwiftRover

# Install dependencies
pip install -r requirements.txt

# Configure Adafruit IO
cp config/adafruit.sample.json config/adafruit.json
nano config/adafruit.json  # Add your credentials
```
