import asyncio
import json
import logging
from typing import AsyncGenerator, Callable, Dict, Optional, Set
import redis.asyncio as aioredis
from backend.app.core.config import settings

logger = logging.getLogger("kanvaset.redis")


class InMemoryEventBroker:
    """Fallback in-memory pub-sub broker when Redis is unavailable."""
    def __init__(self):
        self._channels: Dict[str, Set[asyncio.Queue]] = {}
        self._presence: Dict[str, Dict[str, dict]] = {}  # board_id -> user_id -> user_data
        self._seen_ops: Set[str] = set()

    async def publish(self, channel: str, message: str) -> int:
        if channel not in self._channels:
            return 0
        queues = list(self._channels[channel])
        for q in queues:
            await q.put(message)
        return len(queues)

    async def subscribe(self, channel: str) -> asyncio.Queue:
        if channel not in self._channels:
            self._channels[channel] = set()
        q = asyncio.Queue()
        self._channels[channel].add(q)
        return q

    async def unsubscribe(self, channel: str, q: asyncio.Queue) -> None:
        if channel in self._channels and q in self._channels[channel]:
            self._channels[channel].remove(q)
            if not self._channels[channel]:
                del self._channels[channel]

    async def add_presence(self, board_id: str, user_id: str, user_data: dict) -> None:
        if board_id not in self._presence:
            self._presence[board_id] = {}
        self._presence[board_id][user_id] = user_data

    async def remove_presence(self, board_id: str, user_id: str) -> None:
        if board_id in self._presence and user_id in self._presence[board_id]:
            del self._presence[board_id][user_id]
            if not self._presence[board_id]:
                del self._presence[board_id]

    async def get_presence(self, board_id: str) -> list:
        if board_id in self._presence:
            return list(self._presence[board_id].values())
        return []

    async def is_operation_seen(self, op_id: str) -> bool:
        if op_id in self._seen_ops:
            return True
        self._seen_ops.add(op_id)
        # Cap size to prevent unbounded memory growth
        if len(self._seen_ops) > 50000:
            self._seen_ops.clear()
        return False


class RedisService:
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.in_memory = InMemoryEventBroker()
        self.is_connected = False

    async def connect(self) -> None:
        if not settings.USE_REDIS:
            logger.info("USE_REDIS is disabled; using InMemoryEventBroker.")
            return

        try:
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            await client.ping()
            self.redis_client = client
            self.is_connected = True
            logger.info("Connected to Redis successfully at %s", settings.REDIS_URL)
        except Exception as e:
            logger.warning("Could not connect to Redis (%s). Falling back to InMemoryEventBroker.", e)
            self.redis_client = None
            self.is_connected = False

    async def disconnect(self) -> None:
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            self.is_connected = False

    async def publish_event(self, channel: str, data: dict) -> None:
        payload = json.dumps(data)
        if self.is_connected and self.redis_client:
            try:
                await self.redis_client.publish(channel, payload)
                return
            except Exception as e:
                logger.error("Redis publish failed (%s), falling back to in-memory", e)
        await self.in_memory.publish(channel, payload)

    async def subscribe_channel(self, channel: str):
        """Returns an async iterator for incoming channel messages."""
        if self.is_connected and self.redis_client:
            try:
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe(channel)
                return pubsub
            except Exception as e:
                logger.error("Redis subscribe failed (%s), falling back to in-memory", e)
        return await self.in_memory.subscribe(channel)

    async def add_presence(self, board_id: str, user_id: str, user_data: dict) -> None:
        if self.is_connected and self.redis_client:
            try:
                key = f"presence:{board_id}"
                await self.redis_client.hset(key, user_id, json.dumps(user_data))
                await self.redis_client.expire(key, 86400)
                return
            except Exception as e:
                logger.error("Redis presence set failed (%s)", e)
        await self.in_memory.add_presence(board_id, user_id, user_data)

    async def remove_presence(self, board_id: str, user_id: str) -> None:
        if self.is_connected and self.redis_client:
            try:
                key = f"presence:{board_id}"
                await self.redis_client.hdel(key, user_id)
                return
            except Exception as e:
                logger.error("Redis presence remove failed (%s)", e)
        await self.in_memory.remove_presence(board_id, user_id)

    async def get_presence(self, board_id: str) -> list:
        if self.is_connected and self.redis_client:
            try:
                key = f"presence:{board_id}"
                data = await self.redis_client.hgetall(key)
                return [json.loads(v) for v in data.values()]
            except Exception as e:
                logger.error("Redis presence get failed (%s)", e)
        return await self.in_memory.get_presence(board_id)

    async def check_and_mark_operation(self, op_id: str, expire_secs: int = 300) -> bool:
        """Returns True if operation was ALREADY seen (duplicate), False if newly recorded."""
        if not op_id:
            return False
        if self.is_connected and self.redis_client:
            try:
                key = f"op_dedup:{op_id}"
                is_new = await self.redis_client.set(key, "1", nx=True, ex=expire_secs)
                return not is_new
            except Exception as e:
                logger.error("Redis op dedup failed (%s)", e)
        return await self.in_memory.is_operation_seen(op_id)


redis_service = RedisService()
