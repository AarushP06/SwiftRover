#!/usr/bin/env python3
"""
Flask Web Application for IoT Smart Robot Car
Milestone 3 - Champlain College Saint-Lambert
"""
from flask import Flask, render_template, jsonify, request
import os
import json
from pathlib import Path
from datetime import datetime
import sqlite3
import requests
from threading import Thread
import time
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration paths
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "src"))
from database_sync import (
    save_to_local_db,
    sync_to_cloud,
    check_internet,
    init_local_db,
    get_cloud_connection
)
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
DB_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Load Adafruit IO config
# Priority: Environment variables (for Render.com) > Config file (for local dev)
ADAFRUIT_CONFIG = None

# Try environment variables first (for Render.com deployment)
AIO_USERNAME = os.environ.get("AIO_USERNAME", "")
AIO_KEY = os.environ.get("AIO_KEY", "")
AIO_FEEDS_JSON = os.environ.get("AIO_FEEDS", "{}")

# If env vars not set, try config file (for local development)
if not AIO_USERNAME or not AIO_KEY:
    try:
        with open(CONFIG_DIR / "adafruit.json") as f:
            ADAFRUIT_CONFIG = json.load(f)
            if "adafruit" in ADAFRUIT_CONFIG:
                ADAFRUIT_CONFIG = ADAFRUIT_CONFIG["adafruit"]
            AIO_USERNAME = AIO_USERNAME or ADAFRUIT_CONFIG.get("username", "")
            AIO_KEY = AIO_KEY or ADAFRUIT_CONFIG.get("key", "")
            if not AIO_FEEDS_JSON or AIO_FEEDS_JSON == "{}":
                AIO_FEEDS_JSON = json.dumps(ADAFRUIT_CONFIG.get("feeds", {}))
    except Exception as e:
        print(f"Warning: Could not load Adafruit config file: {e}")

# Parse feeds from JSON string (env var) or dict (config file)
try:
    if isinstance(AIO_FEEDS_JSON, str):
        AIO_FEEDS = json.loads(AIO_FEEDS_JSON)
    else:
        AIO_FEEDS = AIO_FEEDS_JSON
except Exception:
    AIO_FEEDS = {}

# Database paths
LOCAL_DB = DB_DIR / "robot_telemetry.db"
SYNC_STATUS_FILE = DB_DIR / "sync_status.json"

# Cloud database config (Neon.com PostgreSQL)
CLOUD_DB_URL = os.environ.get("DATABASE_URL", "")  # Set in Render.com environment

# Initialize local database (use function from database_sync module)
init_local_db()

# ============================================================================
# Database Functions
# ============================================================================

