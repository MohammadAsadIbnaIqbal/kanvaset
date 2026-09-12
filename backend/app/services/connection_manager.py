import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
from backend.app.core.redis import redis_service
from backend.app.schemas.ws_messages import WSMessage, WSMessageType

logger = logging.getLogger("kanvaset.ws_manager")


class ClientConnection:
    def __init__(self, websocket: WebSocket, user_id: str, username: str, role: str, color: str):
        self.websocket = websocket
        self.user_id = user_id
        self.username = username
        self.role = role
        self.color = color


class BoardConnectionManager:
    def __init__(self):
        # board_id -> list of ClientConnection
        self._board_connections: Dict[str, List[ClientConnection]] = {}
        # board_id -> background asyncio.Task listening to Redis Pub/Sub
        self._pubsub_tasks: Dict[str, asyncio.Task] = {}
        # lock for thread-safe/async modifications
        self._lock = asyncio.Lock()

    async def connect(
        self,
        board_id: str,
        websocket: WebSocket,
        user_id: str,
        username: str,
        role: str,
        color: str
    ) -> ClientConnection:
        await websocket.accept()
        client = ClientConnection(
            websocket=websocket,
            user_id=user_id,
            username=username,
            role=role,
            color=color
        )

        async with self._lock:
            if board_id not in self._board_connections:
                self._board_connections[board_id] = []
                # Start Redis pubsub listener task for this board
                self._pubsub_tasks[board_id] = asyncio.create_task(
                    self._listen_to_board_channel(board_id)
                )
            self._board_connections[board_id].append(client)

        # Register presence in Redis / broker
        user_presence = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "color": color,
        }
        await redis_service.add_presence(board_id, user_id, user_presence)

        # Broadcast USER_JOINED to room
        join_msg = WSMessage(
            type=WSMessageType.USER_JOINED,
            board_id=board_id,
            user_id=user_id,
            user_name=username,
            user_color=color,
            payload={"user": user_presence}
        )
        await self.broadcast_global(board_id, join_msg.model_dump())

        logger.info(
            "User %s (%s) connected to board %s. Local board clients: %d",
            username, user_id, board_id, len(self._board_connections[board_id])
        )
        return client

    async def disconnect(self, board_id: str, client: ClientConnection) -> None:
        remaining_clients = 0
        user_has_other_connections = False

        async with self._lock:
            if board_id in self._board_connections:
                if client in self._board_connections[board_id]:
                    self._board_connections[board_id].remove(client)
                
                # Check if this user still has another open tab/socket on this board
                for conn in self._board_connections[board_id]:
                    if conn.user_id == client.user_id:
                        user_has_other_connections = True
                        break

                remaining_clients = len(self._board_connections[board_id])
                if remaining_clients == 0:
                    del self._board_connections[board_id]
                    task = self._pubsub_tasks.pop(board_id, None)
                    if task and not task.done():
                        task.cancel()

        # If user has disconnected all sockets, remove from presence and notify
        if not user_has_other_connections:
            await redis_service.remove_presence(board_id, client.user_id)
            leave_msg = WSMessage(
                type=WSMessageType.USER_LEFT,
                board_id=board_id,
                user_id=client.user_id,
                user_name=client.username,
                user_color=client.color,
                payload={"user_id": client.user_id}
            )
            await self.broadcast_global(board_id, leave_msg.model_dump())

        logger.info(
            "User %s disconnected from board %s. Local board clients left: %d",
            client.username, board_id, remaining_clients
        )

    async def broadcast_local(
        self,
        board_id: str,
        message_dict: dict,
        exclude_ws: Optional[WebSocket] = None
    ) -> None:
        conns = list(self._board_connections.get(board_id, []))
        if not conns:
            return

        payload_str = json.dumps(message_dict)
        dead_conns = []
        is_ephemeral_or_join = message_dict.get("type") in ["CURSOR_MOVED", "USER_JOINED"]
        sender_id = message_dict.get("user_id")

        for conn in conns:
            if exclude_ws and conn.websocket == exclude_ws:
                continue
            if is_ephemeral_or_join and conn.user_id == sender_id:
                # Do not echo cursor or user_joined back to the user
                continue
            try:
                await conn.websocket.send_text(payload_str)
            except Exception as e:
                logger.warning("Failed to send message to client %s: %s", conn.user_id, e)
                dead_conns.append(conn)

        if dead_conns:
            async with self._lock:
                for dead in dead_conns:
                    if board_id in self._board_connections and dead in self._board_connections[board_id]:
                        self._board_connections[board_id].remove(dead)

    async def broadcast_global(self, board_id: str, message_dict: dict) -> None:
        """Publishes to Redis pubsub so all backend instances broadcast to their local clients."""
        channel = f"board:{board_id}:events"
        await redis_service.publish_event(channel, message_dict)

    async def _listen_to_board_channel(self, board_id: str) -> None:
        channel = f"board:{board_id}:events"
        try:
            sub = await redis_service.subscribe_channel(channel)
            if hasattr(sub, "listen"):
                # Redis pubsub object
                async for message in sub.listen():
                    if message["type"] == "message":
                        data = json.loads(message["data"])
                        await self.broadcast_local(board_id, data)
            elif isinstance(sub, asyncio.Queue):
                # InMemoryEventBroker queue
                while True:
                    msg_str = await sub.get()
                    data = json.loads(msg_str)
                    await self.broadcast_local(board_id, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in board channel listener for %s: %s", board_id, e)


manager = BoardConnectionManager()
