from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, dict[str, set[WebSocket]]] = defaultdict(lambda: defaultdict(set))
        self.user_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect_to_conversation(self, conversation_id: int, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[conversation_id][user_id].add(websocket)

    def disconnect_from_conversation(self, conversation_id: int, user_id: str, websocket: WebSocket) -> bool:
        user_connections = self.active_connections.get(conversation_id, {}).get(user_id)
        if not user_connections:
            return False

        user_connections.discard(websocket)
        user_offline = len(user_connections) == 0
        if user_offline:
            self.active_connections[conversation_id].pop(user_id, None)
        if not self.active_connections.get(conversation_id):
            self.active_connections.pop(conversation_id, None)
        return user_offline

    async def connect_user(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.user_connections[user_id].add(websocket)

    def disconnect_user(self, user_id: str, websocket: WebSocket) -> None:
        connections = self.user_connections.get(user_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self.user_connections.pop(user_id, None)

    async def broadcast_to_user(self, user_id: str, payload: dict) -> None:
        for websocket in list(self.user_connections.get(user_id, set())):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                self.user_connections[user_id].discard(websocket)

    async def broadcast_to_conversation(self, conversation_id: int, payload: dict) -> None:
        conversation_connections = list(self.active_connections.get(conversation_id, {}).items())
        for _, sockets in conversation_connections:
            for websocket in list(sockets):
                try:
                    await websocket.send_json(payload)
                except RuntimeError:
                    sockets.discard(websocket)

    async def broadcast_to_others(self, conversation_id: int, sender_id: str, payload: dict) -> None:
        conversation_connections = list(self.active_connections.get(conversation_id, {}).items())
        for user_id, sockets in conversation_connections:
            if user_id == sender_id:
                continue
            for websocket in list(sockets):
                try:
                    await websocket.send_json(payload)
                except RuntimeError:
                    sockets.discard(websocket)


manager = ConnectionManager()
