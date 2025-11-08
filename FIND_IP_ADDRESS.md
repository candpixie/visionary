# How to Find Your IP Address and Port

## Finding Your IP Address (Windows)

### Method 1: Using Command Prompt/PowerShell

1. **Open PowerShell or Command Prompt**
   - Press `Win + X` and select "Windows PowerShell" or "Terminal"
   - Or press `Win + R`, type `cmd`, and press Enter

2. **Run this command:**
   ```powershell
   ipconfig
   ```

3. **Look for your Wi-Fi IP address:**
   - Find the section labeled "Wireless LAN adapter Wi-Fi" or "Ethernet adapter"
   - Look for "IPv4 Address" - this is your IP address
   - Example: `IPv4 Address. . . . . . . . . . . . : 10.28.39.17`

### Method 2: Quick Command (Just IP Address)

```powershell
ipconfig | findstr /i "IPv4"
```

This will show only the IPv4 addresses.

### Method 3: Using PowerShell (More Detailed)

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like "*Wi-Fi*" -or $_.InterfaceAlias -like "*Ethernet*"} | Select-Object IPAddress, InterfaceAlias
```

## Finding Your Port (What Ports Are In Use)

### Check if a Specific Port is Available

```powershell
netstat -an | findstr :8765
```

If nothing shows up, the port is free. If you see results, the port is in use.

### See All Listening Ports

```powershell
netstat -an | findstr "LISTENING"
```

### See Ports with Process Names

```powershell
netstat -ano | findstr "LISTENING"
```

Then find the PID (Process ID) and check what it is:
```powershell
tasklist | findstr <PID>
```

### Alternative: Using PowerShell

```powershell
Get-NetTCPConnection | Where-Object {$_.State -eq "Listen"} | Select-Object LocalAddress, LocalPort, OwningProcess | Format-Table
```

## For Your GlaucoGuard Project

### Your Current Configuration:

1. **Backend Server Port:** `8765` (defined in `backend/server.py`)
2. **Mobile App IP:** `10.28.39.17` (in `mobile/App.js` line 15)
3. **UI Development Server:** Port `3000` (or next available: 3001, 3002, etc.)

### To Update Your Mobile App IP:

1. Find your current IP using `ipconfig`
2. Edit `mobile/App.js` line 15:
   ```javascript
   const [serverUrl, setServerUrl] = useState('ws://YOUR_IP_HERE:8765');
   ```
   Replace `YOUR_IP_HERE` with your actual IP address

### Common IP Address Ranges:

- **Home Wi-Fi:** Usually `192.168.x.x` or `10.x.x.x`
- **Localhost:** `127.0.0.1` or `localhost` (only works on same computer)
- **All Interfaces:** `0.0.0.0` (server listens on all network interfaces)

## Quick Reference Commands

```powershell
# Find your IP address
ipconfig | findstr /i "IPv4"

# Check if port 8765 is in use
netstat -an | findstr :8765

# See all listening ports
netstat -an | findstr "LISTENING"

# Find what's using a specific port
netstat -ano | findstr :8765
```