def get_historical_data(date_str=None):
    """Get historical data from cloud DB (Neon.com) or local DB fallback
    If date_str is None, returns ALL historical data
    If date_str is provided, returns data for that specific date only
    """
    # Try cloud database first (for Render.com deployment)
    if CLOUD_DB_URL:
        conn, error = get_cloud_connection()
        if conn:
            try:
                from psycopg2.extras import RealDictCursor
                c = conn.cursor(cursor_factory=RealDictCursor)

                # Query by date if provided, otherwise get all data
                if date_str:
                    # Support both date formats: YYYY-MM-DD and full datetime
                    c.execute('''
                        SELECT timestamp, ultrasonic_cm, ir_left, ir_center, ir_right, line_state
                        FROM sensor_data
                        WHERE DATE(timestamp) = %s
                        ORDER BY timestamp ASC
                    ''', (date_str,))
                else:
                    # Get ALL historical data (most recent first, or oldest first?)
                    # Using ASC to show chronological order
                    c.execute('''
                        SELECT timestamp, ultrasonic_cm, ir_left, ir_center, ir_right, line_state
                        FROM sensor_data
                        ORDER BY timestamp ASC
                    ''')

                records = c.fetchall()
                conn.close()
                print(f"[app] Retrieved {len(records)} records from cloud DB (date: {date_str or 'ALL'})", file=sys.stderr)
                # Convert to list of tuples for compatibility
                result = [(r['timestamp'], r['ultrasonic_cm'], r['ir_left'], r['ir_center'], r['ir_right'], r['line_state'])
                        for r in records]
                if len(result) == 0:
                    print(f"[app] WARNING: No records found in cloud DB for date: {date_str or 'ALL'}", file=sys.stderr)
                return result
            except Exception as e:
                print(f"[app] ERROR getting historical data from cloud DB: {e}", file=sys.stderr)
                import traceback
                print(f"[app] Traceback: {traceback.format_exc()}", file=sys.stderr)
                try:
                    conn.close()
                except:
                    pass
                # Fall through to local DB
        else:
            print(f"[app] Could not connect to cloud DB: {error}", file=sys.stderr)

    # Fallback to local DB (for local development or if cloud fails)
    try:
        conn = sqlite3.connect(LOCAL_DB)
        c = conn.cursor()

        if date_str:
            c.execute('''
                SELECT timestamp, ultrasonic_cm, ir_left, ir_center, ir_right, line_state
                FROM sensor_data
                WHERE date(timestamp) = date(?)
                ORDER BY timestamp
            ''', (date_str,))
        else:
            # Get ALL historical data
            c.execute('''
                SELECT timestamp, ultrasonic_cm, ir_left, ir_center, ir_right, line_state
                FROM sensor_data
                ORDER BY timestamp
            ''')

        records = c.fetchall()
        conn.close()
        print(f"[app] Retrieved {len(records)} records from local DB (date: {date_str or 'ALL'})")
        return records
    except Exception as e:
        print(f"[app] Error getting historical data from local DB: {e}", file=sys.stderr)
        return []

# ============================================================================
# Adafruit IO Functions
# ============================================================================

# Cache for Adafruit IO data to reduce API calls (free tier has 30/min limit)
_adafruit_cache = {}
_adafruit_cache_time = {}
ADAFRUIT_CACHE_TTL = 10  # Cache for 10 seconds (increased to reduce API calls)

def get_adafruit_data(feed_key):
    """Get latest value from Adafruit IO feed via HTTP (with caching)"""
    global _adafruit_cache, _adafruit_cache_time
    
    if not AIO_USERNAME or not AIO_KEY:
        return None
    
    # Check cache first
    now = time.time()
    if feed_key in _adafruit_cache:
        cache_age = now - _adafruit_cache_time.get(feed_key, 0)
        if cache_age < ADAFRUIT_CACHE_TTL:
            return _adafruit_cache[feed_key]
    
    try:
        feed_name = AIO_FEEDS.get(feed_key, "")
        if not feed_name:
            return None
        url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{feed_name}/data/last"
        headers = {"X-AIO-Key": AIO_KEY}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            value = data.get("value")
            # Update cache
            _adafruit_cache[feed_key] = value
            _adafruit_cache_time[feed_key] = now
            return value
        elif response.status_code == 429:
            # Rate limited - return cached value if available
            return _adafruit_cache.get(feed_key)
        return None
    except Exception as e:
        print(f"Error fetching Adafruit data: {e}")
        # Return cached value on error
        return _adafruit_cache.get(feed_key)

# Rate limiting tracker
_last_command_time = {}
RATE_LIMIT_SECONDS = 2  # Minimum seconds between commands to same feed

