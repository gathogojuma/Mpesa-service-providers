from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, business_id: str):
        await websocket.accept()
        if business_id not in self.active_connections:
            self.active_connections[business_id] = []
        self.active_connections[business_id].append(websocket)

    def disconnect(self, websocket: WebSocket, business_id: str):
        if business_id in self.active_connections:
            self.active_connections[business_id].remove(websocket)
            if not self.active_connections[business_id]:
                del self.active_connections[business_id]

    async def broadcast(self, event_type: str, data: dict, business_id: str = None):
        """Broadcast to all connections or to a specific business"""
        message = {"type": event_type, "data": data}
        if business_id:
            connections = self.active_connections.get(business_id, [])
        else:
            # Broadcast to all businesses
            connections = []
            for conns in self.active_connections.values():
                connections.extend(conns)

        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, business_id: str):
    await manager.connect(websocket, business_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, business_id)
