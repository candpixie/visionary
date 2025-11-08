# How to Connect Phone Camera to Laptop

This guide will help you stream your phone's camera feed to your laptop using Expo Go.

## Quick Start

### Step 1: Find Your Laptop's IP Address

**Windows:**
1. Open Command Prompt (Press `Win + R`, type `cmd`, press Enter)
2. Type: `ipconfig`
3. Look for "IPv4 Address" under your active network adapter (usually Wi-Fi or Ethernet)
4. Copy this IP address (e.g., `192.168.1.100`)

**Mac/Linux:**
1. Open Terminal
2. Type: `ifconfig` or `ip addr`
3. Look for your network interface (usually `en0` on Mac, `wlan0` on Linux)
4. Find the `inet` address (e.g., `192.168.1.100`)

### Step 2: Update Mobile App Configuration

1. Open `mobile/App.js`
2. Find this line (around line 12):
   ```javascript
   const [serverUrl, setServerUrl] = useState('ws://192.168.1.100:8765');
   ```
3. Replace `192.168.1.100` with your laptop's IP address from Step 1

### Step 3: Start the Backend Server

On your laptop, open a terminal in the project directory and run:

```bash
python backend/server.py
```

You should see:
```
Server running on ws://0.0.0.0:8765
Waiting for connections...
```

**Important:** Keep this terminal window open while using the app.

### Step 4: Install and Run the Mobile App

1. **Install Node.js and npm** (if not already installed)
   - Download from: https://nodejs.org/

2. **Install Expo CLI** (if not already installed):
   ```bash
   npm install -g expo-cli
   ```

3. **Install app dependencies:**
   ```bash
   cd mobile
   npm install
   ```

4. **Start the Expo development server:**
   ```bash
   npm start
   ```

5. **On your phone:**
   - Install **Expo Go** app from App Store (iOS) or Google Play (Android)
   - Open Expo Go
   - Scan the QR code shown in your terminal/browser
   - The app will load on your phone

### Step 5: Connect and Stream

1. **On your phone (in Expo Go app):**
   - Grant camera permission when prompted
   - Tap **"CONNECT TO SERVER"**
   - Wait for "Connected" message
   - Tap **"START STREAMING"**

2. **On your laptop:**
   - Open `web/index.html` in your web browser
   - You should see the video feed from your phone's camera!

## Troubleshooting

### "Can't connect to server" on phone

- ✅ Make sure your phone and laptop are on the **same Wi-Fi network**
- ✅ Verify the IP address in `App.js` matches your laptop's IP
- ✅ Check that the server is running (`python backend/server.py`)
- ✅ Try disabling your laptop's firewall temporarily to test
- ✅ On Windows, you may need to allow Python through Windows Firewall

### Camera permission denied

- Go to your phone's Settings → Apps → Expo Go → Permissions
- Enable Camera permission

### Video not showing on laptop

- ✅ Make sure you tapped "START STREAMING" on the phone
- ✅ Check browser console (F12) for errors
- ✅ Verify WebSocket connection status (should show "CONNECTED" in top-right)
- ✅ Check server terminal for connection messages

### Server shows "Connection refused"

- Make sure the server is listening on `0.0.0.0` (not `localhost`)
- Check that port 8765 is not blocked by firewall
- Try restarting the server

## Network Requirements

- Both devices must be on the same Wi-Fi network
- The laptop's firewall should allow incoming connections on port 8765
- For best performance, use a stable Wi-Fi connection

## Performance Tips

- The app streams at 10 FPS (frames per second)
- Video quality is set to 50% to reduce bandwidth
- For smoother streaming, ensure a strong Wi-Fi signal
- Close other bandwidth-intensive apps on your phone

## Next Steps

Once the camera is streaming:
- The video feed will appear in the web interface
- Detection data will continue to work as before
- You can use this setup for real-time obstacle detection with your phone's camera

