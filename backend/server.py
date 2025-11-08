#!/usr/bin/env python3
"""
GlaucoGuard Detection Server
WebSocket server for real-time obstacle detection and haptic feedback
"""

import asyncio
import websockets
import json
import random
import base64
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, Any, Optional

# HTTP server for TTS and client downloads
from aiohttp import web, ClientSession

# Image analyzer for Claude API
try:
    from backend.image_analyzer import ImageAnalyzer
    IMAGE_ANALYZER_AVAILABLE = True
except ImportError:
    IMAGE_ANALYZER_AVAILABLE = False
    print("Warning: ImageAnalyzer not available. Image analysis will be disabled.")


class GlaucoGuardServer:
    """Main server class for GlaucoGuard detection system"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.mobile_clients: Set[websockets.WebSocketServerProtocol] = set()  # Phone camera clients
        self.client_types: Dict[websockets.WebSocketServerProtocol, bool] = {}  # Track if client is mobile
        self.client_streaming: Dict[websockets.WebSocketServerProtocol, bool] = {}  # Track which mobile clients are streaming
        self.detection_active = False
        self.latest_frame: str = None  # Store latest video frame from phone
        self.streaming_active = False  # Track if mobile client is actively streaming
        self.explicitly_stopped = False  # Track if streaming was explicitly stopped (prevents re-enabling)
        
        # Setup tmp directory for saving photos
        self.tmp_dir = Path(__file__).parent.parent / "tmp"
        self.tmp_dir.mkdir(exist_ok=True)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Photos will be saved to: {self.tmp_dir}")
        
        # Photo saving throttling - save every 5 seconds
        self.last_photo_save_time = 0
        self.photo_save_interval = 5.0  # seconds
        
        # ElevenLabs configuration
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
        self.ELEVENLABS_API_BASE = os.getenv("ELEVENLABS_API_BASE", "https://api.elevenlabs.io/v1")
        
        # Local cache folder for generated audio
        self.tts_cache_dir = Path(__file__).parent / "tts_cache"
        try:
            self.tts_cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        # Initialize image analyzer if available
        self.image_analyzer = None
        if IMAGE_ANALYZER_AVAILABLE:
            try:
                self.image_analyzer = ImageAnalyzer()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Image analyzer initialized")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Could not initialize image analyzer: {e}")

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
            # Pre-serialize message once for faster broadcasting (skip timestamp for speed)
            message_json = json.dumps({
                "type": "video_frame",
                "data": frame_data
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

    def _save_photo_sync(self, base64_data: str, timestamp: int = None) -> Optional[Path]:
        """Synchronous photo saving (runs in executor to avoid blocking)"""
        try:
            if not base64_data:
                return None
            
            # Use provided timestamp or generate one
            if timestamp is None:
                timestamp = int(datetime.now().timestamp() * 1000)
            
            # Create filename with timestamp
            filename = f"photo_{timestamp}.jpg"
            filepath = self.tmp_dir / filename
            
            # Decode base64 and save
            image_data = base64.b64decode(base64_data)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Photo saved: {filepath}")
            return filepath
        except Exception as e:
            # Log error but don't break streaming
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error saving photo: {e}")
            return None
    
    def should_save_photo(self) -> bool:
        """Check if enough time has passed to save a photo (throttling)"""
        current_time = datetime.now().timestamp()
        if current_time - self.last_photo_save_time >= self.photo_save_interval:
            self.last_photo_save_time = current_time
            return True
        return False
    
    async def generate_tts(self, text: str, voice: str = "alloy") -> Optional[str]:
        """
        Generate TTS via ElevenLabs, save to cache and return filename (relative to tts_cache dir).
        Returns None on failure.
        """
        if not self.ELEVENLABS_API_KEY:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ELEVENLABS_API_KEY not set - cannot generate TTS")
            return None

        # Create deterministic filename from text+voice
        h = hashlib.sha1()
        h.update((voice + "|" + text).encode("utf-8"))
        filename = f"tts_{h.hexdigest()}.mp3"
        out_path = self.tts_cache_dir / filename

        # If cached, return immediately
        if out_path.exists():
            return filename

        tts_url = f"{self.ELEVENLABS_API_BASE}/text-to-speech/{voice}"
        headers = {
            "Authorization": f"Bearer {self.ELEVENLABS_API_KEY}",
            "Accept": "audio/mpeg",
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        try:
            async with ClientSession() as session:
                async with session.post(tts_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ElevenLabs TTS error: {resp.status} {txt}")
                        return None
                    data = await resp.read()
                    try:
                        out_path.write_bytes(data)
                        return filename
                    except Exception as e:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to write TTS file: {e}")
                        return None
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Exception calling ElevenLabs: {e}")
            return None

    async def analyze_image_and_generate_tts(self, image_path: Path):
        """Analyze image and generate TTS from the analysis (async, non-blocking)"""
        if not self.image_analyzer:
            return None
        
        try:
            # Analyze image
            analysis = self.image_analyzer.analyze_image(image_path)
            
            # Create TTS text from scene_description only
            tts_text = analysis.get("scene_description", "Image analyzed")
            
            # Generate TTS
            tts_filename = await self.generate_tts(tts_text)
            if tts_filename:
                # Broadcast TTS URL to web clients
                tts_url = f"http://{self.host}:8080/tts_audio/{tts_filename}"
                message = {
                    "type": "tts_audio",
                    "url": tts_url,
                    "text": tts_text,
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(message, to_mobile=False)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] TTS generated and broadcasted: {tts_text[:50]}...")
                return tts_filename
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error in analyze_image_and_generate_tts: {e}")
            import traceback
            traceback.print_exc()
        return None

    def save_photo_async(self, base64_data: str, timestamp: int = None):
        """Save photo to tmp directory on computer (completely fire-and-forget, non-blocking)"""
        # Only save if enough time has passed (throttling)
        if not self.should_save_photo():
            return
        
        # Save photo in executor, then trigger analysis
        loop = asyncio.get_event_loop()
        def save_photo():
            return self._save_photo_sync(base64_data, timestamp)
        
        def on_photo_saved(future):
            # This callback runs after photo is saved, triggers async analysis
            try:
                filepath = future.result()
                if filepath and self.image_analyzer:
                    # Schedule async task in the event loop (thread-safe)
                    asyncio.run_coroutine_threadsafe(
                        self.analyze_image_and_generate_tts(filepath),
                        loop
                    )
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error in photo save callback: {e}")
        
        try:
            # Save photo in executor
            future = loop.run_in_executor(None, save_photo)
            # When done, trigger analysis
            future.add_done_callback(on_photo_saved)
        except Exception:
            # Silently ignore any errors in task creation - don't affect streaming
            pass

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
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Detection data sent to {len(self.clients)} web client(s) (streaming_active: {self.streaming_active}, explicitly_stopped: {self.explicitly_stopped}, any_client_streaming: {any_client_streaming})")
                else:
                    # Safety check: if streaming_active is True but no clients are streaming, reset it
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: streaming_active=True but no clients streaming, resetting immediately")
                    self.streaming_active = False
            # If not streaming, just wait without sending data
            await asyncio.sleep(0.1)  # Check every 500ms

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
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    # Check if this is a mobile client sending video frames
                    if message_type == "video_frame":
                        # Mark as mobile client if not already (fast path - minimal logging)
                        if not self.client_types.get(websocket, False):
                            # Move from web clients to mobile clients
                            self.clients.discard(websocket)
                            self.mobile_clients.add(websocket)
                            self.client_types[websocket] = True
                            self.client_streaming[websocket] = True  # New client starts streaming
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] Client identified as mobile camera")
                            # Reset streaming_active when a new mobile client connects to prevent stale state
                            if self.streaming_active:
                                self.streaming_active = False
                        elif self.client_types.get(websocket, False) and not self.client_streaming.get(websocket, False):
                            # Client was previously streaming but stopped
                            # CRITICAL: If explicitly_stopped is True, this is a late-arriving frame after stop_streaming
                            # DO NOT reset explicitly_stopped - wait for explicit start_streaming message
                            if self.explicitly_stopped:
                                # Late-arriving frame after stop_streaming - ignore it completely
                                continue  # Skip processing this frame
                            else:
                                # Not explicitly stopped - user wants to resume
                                self.client_streaming[websocket] = True
                                self.explicitly_stopped = False  # Reset when resuming - user wants to stream again
                        
                        # Only process if this websocket is registered as a mobile client AND is marked as streaming
                        if (self.client_types.get(websocket, False) and 
                            websocket in self.mobile_clients and 
                            self.client_streaming.get(websocket, False)):
                            
                            # Fast path: Process video frame immediately
                            frame_data = data.get("data")
                            if not frame_data:
                                continue
                            
                            # Update latest frame for streaming
                            self.latest_frame = frame_data
                            
                            # Broadcast to web clients immediately (do this FIRST, before photo saving)
                            # This ensures video streaming is never interrupted by photo saving
                            try:
                                await self.broadcast_video_frame(frame_data)
                            except Exception as e:
                                # Only log errors, don't spam on every frame
                                pass
                            
                            # Save photo AFTER broadcasting using a COMPLETELY SEPARATE copy of the data
                            # Create an explicit copy to ensure photo saving operations never interfere with streaming
                            photo_data_copy = str(frame_data)  # Explicit copy for photo saving (completely independent)
                            self.save_photo_async(photo_data_copy, data.get("timestamp"))
                            
                            # Enable detection if not explicitly stopped
                            if not self.explicitly_stopped and not self.streaming_active:
                                self.streaming_active = True
                            elif self.explicitly_stopped:
                                self.streaming_active = False
                        # If client is mobile but not streaming, ignore frame silently
                        # (No need to log every skipped frame - would be too verbose)
                    elif message_type == "start_streaming":
                        # User explicitly pressed START STREAMING - reset flags and allow streaming
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] *** START STREAMING MESSAGE RECEIVED - RESUMING STREAMING ***")
                        
                        # Reset flags to allow streaming
                        self.client_streaming[websocket] = True
                        self.explicitly_stopped = False  # Reset - user explicitly wants to stream
                        self.streaming_active = False  # Will be set to True when first video frame arrives
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Streaming resumed - flags reset (explicitly_stopped: {self.explicitly_stopped}, client_streaming: {self.client_streaming.get(websocket, False)})")
                    elif message_type == "stop_streaming":
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
                    elif message_type == "phone_disconnecting":
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

        # Start a small HTTP server (aiohttp) for TTS and audio file serving
        app = web.Application()

        async def tts_route(request):
            """POST /tts
            JSON body: { "text": "...", "voice": "alloy" }
            Returns: audio file (audio/mpeg) or JSON error
            """
            try:
                body = await request.json()
            except Exception:
                return web.json_response({"error": "invalid_json"}, status=400)

            text = body.get("text")
            voice = body.get("voice", "alloy")
            if not text:
                return web.json_response({"error": "missing_text"}, status=400)

            filename = await self.generate_tts(text, voice=voice)
            if not filename:
                return web.json_response({"error": "tts_failed"}, status=502)

            path = self.tts_cache_dir / filename
            if not path.exists():
                return web.json_response({"error": "file_not_found"}, status=500)

            return web.FileResponse(path, headers={"Content-Type": "audio/mpeg"})

        # Add routes
        app.router.add_post("/tts", tts_route)
        app.router.add_static("/tts_audio", str(self.tts_cache_dir), show_index=False)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print(f"HTTP TTS service running on http://0.0.0.0:8080 (endpoints: POST /tts, /tts_audio/<file>)")

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
        server.detection_active = False


if __name__ == "__main__":
    asyncio.run(main())
