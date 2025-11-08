#!/usr/bin/env python3
"""
GlaucoGuard Detection Server
WebSocket server for real-time obstacle detection and haptic feedback
"""

import asyncio
import websockets
import json
import random
from datetime import datetime
from typing import Set, Dict, Any


class GlaucoGuardServer:
    """Main server class for GlaucoGuard detection system"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.detection_active = False

    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Client connected. Total clients: {len(self.clients)}")

    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client connection"""
        self.clients.discard(websocket)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected clients"""
        if self.clients:
            message_json = json.dumps(message)
            await asyncio.gather(
                *[client.send(message_json) for client in self.clients],
                return_exceptions=True
            )

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
            data = self.simulate_detection()
            await self.broadcast(data)
            await asyncio.sleep(0.5)  # Send updates every 500ms

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle individual client connections"""
        await self.register_client(websocket)

        try:
            # Send initial connection confirmation
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "message": "Connected to GlaucoGuard server"
            }))

            # Listen for client messages (if any)
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle client commands here if needed
                    print(f"Received from client: {data}")
                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message}")

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)

    async def start(self):
        """Start the WebSocket server"""
        print("=" * 50)
        print("GLAUCOGUARD DETECTION SERVER")
        print("=" * 50)
        print(f"Starting server on {self.host}:{self.port}")

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
        server.detection_active = False


if __name__ == "__main__":
    asyncio.run(main())
