#!/usr/bin/env python3
"""
Remote Alarm Server
A simple Flask server for playing alarm sounds remotely.
"""

import os
import threading
import time
import logging
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request, Response

# Initialize pygame mixer for audio
import pygame

pygame.mixer.init()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Set to False to disable authentication (for testing)
AUTH_ENABLED = True

# Basic auth credentials (change these!)
USERNAME = "admin"
PASSWORD = "alarm123"

# Path to your alarm sound file
ALARM_FILE = "alarm.mp3"

# Server settings
HOST = "0.0.0.0"  # Listen on all interfaces for LAN access
PORT = 5000

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("alarm_server.log"),
    ],
)
logger = logging.getLogger(__name__)

# =============================================================================
# APPLICATION STATE
# =============================================================================

app = Flask(__name__)


class AlarmState:
    """Manages the current state of the alarm system."""

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"  # idle, playing, looping, stopping_soon
        self.stop_event = threading.Event()
        self.loop_thread = None
        self.delayed_stop_thread = None
        self.loop_end_time = None
        self.volume = 1.0  # Default volume (0.0 to 1.0)

    def set_status(self, status):
        with self.lock:
            self.status = status
            logger.info(f"Status changed to: {status}")

    def get_status(self):
        with self.lock:
            return self.status

    def get_info(self):
        with self.lock:
            info = {"status": self.status, "volume": int(self.volume * 100)}
            if self.status == "looping" and self.loop_end_time:
                remaining = self.loop_end_time - datetime.now()
                if remaining.total_seconds() > 0:
                    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    info["remaining"] = f"{hours}h {minutes}m {seconds}s"
                else:
                    info["remaining"] = "ending..."
            return info


state = AlarmState()

# =============================================================================
# AUTHENTICATION
# =============================================================================


def check_auth(username, password):
    """Verify username and password."""
    return username == USERNAME and password == PASSWORD


def authenticate():
    """Send a 401 response to enable basic auth."""
    return Response(
        "Authentication required.\n",
        401,
        {"WWW-Authenticate": 'Basic realm="Alarm Server"'},
    )


def requires_auth(f):
    """Decorator for routes that require authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            logger.warning(f"Failed auth attempt from {request.remote_addr}")
            return authenticate()
        return f(*args, **kwargs)

    return decorated


# =============================================================================
# AUDIO FUNCTIONS
# =============================================================================


def get_alarm_path():
    """Get the full path to the alarm file."""
    if os.path.isabs(ALARM_FILE):
        return ALARM_FILE
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ALARM_FILE)


def check_alarm_file():
    """Check if alarm file exists and is readable."""
    path = get_alarm_path()
    if not os.path.exists(path):
        logger.error(f"Alarm file not found: {path}")
        return False, f"Alarm file not found: {path}"
    return True, path


def play_once():
    """Play the alarm sound once."""
    exists, path = check_alarm_file()
    if not exists:
        return False, path

    stop_all()
    state.set_status("playing")

    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(state.volume)
        pygame.mixer.music.play()
        logger.info("Playing alarm once")

        # Monitor in background thread to update status when done
        def monitor():
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            if state.get_status() == "playing":
                state.set_status("idle")

        threading.Thread(target=monitor, daemon=True).start()
        return True, "Playing alarm once"
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        state.set_status("idle")
        return False, str(e)


def play_loop(duration_hours=6):
    """Play the alarm on loop for specified duration."""
    exists, path = check_alarm_file()
    if not exists:
        return False, path

    stop_all()
    state.set_status("looping")
    state.stop_event.clear()
    state.loop_end_time = datetime.now() + timedelta(hours=duration_hours)

    def loop_worker():
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(state.volume)
            pygame.mixer.music.play(loops=-1)  # -1 means infinite loop
            logger.info(f"Started looping for {duration_hours} hours")

            end_time = time.time() + (duration_hours * 3600)
            while time.time() < end_time and not state.stop_event.is_set():
                time.sleep(0.5)

            pygame.mixer.music.stop()
            if not state.stop_event.is_set():
                logger.info("Loop duration completed")
            state.set_status("idle")
        except Exception as e:
            logger.error(f"Error in loop worker: {e}")
            state.set_status("idle")

    state.loop_thread = threading.Thread(target=loop_worker, daemon=True)
    state.loop_thread.start()
    return True, f"Looping alarm for {duration_hours} hours"


def stop_all():
    """Stop all audio playback immediately."""
    state.stop_event.set()
    pygame.mixer.music.stop()
    state.loop_end_time = None
    state.set_status("idle")
    logger.info("Stopped all audio")
    return True, "Stopped"


def stop_delayed(delay_seconds=10):
    """Stop audio after a delay."""
    if state.get_status() == "idle":
        return False, "Nothing is playing"

    state.set_status("stopping_soon")

    def delayed_worker():
        logger.info(f"Will stop in {delay_seconds} seconds")
        for _ in range(delay_seconds * 10):
            if state.stop_event.is_set() or state.get_status() == "idle":
                return
            time.sleep(0.1)
        stop_all()
        logger.info("Delayed stop executed")

    state.delayed_stop_thread = threading.Thread(target=delayed_worker, daemon=True)
    state.delayed_stop_thread.start()
    return True, f"Stopping in {delay_seconds} seconds"


def set_volume(volume_percent):
    """Set the volume (0-100)."""
    volume = max(0, min(100, volume_percent)) / 100.0
    state.volume = volume
    pygame.mixer.music.set_volume(volume)
    logger.info(f"Volume set to {volume_percent}%")
    return True, f"Volume set to {volume_percent}%"


# =============================================================================
# ROUTES
# =============================================================================


@app.route("/")
@requires_auth
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/api/status")
@requires_auth
def api_status():
    """Get current alarm status."""
    return jsonify(state.get_info())


@app.route("/api/play", methods=["POST"])
@requires_auth
def api_play():
    """Play alarm once."""
    success, message = play_once()
    return jsonify({"success": success, "message": message})


@app.route("/api/loop", methods=["POST"])
@requires_auth
def api_loop():
    """Play alarm on loop for 6 hours."""
    success, message = play_loop(duration_hours=6)
    return jsonify({"success": success, "message": message})


@app.route("/api/stop", methods=["POST"])
@requires_auth
def api_stop():
    """Stop immediately."""
    success, message = stop_all()
    return jsonify({"success": success, "message": message})


@app.route("/api/stop-delayed", methods=["POST"])
@requires_auth
def api_stop_delayed():
    """Stop after 10 seconds."""
    success, message = stop_delayed(delay_seconds=10)
    return jsonify({"success": success, "message": message})


@app.route("/api/volume", methods=["POST"])
@requires_auth
def api_volume():
    """Set volume."""
    data = request.get_json() or {}
    volume = data.get("volume", 100)
    success, message = set_volume(volume)
    return jsonify({"success": success, "message": message, "volume": volume})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    logger.info(f"Starting Alarm Server on http://{HOST}:{PORT}")
    logger.info(f"Authentication: {'ENABLED' if AUTH_ENABLED else 'DISABLED'}")

    exists, path = check_alarm_file()
    if exists:
        logger.info(f"Alarm file: {path}")
    else:
        logger.warning(f"Alarm file not found! Please add: {get_alarm_path()}")

    app.run(host=HOST, port=PORT, debug=False, threaded=True)
