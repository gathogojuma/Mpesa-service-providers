"""
WebSocket connection manager for real-time updates.

Provides a simple pub/sub mechanism so the merchant dashboard can
receive live notifications (e.g., new payment received, flagged event).

Each business (tenant) has its own channel; broadcasts can be scoped
to a single business or sent platform-wide.
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json


class ConnectionManager:
    """Tracks active WebSocket connections, grouped by business_id."""

    def __init__(self):
        # business_id -> list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, business_id: str):
        """Accept a new connection and register it under the business."""
        await websocket.accept()
        if business_id not in self.active_connections:
            self.active_connections[business_id] = []
        self.active_connections[business_id].append(websocket)

    def disconnect(self, websocket: WebSocket, business_id: str):
        """Remove a connection when the client disconnects."""
        if business_id in self.active_connections:
            try:
                self.active_connections[business_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[business_id]:
                del self.active_connections[business_id]

    async def broadcast(
        self,
        event_type: str,
        data: dict,
        business_id: str = None
    ):
        """
        Send a message to all connections.

        If business_id is provided, only sends to that business's clients.
        Otherwise, sends to every connected client (platform-wide).
        """
        message = json.dumps({"type": event_type, "data": data})

        if business_id:
            targets = self.active_connections.get(business_id, [])
        else:
            targets = []
            for conns in self.active_connections.values():
                targets.extend(conns)

        # Send to each; drop dead connections silently
        dead = []
        for connection in targets:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)

        # Clean up any broken sockets
        for connection in dead:
            for biz_id, conns in list(self.active_connections.items()):
                if connection in conns:
                    conns.remove(connection)
                    if not conns:
                        del self.active_connections[biz_id]


# Module-level singleton used by the rest of the app
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, business_id: str):
    """
    WebSocket endpoint handler.

    Clients connect to `/ws?business_id=<id>` to receive real-time events
    for their business. The server echoes incoming messages back for now;
    real events are pushed via `manager.broadcast(...)` from other parts
    of the app (e.g., the M-Pesa webhook).
    """
    await manager.connect(websocket, business_id)
    try:
        while True:
            # Wait for messages from client (used as a keep-alive)
            data = await websocket.receive_text()
            # Echo back so clients can confirm the connection is alive
            await websocket.send_text(
                json.dumps({"type": "echo", "data": {"received": data}})
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, business_id)
    except Exception:
        manager.disconnect(websocket, business_id)
