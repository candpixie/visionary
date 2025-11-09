#!/usr/bin/env python3
"""
GlaucoGuard Detection Server
WebSocket server for real-time obstacle detection and haptic feedback
"""

import asyncio
import base64
import os
import websockets
import json
import random
from datetime import datetime
from typing import Set, Dict, Any
from analyze_hazard import analyze, ask_question_about_image
import threading
import serial
import time
import sounddevice as sd


TMP_DIR = './tmp'
os.makedirs(TMP_DIR, exist_ok=True)

class GlaucoGuardServer:
    """Main server class for GlaucoGuard detection system"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        #Arduino setup
        self.baud = int(os.getenv("BAUD_RATE", "9600"))
        self.test = False
        self.left_port = os.getenv("LEFT_ARDUINO_PORT", "/dev/cu.usbmodemB0818497DA102")
        self.right_port = os.getenv("RIGHT_ARDUINO_PORT", "/dev/cu.usbmodemB0818499D0202")
        self.left_arduino = self.connect_arduino(self.left_port, "LEFT")
        self.right_arduino = self.connect_arduino(self.right_port, "RIGHT")
        if self.left_arduino:
            threading.Thread(target=self.read_stream, args=(self.left_arduino, "LEFT"), daemon=True).start()
        if self.right_arduino:
            threading.Thread(target=self.read_stream, args=(self.right_arduino, "RIGHT"), daemon=True).start()
        
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.mobile_clients: Set[websockets.WebSocketServerProtocol] = set()  # Phone camera clients
        self.client_types: Dict[websockets.WebSocketServerProtocol, bool] = {}  # Track if client is mobile
        self.client_streaming: Dict[websockets.WebSocketServerProtocol, bool] = {}  # Track which mobile clients are streaming
        self.detection_active = False
        self.left_touch = threading.Event()
        self.right_touch = threading.Event()
        self.touch_detected = threading.Event()
        self.latest_frame: str = None  # Store latest video frame from phone
        self.streaming_active = False  # Track if mobile client is actively streaming
        self.explicitly_stopped = False  # Track if streaming was explicitly stopped (prevents re-enabling)
        self.last_analyze_time: float = 0  # Track last time analyze was called
        self.analyze_interval: float = 10.0  # Minimum seconds between analyze calls


        
    def read_stream(self, arduino, label):
        pressed_state = False  # internal toggle memory

        while arduino and arduino.is_open:
            try:
                line = arduino.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                if "touch=" in line.lower():
                    value = line.split("=")[-1].strip()

                    # Only act when Arduino reports a press
                    if value == "1":
                        pressed_state = not pressed_state  # flip ON/OFF
                        state_str = "ON" if pressed_state else "OFF"
                        print(f"[{label}] Toggled → {state_str}")

                        if pressed_state:
                            # Turn ON for this side
                            if label == "LEFT":
                                self.left_touch.set()
                                # Trigger async question asking MIGHT FUCK SHIT
                                ask_question_about_image()

                                
                            elif label == "RIGHT":
                                self.right_touch.set()
                            self.touch_detected.set()

                        else:
                            # Turn OFF for this side
                            if label == "LEFT":
                                self.left_touch.clear()
                            elif label == "RIGHT":
                                self.right_touch.clear()

                            # If both sides are OFF, resume detection
                            if not (self.left_touch.is_set() or self.right_touch.is_set()):
                                self.touch_detected.clear()
                                print("[SYSTEM] Both OFF → resuming detection")

            except Exception as e:
                print(f"[{label}] Error: {e}")
                break

    def connect_arduino(self, port, label):
        try:
            arduino = serial.Serial(port, self.baud, timeout=0.1)
            print(f"[{label}] Connected.")
            return arduino
        except Exception as e:
            print(f"[{label}] Connection failed: {e}")
            return None

    async def register_client(self, websocket: websockets.WebSocketServerProtocol, is_mobile: bool = False):
        """Register a new client connection"""
        self.client_types[websocket] = is_mobile
        if is_mobile:
            self.mobile_clients.add(websocket)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Mobile client (camera) connected. Total mobile clients: {len(self.mobile_clients)}")
            # Don't set streaming_active here - wait for first video frame
        else:
            self.clients.add(websocket)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Web client connected. Total web clients: {len(self.clients)}")

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client connection"""
        is_mobile = self.client_types.get(websocket, False)
        if is_mobile:
            self.mobile_clients.discard(websocket)
            self.client_streaming.pop(websocket, None)  # Remove streaming status
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Mobile client disconnected. Total mobile clients: {len(self.mobile_clients)}")
            
            # Check if any mobile client is still streaming
            any_streaming = any(self.client_streaming.get(client, False) for client in self.mobile_clients)
            was_streaming = self.streaming_active
            self.streaming_active = any_streaming
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Streaming stopped - mobile client disconnected (was streaming: {was_streaming}, now: {self.streaming_active})")
            
            # Notify web clients that phone disconnected
            try:
                disconnect_message = {
                    "type": "phone_disconnected",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Phone disconnected from server"
                }
                await self.broadcast(disconnect_message, to_mobile=False)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Phone disconnect notification sent to {len(self.clients)} web client(s)")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error notifying web clients of phone disconnect: {e}")
        else:
            self.clients.discard(websocket)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Web client disconnected. Total web clients: {len(self.clients)}")
        self.client_types.pop(websocket, None)

    async def broadcast(self, message: Dict[str, Any], to_mobile: bool = False):
        """Send message to all connected clients"""
        target_clients = self.mobile_clients if to_mobile else self.clients
        if target_clients:
            message_json = json.dumps(message)
            await asyncio.gather(
                *[client.send(message_json) for client in target_clients],
                return_exceptions=True
            )
    
    async def broadcast_video_frame(self, frame_data: str):
        """Broadcast video frame to all web clients - optimized for maximum speed"""
        if self.clients and frame_data:
            # Pre-serialize message once for faster broadcasting
            message_json = json.dumps({
                "type": "video_frame",
                "data": frame_data,
                "timestamp": datetime.now().isoformat()
            })
            
            # Send to all web clients in parallel for maximum speed
            disconnected = set()
            tasks = []
            clients_list = list(self.clients)  # Convert to list to avoid set modification during iteration
            
            for client in clients_list:
                try:
                    # Create send tasks for parallel execution
                    tasks.append(client.send(message_json))
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error preparing video frame send: {e}")
                    disconnected.add(client)
            
            # Wait for all sends to complete in parallel (much faster than sequential)
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        disconnected.add(clients_list[i])
            
            # Clean up disconnected clients
            for client in disconnected:
                self.clients.discard(client)
                self.client_types.pop(client, None)

    async def save_image_async(self, image_base64: str, filename: str):
        """Async function to save a base64 image to disk"""
        image_data = base64.b64decode(image_base64)
        path = os.path.join(TMP_DIR, filename)
        loop = asyncio.get_running_loop()
        # Run blocking I/O in executor to avoid blocking the event loop
        await loop.run_in_executor(None, lambda: open(path, 'wb').write(image_data))
        # print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved image to {path}")

    def simulate_detection(self) -> Dict[str, Any]:
        """
        Simulate obstacle detection data
        In production, this would connect to actual sensors/cameras
        """
        # Simulate random obstacles with varying distances
        left_distance = random.randint(50, 300) if random.random() > 0.7 else None
        center_distance = random.randint(50, 300) if random.random() > 0.7 else None
        right_distance = random.randint(50, 300) if random.random() > 0.7 else None

        # Determine if any obstacle is in danger zone (< 200cm)
        has_detection = any(
            d is not None and d < 200
            for d in [left_distance, center_distance, right_distance]
        )

        # Determine haptic feedback zone
        haptic = "none"
        if left_distance is not None and left_distance < 200:
            haptic = "left"
        elif center_distance is not None and center_distance < 200:
            haptic = "center"
        elif right_distance is not None and right_distance < 200:
            haptic = "right"

        return {
            "timestamp": datetime.now().isoformat(),
            "detection": has_detection,
            "zones": {
                "left": left_distance,
                "center": center_distance,
                "right": right_distance
            },
            "haptic": haptic
        }

    async def detection_loop(self):
        """Continuously generate and broadcast detection data"""
        self.detection_active = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Detection loop started")

        while self.detection_active:
            # CRITICAL: Check explicitly_stopped FIRST - if True, NEVER send detection data
            # This ensures stop_streaming works exactly like disconnect
            if self.explicitly_stopped:
                # Explicitly stopped - wait and check again, don't send anything
                await asyncio.sleep(0.5)
                continue
            
            # CRITICAL: Check streaming_active SECOND - if False, don't send ANY detection data
            if not self.streaming_active:
                # Not streaming - wait and check again, don't send anything
                await asyncio.sleep(0.5)
                continue
            
            # FINAL CHECK: Verify both flags are correct before proceeding
            # If either is wrong, skip this iteration
            if self.explicitly_stopped or not self.streaming_active:
                await asyncio.sleep(0.5)
                continue
            
            # Only proceed if ALL conditions are met:
            # 1. streaming_active is True
            # 2. explicitly_stopped is False
            # 3. We have web clients
            # 4. We have mobile clients
            # 5. At least one mobile client is actually streaming
            if (self.streaming_active and 
                not self.explicitly_stopped and
                self.clients and 
                self.mobile_clients):
                # Double-check that at least one client is actually streaming (safety check)
                any_client_streaming = any(self.client_streaming.get(client, False) for client in self.mobile_clients)
                if any_client_streaming:
                    data = self.simulate_detection()
                    await self.broadcast(data)
                    # print(f"[{datetime.now().strftime('%H:%M:%S')}] Detection data sent to {len(self.clients)} web client(s) (streaming_active: {self.streaming_active}, explicitly_stopped: {self.explicitly_stopped}, any_client_streaming: {any_client_streaming})")
                else:
                    # Safety check: if streaming_active is True but no clients are streaming, reset it
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: streaming_active=True but no clients streaming, resetting immediately")
                    self.streaming_active = False
            # If not streaming, just wait without sending data
            await asyncio.sleep(0.5)  # Check every 500ms

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str = None):
        """Handle individual client connections"""
        # Initially register as web client, will be updated if mobile sends video frames
        await self.register_client(websocket, is_mobile=False)

        try:
            # Send initial connection confirmation
            try:
                await websocket.send(json.dumps({
                    "type": "connection",
                    "status": "connected",
                    "message": "Connected to GlaucoGuard server"
                }))
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error sending initial message: {e}")
                return

            # Listen for client messages
            # wrapped in a touch stream ->
            # bool = 0
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Debug: Log all incoming messages to see what we're receiving
                    if data.get("type") in ["stop_streaming", "video_frame", "phone_disconnecting"]:
                        # print(f"[{datetime.now().strftime('%H:%M:%S')}] Received message type: {data.get('type')} from client")
                        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                        asyncio.create_task(self.save_image_async(data["data"], filename))
                        
                        # Only analyze every 10 seconds
                        current_time = asyncio.get_event_loop().time()
                        if not self.touch_detected.is_set() and current_time - self.last_analyze_time >= self.analyze_interval:
                            self.last_analyze_time = current_time
                            asyncio.create_task(analyze(
                                    data["data"],
                                    encoded=True,
                                    left_arduino=self.left_arduino,
                                    right_arduino=self.right_arduino,
                                    test=self.test
                                ))

                    
                    # Check if this is a mobile client sending video frames
                    if data.get("type") == "video_frame":
                        # Mark as mobile client if not already
                        if not self.client_types.get(websocket, False):
                            # Move from web clients to mobile clients
                            self.clients.discard(websocket)
                            self.mobile_clients.add(websocket)
                            self.client_types[websocket] = True
                            self.client_streaming[websocket] = True  # New client starts streaming
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Client identified as mobile camera")
                            # Reset streaming_active when a new mobile client connects to prevent stale state
                            if self.streaming_active:
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Resetting streaming_active for new mobile client connection")
                                self.streaming_active = False
                        elif self.client_types.get(websocket, False) and not self.client_streaming.get(websocket, False):
                            # Client was previously streaming but stopped
                            # CRITICAL: If explicitly_stopped is True, this is a late-arriving frame after stop_streaming
                            # DO NOT reset explicitly_stopped - wait for explicit start_streaming message
                            if self.explicitly_stopped:
                                # Late-arriving frame after stop_streaming - ignore it completely
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Received late video_frame after stop_streaming - IGNORING (explicitly_stopped: {self.explicitly_stopped})")
                                # Don't set client_streaming or reset explicitly_stopped - wait for start_streaming message
                            else:
                                # Not explicitly stopped - user wants to resume
                                self.client_streaming[websocket] = True
                                self.explicitly_stopped = False  # Reset when resuming - user wants to stream again
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Mobile client resumed streaming - resetting explicitly_stopped (explicitly_stopped: {self.explicitly_stopped})")
                        
                        # Only process if this websocket is registered as a mobile client AND is marked as streaming
                        if (self.client_types.get(websocket, False) and 
                            websocket in self.mobile_clients and 
                            self.client_streaming.get(websocket, False)):
                            
                            # CRITICAL: If explicitly stopped, NEVER re-enable detection, even if video frames arrive
                            # Check this FIRST before doing anything else
                            if self.explicitly_stopped:
                                # Streaming was explicitly stopped - show video but NEVER enable detection
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] Received video_frame but explicitly_stopped=True - showing video but NOT enabling detection (streaming_active: {self.streaming_active})")
                                # Update latest frame and broadcast to web clients (for display only)
                                self.latest_frame = data.get("data")
                                try:
                                    await self.broadcast_video_frame(self.latest_frame)
                                except Exception as e:
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error broadcasting video frame: {e}")
                                # DO NOT enable detection - explicitly_stopped means stay stopped
                                # FORCE streaming_active to False if it somehow got set to True
                                if self.streaming_active:
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: streaming_active was True but explicitly_stopped=True - FORCING to False")
                                    self.streaming_active = False
                            else:
                                # Not explicitly stopped - normal operation
                                # Update latest frame and broadcast to web clients
                                self.latest_frame = data.get("data")
                                try:
                                    await self.broadcast_video_frame(self.latest_frame)
                                except Exception as e:
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error broadcasting video frame: {e}")
                                
                                # Enable detection if not already enabled AND not explicitly stopped
                                # Double-check explicitly_stopped to prevent any race conditions
                                if not self.streaming_active and not self.explicitly_stopped:
                                    self.streaming_active = True
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Streaming started - detection updates enabled (streaming_active: {self.streaming_active}, explicitly_stopped: {self.explicitly_stopped})")
                                elif self.explicitly_stopped:
                                    print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: Attempted to enable detection but explicitly_stopped=True - blocking and forcing streaming_active=False")
                                    self.streaming_active = False
                        elif self.client_types.get(websocket, False) and websocket in self.mobile_clients:
                            # Client is mobile but not marked as streaming - ignore frame (stopped)
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Received video_frame from stopped mobile client, ignoring (client_streaming=False)")
                        elif self.client_types.get(websocket, False) and not self.client_streaming.get(websocket, False):
                            # Client was stopped - ignore any frames
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Received video_frame from stopped client, ignoring completely")
                        else:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: Received video_frame from non-mobile client, ignoring")
                    elif data.get("type") == "start_streaming":
                        # User explicitly pressed START STREAMING - reset flags and allow streaming
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] *** START STREAMING MESSAGE RECEIVED - RESUMING STREAMING ***")
                        
                        # Reset flags to allow streaming
                        self.client_streaming[websocket] = True
                        self.explicitly_stopped = False  # Reset - user explicitly wants to stream
                        self.streaming_active = False  # Will be set to True when first video frame arrives
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Streaming resumed - flags reset (explicitly_stopped: {self.explicitly_stopped}, client_streaming: {self.client_streaming.get(websocket, False)})")
                    elif data.get("type") == "stop_streaming":
                        # Stop streaming - work EXACTLY like disconnect
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] *** STOP STREAMING MESSAGE RECEIVED - WORKING LIKE DISCONNECT ***")
                        
                        # Do EXACTLY what disconnect does:
                        # 1. Mark client as not streaming
                        self.client_streaming[websocket] = False
                        
                        # 2. Check if any mobile client is still streaming (for logging)
                        any_streaming = any(self.client_streaming.get(client, False) for client in self.mobile_clients)
                        was_streaming = self.streaming_active
                        
                        # 3. Set streaming_active to False (same as disconnect)
                        self.streaming_active = False
                        self.explicitly_stopped = True  # Also set this to prevent any re-enabling
                        
                        # 4. Clear latest frame
                        self.latest_frame = None
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Streaming stopped - detection updates COMPLETELY STOPPED (was streaming: {was_streaming}, now: {self.streaming_active}, any_streaming: {any_streaming})")
                        
                        # 5. Broadcast stop message to web clients (like phone_disconnected)
                        try:
                            stop_message = {
                                "type": "stop_streaming",
                                "timestamp": datetime.now().isoformat(),
                                "message": "Streaming stopped - camera paused"
                            }
                            await self.broadcast(stop_message, to_mobile=False)
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Stop message broadcasted to {len(self.clients)} web client(s)")
                        except Exception as e:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error broadcasting stop message: {e}")
                            import traceback
                            traceback.print_exc()
                    elif data.get("type") == "phone_disconnecting":
                        # Phone is disconnecting - notify web clients immediately
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Phone disconnecting message received")
                        # Mark this client as not streaming
                        self.client_streaming[websocket] = False
                        
                        # Check if any mobile client is still streaming
                        any_streaming = any(self.client_streaming.get(client, False) for client in self.mobile_clients)
                        was_streaming = self.streaming_active
                        self.streaming_active = any_streaming
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Streaming stopped - phone disconnecting (was streaming: {was_streaming}, now: {self.streaming_active}, any_streaming: {any_streaming})")
                        
                        # Notify web clients that phone is disconnecting
                        try:
                            disconnect_message = {
                                "type": "phone_disconnected",
                                "timestamp": datetime.now().isoformat(),
                                "message": "Phone disconnected from server"
                            }
                            await self.broadcast(disconnect_message, to_mobile=False)
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Phone disconnect notification sent to {len(self.clients)} web client(s)")
                        except Exception as e:
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error notifying web clients: {e}")
                    else:
                        # Handle other client commands
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Received from client: {data}")
                        
                except json.JSONDecodeError as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Invalid JSON received: {message[:100]}... Error: {e}")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection closed normally: {e}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected error in handle_client: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.unregister_client(websocket)
            
    def cleanup(self):
        for arduino, label in [(self.left_arduino, "LEFT"), (self.right_arduino, "RIGHT")]:
            if arduino and arduino.is_open:
                arduino.close()
                print(f"[{label}] Closed.")

    async def start(self):
        """Start the WebSocket server"""
        print("=" * 50)
        print("GLAUCOGUARD DETECTION SERVER")
        print("=" * 50)
        print(f"Starting server on {self.host}:{self.port}")
        print("Note: Server is listening on 0.0.0.0 to accept connections from mobile devices")
        print("Make sure your phone and laptop are on the same network")

        # Start the detection loop
        detection_task = asyncio.create_task(self.detection_loop())

        # Start the WebSocket server
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"Server running on ws://{self.host}:{self.port}")
            print("Waiting for connections...")
            print("Press Ctrl+C to stop")
            print("=" * 50)

            await asyncio.Future()  # Run forever


async def main():
    """Main entry point"""
    server = GlaucoGuardServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.cleanup()
        print("Server stopped.")
        server.detection_active = False


if __name__ == "__main__":
    asyncio.run(main())
