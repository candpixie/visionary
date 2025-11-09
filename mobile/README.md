# Visionary Mobile Camera App

This Expo app allows you to stream your phone's camera feed to the Visionary server running on your laptop.

## Setup Instructions

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Configure Server IP Address

Before running the app, you need to update the server URL in `App.js`:

1. Find your laptop's IP address on your local network:
   - **Windows**: Open Command Prompt and run `ipconfig`, look for "IPv4 Address"
   - **Mac/Linux**: Open Terminal and run `ifconfig` or `ip addr`, look for your network interface IP

2. Update the `serverUrl` in `App.js`:
   ```javascript
   const [serverUrl, setServerUrl] = useState('ws://YOUR_LAPTOP_IP:8765');
   ```
   Replace `YOUR_LAPTOP_IP` with your actual IP address (e.g., `ws://192.168.1.100:8765`)

### 3. Start the Backend Server

On your laptop, make sure the Visionary server is running:

```bash
python backend/server.py
```

The server should show:
```
Server running on ws://0.0.0.0:8765
```

### 4. Run the Mobile App

```bash
npm start
```

Then:
- Scan the QR code with Expo Go app on your phone
- Or press `a` for Android emulator
- Or press `i` for iOS simulator

### 5. Connect and Stream

1. Open the app on your phone
2. Tap "CONNECT TO SERVER"
3. Once connected, tap "START STREAMING"
4. The camera feed will now stream to your laptop
5. Open `web/index.html` in your browser to view the stream

## Troubleshooting

### Can't Connect to Server

- Make sure your phone and laptop are on the same Wi-Fi network
- Check that the server IP address in `App.js` matches your laptop's IP
- Verify the server is running and listening on `0.0.0.0:8765`
- Check your firewall settings - port 8765 should be open

### Camera Permission Denied

- Go to your phone's Settings
- Find the Expo Go app
- Enable Camera permissions

### Video Not Showing on Laptop

- Make sure you've started streaming from the phone app
- Check the browser console (F12) for errors
- Verify the WebSocket connection is established (check connection status indicator)

## Notes

- The app captures frames at 10 FPS (every 100ms) for smooth streaming
- Video quality is set to 0.5 (50%) to reduce bandwidth usage
- Make sure both devices are on the same network for best performance

