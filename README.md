# 🔔 Remote Alarm Server

A simple cross-platform Python server for playing alarm sounds remotely via web interface.

## Features

- **Play Once** - Play alarm sound a single time
- **Loop Mode** - Play on repeat for 6 hours
- **Stop Now** - Immediately stop playback
- **Delayed Stop** - Stop after 10 seconds (snooze-like)
- **Volume Control** - Adjust volume from the web UI
- **Basic Authentication** - Optional password protection
- **Mobile Friendly** - Large buttons, works great on phones
- **Status Display** - Real-time status with remaining time for loops
- **Logging** - All actions logged to `alarm_server.log`

## Quick Start

### 1. Set up Python environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Add your alarm sound

Place your MP3 file in the project directory and name it `alarm.mp3`:

```bash
cp /path/to/your/sound.mp3 alarm.mp3
```

Or edit `ALARM_FILE` in `app.py` to point to your file.

### 3. Run the server

```bash
python app.py
```

The server starts on `http://0.0.0.0:5000`

### 4. Access the UI

- **Local machine:** http://localhost:5000
- **From LAN:** http://YOUR_IP:5000 (find your IP with `ip addr` or `ipconfig`)

Default credentials: `admin` / `alarm123`

## Configuration

Edit these variables at the top of `app.py`:

```python
# Set to False to disable authentication (for testing)
AUTH_ENABLED = True

# Basic auth credentials (change these!)
USERNAME = "admin"
PASSWORD = "alarm123"

# Path to your alarm sound file
ALARM_FILE = "alarm.mp3"

# Server settings
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000
```

## API Endpoints

All endpoints require authentication (if enabled).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI |
| GET | `/api/status` | Get current status |
| POST | `/api/play` | Play alarm once |
| POST | `/api/loop` | Loop for 6 hours |
| POST | `/api/stop` | Stop immediately |
| POST | `/api/stop-delayed` | Stop in 10 seconds |
| POST | `/api/volume` | Set volume (JSON: `{"volume": 0-100}`) |

### Example API usage with curl:

```bash
# Play once
curl -u admin:alarm123 -X POST http://localhost:5000/api/play

# Stop
curl -u admin:alarm123 -X POST http://localhost:5000/api/stop

# Set volume to 50%
curl -u admin:alarm123 -X POST http://localhost:5000/api/volume \
  -H "Content-Type: application/json" \
  -d '{"volume": 50}'
```

## Exposing to Internet

### Option 1: ngrok (easiest)

```bash
ngrok http 5000
```

### Option 2: DuckDNS + Port Forwarding

1. Get a subdomain at https://duckdns.org
2. Set up port forwarding on your router (port 5000)
3. Point DuckDNS to your public IP
4. Consider adding HTTPS with a reverse proxy (nginx/caddy)

### Security Recommendations

- **Always enable authentication** when exposed to internet
- **Change default credentials** before deploying
- Use **HTTPS** (ngrok provides this automatically)
- Consider IP whitelisting if possible

## Troubleshooting

### No sound on Linux

You may need to install audio dependencies:

```bash
# Debian/Ubuntu
sudo apt-get install libsdl2-mixer-2.0-0

# Fedora
sudo dnf install SDL2_mixer
```

### No sound on Windows

Ensure your audio output device is set correctly and not muted.

### "Alarm file not found" error

Make sure `alarm.mp3` exists in the same directory as `app.py`, or update `ALARM_FILE` to the correct path.

## Project Structure

```
remote_alarm/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── alarm.mp3          # Your alarm sound (add this)
├── alarm_server.log   # Log file (created on first run)
├── templates/
│   └── index.html     # Web UI
└── README.md          # This file
```

## License

MIT - Do whatever you want with it!


## creating the alarm sound

ffmpeg -i nurit.mp3 -ss 4 -t 8 -i police-operation-siren-144229.mp3 \
  -filter_complex "[0:a]adelay=1500|1500,volume=1.0[a0];[1:a]volume=0.3[a1];[a0][a1]amix=inputs=2:duration=longest" \
  alarm.mp3 -y
