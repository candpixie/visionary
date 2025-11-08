# GlaucoGuard Detection System

A real-time obstacle detection system with haptic feedback, designed for visual assistance applications.

## Features

- **Real-time Detection**: Monitor three zones (LEFT, CENTER, RIGHT) for obstacles
- **WebSocket Communication**: Low-latency real-time data streaming
- **Phone Camera Support**: Stream camera feed from your phone using Expo Go
- **Dual Interface**:
  - Web UI with live video feed and visual alerts
  - Terminal UI for quick status monitoring
- **Haptic Feedback System**: Zone-specific alerts for obstacle detection
- **Distance Monitoring**: Track obstacle distances in centimeters

## Project Structure

```
glaucogauard/
├── backend/
│   ├── server.py          # WebSocket server with detection logic
│   └── terminal_ui.py     # Terminal-based monitoring interface
├── web/
│   └── index.html         # Web-based UI with live feed
├── mobile/                # Expo app for phone camera streaming
│   ├── App.js             # React Native camera app
│   ├── package.json       # Mobile app dependencies
│   └── README.md          # Mobile app setup guide
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── SETUP_PHONE_CAMERA.md  # Phone camera setup guide
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Backend Server

```bash
python backend/server.py
```

The WebSocket server will start on `ws://localhost:8765`

### 3. Open the Web UI

Open `web/index.html` in a modern web browser. The UI will:
- Automatically connect to the WebSocket server
- Display real-time detection data
- Show video feed from phone camera (if connected)

### 4. (Optional) Connect Phone Camera

To stream your phone's camera to the laptop:

1. See `SETUP_PHONE_CAMERA.md` for detailed instructions
2. Quick steps:
   - Find your laptop's IP address
   - Update `mobile/App.js` with your IP
   - Install dependencies: `cd mobile && npm install`
   - Run: `npm start` and scan QR code with Expo Go
   - Connect and start streaming from the phone app

### 5. Or Use the Terminal UI

For a lightweight monitoring interface:

```bash
python backend/terminal_ui.py
```

## Web UI

The web interface provides:

- **Live Video Feed**: Real-time camera display
- **Zone Indicators**: Visual alerts for LEFT, CENTER, and RIGHT zones
- **Distance Display**: Shows obstacle distances in centimeters
- **Status Panel**:
  - System status (ACTIVE/OFFLINE)
  - Detection count
  - Haptic feedback status
- **Connection Indicator**: Shows WebSocket connection state

### UI Features

- **Active Zones**: Red pulsing animation when obstacle detected < 200cm
- **Auto-Reconnect**: Automatically reconnects if connection is lost
- **Responsive Design**: Adapts to different screen sizes

## Terminal UI

Simple text-based interface showing:

```
=== GLAUCOGUARD STATUS ===
LEFT:   🔴 OBSTACLE DETECTED (120cm)
CENTER: ✅ CLEAR
RIGHT:  ✅ CLEAR
HAPTIC: LEFT ACTIVE
==========================
```

**Status Indicators**:
- 🔴 DANGER: Obstacle < 100cm
- 🟡 WARNING: Obstacle 100-200cm
- ✅ CLEAR: No obstacle or > 200cm

## Detection System

The current implementation includes **simulation mode** for testing. In production:

1. **Replace simulation with actual sensors**:
   - Ultrasonic sensors
   - LiDAR
   - Depth cameras (RealSense, etc.)

2. **Integrate computer vision**:
   - Object detection models
   - Depth estimation
   - Semantic segmentation

3. **Add haptic hardware**:
   - Vibration motors
   - Haptic feedback controllers
   - Zone-specific actuators

## WebSocket API

### Server → Client Messages

```json
{
  "timestamp": "2025-11-08T12:34:56.789",
  "detection": true,
  "zones": {
    "left": 120,
    "center": null,
    "right": 250
  },
  "haptic": "left"
}
```

**Fields**:
- `timestamp`: ISO 8601 timestamp
- `detection`: Boolean indicating if any obstacle detected < 200cm
- `zones`: Distance in cm for each zone (null if no obstacle)
- `haptic`: Active haptic zone ("left", "center", "right", or "none")

### Client → Server Messages

Currently, the server accepts client commands for future expansion:

```json
{
  "command": "start_detection",
  "params": {}
}
```

## Configuration

### Server Configuration

Edit `backend/server.py`:

```python
server = GlaucoGuardServer(
    host="localhost",  # Change to "0.0.0.0" for network access
    port=8765          # Change port if needed
)
```

### Detection Parameters

Adjust in `server.py` → `simulate_detection()`:

- **Detection frequency**: Change `await asyncio.sleep(0.5)` in `detection_loop()`
- **Danger threshold**: Modify distance comparisons (currently 200cm)
- **Zone ranges**: Adjust random distance generation

### UI Customization

Edit `web/index.html`:

- **Colors**: Modify CSS variables in `<style>` section
- **WebSocket URL**: Change `ws://localhost:8765` in JavaScript
- **Update frequency**: Adjust reconnection interval (currently 3000ms)

## Development

### Adding Real Sensors

Replace the `simulate_detection()` method in `server.py`:

```python
def get_sensor_data(self) -> Dict[str, Any]:
    """Connect to actual sensors"""
    # Example: Read from ultrasonic sensors
    left_distance = self.read_ultrasonic_sensor(pin=LEFT_SENSOR_PIN)
    center_distance = self.read_ultrasonic_sensor(pin=CENTER_SENSOR_PIN)
    right_distance = self.read_ultrasonic_sensor(pin=RIGHT_SENSOR_PIN)

    return {
        "zones": {
            "left": left_distance,
            "center": center_distance,
            "right": right_distance
        }
    }
```

### Adding Computer Vision

Integrate with OpenCV or other CV libraries:

```python
import cv2
import numpy as np

def detect_obstacles_cv(self, frame):
    """Use computer vision for obstacle detection"""
    # Implement depth estimation, object detection, etc.
    pass
```

### Testing

Create tests in the `tests/` directory:

```bash
python -m pytest tests/
```

## Hardware Requirements

### Minimum (Simulation)
- Python 3.8+
- Modern web browser
- Webcam (optional, for video feed)

### Production (Real Detection)
- Raspberry Pi 4 or equivalent
- Ultrasonic sensors (HC-SR04 or similar) x3
- Haptic feedback motors x3
- Camera module (optional)

## Troubleshooting

### WebSocket Connection Failed

1. Ensure the server is running: `python backend/server.py`
2. Check firewall settings
3. Verify the port (8765) is not in use
4. Try accessing from `http://` (not `https://`) for local testing

### Camera Access Denied

1. Check browser permissions
2. Ensure HTTPS or localhost (required for camera access)
3. Try different browser

### No Detection Data

1. Check browser console for errors (F12)
2. Verify WebSocket connection status (top-right indicator)
3. Check server logs for errors

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Future Enhancements

- [ ] Add machine learning-based object detection
- [ ] Implement real-time depth mapping
- [ ] Add audio feedback system
- [ ] Create mobile app version
- [ ] Add data logging and analytics
- [ ] Implement multi-user support
- [ ] Add configuration web interface
- [ ] Integration with smart glasses
- [ ] Cloud-based processing option

## Support

For issues and questions:
- Create an issue on GitHub
- Contact: [your-email@example.com]

---

**Built for accessibility and safety** 🦯
