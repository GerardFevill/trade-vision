"""WebSocket service for real-time updates"""
import asyncio
import json
from typing import Set
from datetime import datetime
from fastapi import WebSocket
from config.logging import logger


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info("WebSocket disconnected", total_connections=len(self.active_connections))

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("Error sending personal message", error=str(e))
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning("Error broadcasting to client", error=str(e))
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_dashboard_update(self, mt5_connector):
        """Broadcast dashboard data to all clients"""
        try:
            dashboard = mt5_connector.get_full_dashboard()
            if dashboard:
                message = {
                    "type": "dashboard_update",
                    "data": dashboard.model_dump(),
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(message)
        except Exception as e:
            logger.error("Error broadcasting dashboard update", error=str(e))

    async def broadcast_status_update(self, mt5_connector):
        """Broadcast connection status to all clients"""
        try:
            status = mt5_connector.get_connection_status()
            if status:
                message = {
                    "type": "status_update",
                    "data": status.model_dump(),
                    "timestamp": datetime.now().isoformat()
                }
                await self.broadcast(message)
        except Exception as e:
            logger.error("Error broadcasting status update", error=str(e))

    async def start_periodic_broadcast(self, mt5_connector, interval: int = 5):
        """Start periodic broadcasting of updates"""
        logger.info("Starting periodic WebSocket broadcast", interval_seconds=interval)
        while True:
            try:
                if self.active_connections:
                    await self.broadcast_dashboard_update(mt5_connector)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("Periodic broadcast cancelled")
                break
            except Exception as e:
                logger.error("Error in periodic broadcast", error=str(e))
                await asyncio.sleep(interval)


# Global connection manager
ws_manager = ConnectionManager()
