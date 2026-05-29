import json
import asyncio
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("sdo.backend.workers.websocket")

class JobWebSocketManager:
    """
    Coordinates WebSocket pools for SDO.
    Pushes low-latency, real-time chemical telemetry states to the React client.
    """
    def __init__(self):
        # Client ID -> WebSocket mapping
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """Accepts and caches client WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket Connected: Client '{client_id}' registered successfully. Pool size: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """Safely removes client socket from connection pools."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket Disconnected: Client '{client_id}' removed. Pool size: {len(self.active_connections)}")

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Sends a JSON-serializable message to a specific client with fail-safe drops."""
        if client_id not in self.active_connections:
            return False
            
        websocket = self.active_connections[client_id]
        try:
            # Compress and push raw text frames to shrink network size
            await websocket.send_text(json.dumps(message))
            return True
        except Exception:
            # Handle socket drops during transmission
            self.disconnect(client_id)
            return False

    async def broadcast(self, message: Dict[str, Any]):
        """Pushes real-time progress events to all active dashboard sessions simultaneously."""
        if not self.active_connections:
            return
            
        payload = json.dumps(message)
        dead_clients: Set[str] = set()
        
        # Concurrently send text updates
        tasks = []
        for client_id, ws in self.active_connections.items():
            async def safe_send(c_id=client_id, socket=ws):
                try:
                    await socket.send_text(payload)
                except Exception:
                    dead_clients.add(c_id)
            tasks.append(safe_send())
            
        if tasks:
            await asyncio.gather(*tasks)
            
        # Clean up dead sockets
        for cid in dead_clients:
            self.disconnect(cid)

    async def start_heartbeat_monitor(self):
        """
        Background task to perform regular ping checks.
        Cleans up stale or orphan client sockets to avoid memory leaks.
        """
        while True:
            await asyncio.sleep(15.0) # Ping every 15 seconds
            if not self.active_connections:
                continue
                
            dead_clients: Set[str] = set()
            for client_id, ws in list(self.active_connections.items()):
                try:
                    # Send a lightweight ping
                    await ws.send_text(json.dumps({"type": "PING"}))
                except Exception:
                    dead_clients.add(client_id)
                    
            for cid in dead_clients:
                self.disconnect(cid)
                
# Global WebSocket singleton
ws_broadcaster = JobWebSocketManager()