def send_adafruit_command(feed_key, value):
    """Send command to Adafruit IO feed with rate limiting protection.
    
    STOP commands are critical and bypass local rate limiting.
    They also auto-retry up to 3 times if Adafruit IO rate limits.
    """
    global _last_command_time
    
    # STOP commands are critical - bypass local rate limiting and retry on Adafruit rate limit
    is_stop_command = (str(value).lower() == "stop")
    max_retries = 3 if is_stop_command else 1
    retry_delay = 2.5  # seconds between retries for stop commands
    
    app.logger.info(f"[SEND_COMMAND] Attempting to send command: feed_key='{feed_key}', value='{value}' (is_stop={is_stop_command})")
    
    # Check local rate limit to prevent spam (SKIP for stop commands - they must go through)
    now = time.time()
    if not is_stop_command:
        last_time = _last_command_time.get(feed_key, 0)
        if now - last_time < RATE_LIMIT_SECONDS:
            wait_time = RATE_LIMIT_SECONDS - (now - last_time)
            app.logger.warning(f"[SEND_COMMAND] Local rate limit: wait {wait_time:.1f}s before sending to {feed_key}")
            return "rate_limited"
    else:
        app.logger.info(f"[SEND_COMMAND] STOP command - bypassing local rate limit")
    
    if not AIO_USERNAME or not AIO_KEY:
        app.logger.error(f"[SEND_COMMAND] ERROR: Missing credentials - AIO_USERNAME={bool(AIO_USERNAME)}, AIO_KEY={bool(AIO_KEY)}")
        return False
    
    feed_name = AIO_FEEDS.get(feed_key, "")
    if not feed_name:
        app.logger.error(f"[SEND_COMMAND] ERROR: Feed key '{feed_key}' not found in AIO_FEEDS. Available keys: {list(AIO_FEEDS.keys())}")
        return False
    
    url = f"https://io.adafruit.com/api/v2/{AIO_USERNAME}/feeds/{feed_name}/data"
    headers = {"X-AIO-Key": AIO_KEY, "Content-Type": "application/json"}
    data = {"value": str(value)}
    
    # Retry loop for stop commands
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                app.logger.info(f"[SEND_COMMAND] STOP retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay")
            
            app.logger.info(f"[SEND_COMMAND] POST to {url} with value='{value}'")
            response = requests.post(url, headers=headers, json=data, timeout=5)
            
            # Handle rate limiting from Adafruit IO
            if response.status_code == 429:
                app.logger.error(f"[SEND_COMMAND] RATE LIMITED by Adafruit IO: {response.text}")
                
                # For stop commands, wait and retry
                if is_stop_command and attempt < max_retries - 1:
                    app.logger.info(f"[SEND_COMMAND] STOP command rate limited - waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)
                    continue
                
                return "rate_limited"
            
            # Accept both 200 (OK) and 201 (Created) as success
            success = response.status_code in [200, 201]
            if success:
                _last_command_time[feed_key] = time.time()  # Update last command time
                app.logger.info(f"[SEND_COMMAND] SUCCESS: Command sent successfully (status {response.status_code})")
                if attempt > 0:
                    app.logger.info(f"[SEND_COMMAND] STOP command succeeded on retry {attempt + 1}")
                return True
            else:
                app.logger.error(f"[SEND_COMMAND] ERROR: Adafruit IO returned status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            app.logger.exception(f"[SEND_COMMAND] EXCEPTION: Error sending Adafruit command: {e}")
            # For stop commands, retry on exception too
            if is_stop_command and attempt < max_retries - 1:
                app.logger.info(f"[SEND_COMMAND] STOP command failed - waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
                continue
            return False
    
    return False

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def home():
    """Home page / Dashboard"""
    return render_template('home.html')

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/sensor-data')
def sensor_data():
    """Show sensor data page"""
    return render_template('sensor_data.html')

@app.route('/control-car')
def control_car():
    """Control car page"""
    return render_template('control_car.html')

@app.route('/line-tracking')
def line_tracking():
    """Line tracking page"""
    return render_template('line_tracking.html')

@app.route('/obstacle-avoidance')
def obstacle_avoidance():
    """Obstacle avoidance page"""
    return render_template('obstacle_avoidance.html')

# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/live-data')
def api_live_data():
    """Get live sensor data from Adafruit IO"""
    try:
        ultrasonic = get_adafruit_data("ultrasonic_cm")
        ir_left = get_adafruit_data("ir_left")
        ir_center = get_adafruit_data("ir_center")
        ir_right = get_adafruit_data("ir_right")
        line_state = get_adafruit_data("line_state")
        camera_motion = get_adafruit_data("camera_motion")  # Sensor 3: Camera motion detection
        timestamp = datetime.now().isoformat()

        # Save to local database (for offline storage) - only if we have data
        try:
            save_to_local_db(
                timestamp=timestamp,
                ultrasonic=float(ultrasonic) if ultrasonic else None,
                ir_left=int(ir_left) if ir_left else None,
                ir_center=int(ir_center) if ir_center else None,
                ir_right=int(ir_right) if ir_right else None,
                line_state=line_state if line_state else None
            )
        except Exception as e:
            print(f"Warning: Could not save to local DB: {e}")

        data = {
            "ultrasonic_cm": ultrasonic,
            "ir_left": ir_left,
            "ir_center": ir_center,
            "ir_right": ir_right,
            "line_state": line_state,
            "camera_motion": camera_motion,  # Sensor 3: Camera thumbnail (base64 image)
            "timestamp": timestamp
        }
        return jsonify(data)
    except Exception as e:
        print(f"Error in api_live_data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/capture-photo', methods=['POST'])
def api_capture_photo():
    """Refresh camera feed - camera captures automatically via telemetry"""
    try:
        # Just refresh the feed - camera is already capturing automatically
        # This forces an immediate refresh of the image display
        return jsonify({"status": "success", "message": "Refreshing camera feed..."})
    except Exception as e:
        print(f"Error in api_capture_photo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/historical-data', methods=['POST'])
def api_historical_data():
    """Get historical sensor data for a specific date (or all data if no date provided)"""
    try:
        if not request.json:
            return jsonify({"error": "JSON body required"}), 400

        date_str = request.json.get('date')  # Optional - if None, returns all data
        records = get_historical_data(date_str)
        data = {
            "timestamps": [r[0] for r in records],
            "ultrasonic": [r[1] if r[1] is not None else None for r in records],
            "ir_left": [r[2] if r[2] is not None else None for r in records],
            "ir_center": [r[3] if r[3] is not None else None for r in records],
            "ir_right": [r[4] if r[4] is not None else None for r in records],
            "line_state": [r[5] if r[5] else "" for r in records]
        }
        return jsonify(data)
    except Exception as e:
        print(f"Error in api_historical_data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/control/motor', methods=['POST'])
def api_control_motor():
    """Control car motors"""
    try:
        if not request.json:
            return jsonify({"error": "JSON body required"}), 400

        action = request.json.get('action')  # forward, backward, left, right, stop
        if not isinstance(action, str) or action not in ['forward', 'backward', 'left', 'right', 'stop']:
            return jsonify({"error": "Invalid action"}), 400

        # Send command to Adafruit IO (which will be picked up by Raspberry Pi)
        result = send_adafruit_command("motor_control", action)
        if result == "rate_limited":
            return jsonify({"success": False, "action": action, "rate_limited": True}), 429
        return jsonify({"success": bool(result), "action": action})
    except Exception as e:
        print(f"Error in api_control_motor: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/control/led', methods=['POST'])
def api_control_led():
    """Control LEDs"""
    try:
        if not request.json:
            return jsonify({"error": "JSON body required"}), 400

        state = request.json.get('state')  # on, off
        if not isinstance(state, str) or state not in ['on', 'off']:
            return jsonify({"error": "Invalid state"}), 400

        result = send_adafruit_command("led_control", state)
        if result == "rate_limited":
            return jsonify({"success": False, "state": state, "rate_limited": True}), 429
        return jsonify({"success": bool(result), "state": state})
    except Exception as e:
        print(f"Error in api_control_led: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/control/buzzer', methods=['POST'])
def api_control_buzzer():
    """Control buzzer"""
    try:
        if not request.json:
            return jsonify({"error": "JSON body required"}), 400

        state = request.json.get('state')  # on, off
        if not isinstance(state, str) or state not in ['on', 'off']:
            return jsonify({"error": "Invalid state"}), 400

        result = send_adafruit_command("buzzer_control", state)
        if result == "rate_limited":
            return jsonify({"success": False, "state": state, "rate_limited": True}), 429
        return jsonify({"success": bool(result), "state": state})
    except Exception as e:
        print(f"Error in api_control_buzzer: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/line-tracking/start', methods=['POST'])
def api_line_tracking_start():
    """Start line tracking algorithm"""
    try:
        result = send_adafruit_command("line_tracking", "start")
        if result == "rate_limited":
            return jsonify({"success": False, "message": "Rate limited - please wait 2 seconds", "rate_limited": True}), 429
        return jsonify({"success": bool(result)})
    except Exception as e:
        print(f"Error in api_line_tracking_start: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/line-tracking/stop', methods=['POST'])
def api_line_tracking_stop():
    """Stop line tracking algorithm"""
    try:
        result = send_adafruit_command("line_tracking", "stop")
        if result == "rate_limited":
            return jsonify({"success": False, "message": "Rate limited - please wait 2 seconds", "rate_limited": True}), 429
        return jsonify({"success": True, "message": "Stop command sent"})
    except Exception as e:
        print(f"Error in api_line_tracking_stop: {e}")
        return jsonify({"success": False, "message": "Error sending stop command"})

@app.route('/api/obstacle-avoidance/start', methods=['POST'])
def api_obstacle_avoidance_start():
    """Start obstacle avoidance algorithm"""
    app.logger.info("[API_START] ===== Obstacle avoidance start requested =====")
    try:
        result = send_adafruit_command("obstacle_avoidance", "start")
        if result == "rate_limited":
            app.logger.warning("[API_START] ⚠️ Rate limited - please wait before retrying")
            return jsonify({"success": False, "message": "Rate limited - please wait 2 seconds", "rate_limited": True}), 429
        elif result:
            app.logger.info("[API_START] ✅ Command sent successfully to Adafruit IO")
            return jsonify({"success": True, "sent": True})
        else:
            app.logger.error("[API_START] ❌ FAILED to send command to Adafruit IO")
            return jsonify({"success": False, "sent": False})
    except Exception as e:
        app.logger.exception(f"Error in api_obstacle_avoidance_start: {e}")
        return jsonify({"error": "Internal server error", "sent": False}), 500

@app.route('/api/obstacle-avoidance/stop', methods=['POST'])
def api_obstacle_avoidance_stop():
    """Stop obstacle avoidance algorithm"""
    app.logger.info("[API_STOP] ===== Obstacle avoidance stop requested =====")
    try:
        result = send_adafruit_command("obstacle_avoidance", "stop")
        if result == "rate_limited":
            app.logger.warning("[API_STOP] ⚠️ Rate limited - please wait before retrying")
            return jsonify({"success": False, "message": "Rate limited - please wait 2 seconds", "rate_limited": True}), 429
        elif result:
            app.logger.info("[API_STOP] ✅ Command sent successfully to Adafruit IO")
            return jsonify({"success": True, "message": "Stop command sent", "sent": True})
        else:
            app.logger.error("[API_STOP] ❌ FAILED to send command to Adafruit IO")
            return jsonify({"success": False, "message": "Failed to send stop command", "sent": False})
    except Exception as e:
        app.logger.exception(f"[API_STOP] ❌ EXCEPTION in api_obstacle_avoidance_stop: {e}")
        return jsonify({"success": False, "message": "Error sending stop command", "sent": False, "error": str(e)})

def start_sync_worker():
    """Start background thread for database sync"""
    def sync_loop():
        while True:
            if check_internet():
                sync_to_cloud()
            time.sleep(300)  # Sync every 5 minutes

    thread = Thread(target=sync_loop, daemon=True)
    thread.start()

if __name__ == '__main__':
    # Start sync worker
    start_sync_worker()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
