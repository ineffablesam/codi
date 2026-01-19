"""Redis-based message broker for cross-process WebSocket messaging.

This module bridges Celery workers and the FastAPI WebSocket server.
Celery workers publish messages to Redis, and FastAPI subscribes and broadcasts
to actual WebSocket connections.
"""
import asyncio
import json
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Redis pub/sub channel for WebSocket messages
WEBSOCKET_CHANNEL = "codi:websocket:messages"


class RedisBroadcaster:
    """Redis-based broadcaster for cross-process WebSocket messaging.
    
    This is a singleton that:
    - In Celery workers: Publishes messages to Redis
    - In FastAPI: Subscribes to Redis and broadcasts to actual WebSocket connections
    """
    
    _instance: Optional["RedisBroadcaster"] = None
    
    def __new__(cls) -> "RedisBroadcaster":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._subscriber_task: Optional[asyncio.Task] = None
        self._initialized = True
        logger.info("RedisBroadcaster initialized")
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis for broadcasting")
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    async def publish(self, project_id: int, message: Dict[str, Any]) -> None:
        """Publish a message to Redis for broadcasting.
        
        This is called by Celery workers to send messages.
        
        Args:
            project_id: Project ID to broadcast to
            message: Message to broadcast
        """
        await self.connect()
        
        payload = json.dumps({
            "project_id": project_id,
            "message": message,
        })
        
        try:
            await self._redis.publish(WEBSOCKET_CHANNEL, payload)
            logger.debug(f"Published message to Redis: project={project_id}, type={message.get('type')}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

    async def send_agent_signal(self, project_id: int, signal_type: str, data: Dict[str, Any]) -> None:
        """Send a signal to a running agent.
        
        Args:
            project_id: Project ID
            signal_type: Type of signal (e.g., 'plan_approval')
            data: Signal data
        """
        await self.connect()
        
        channel = f"codi:project:{project_id}:signals"
        payload = json.dumps({
            "type": signal_type,
            "data": data,
        })
        
        try:
            await self._redis.publish(channel, payload)
            logger.info(f"Sent agent signal to Redis: channel={channel}, type={signal_type}")
        except Exception as e:
            logger.error(f"Failed to publish signal to Redis: {e}")
    
    async def start_subscriber(self, on_message_callback) -> None:
        """Start subscribing to Redis for messages.
        
        This is called by FastAPI to receive messages and broadcast them.
        
        Args:
            on_message_callback: Async function to call when a message is received.
                                 Signature: async def callback(project_id: int, message: dict)
        """
        await self.connect()
        
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(WEBSOCKET_CHANNEL)
        
        logger.info(f"Subscribed to Redis channel: {WEBSOCKET_CHANNEL}")
        
        async def _listener():
            try:
                async for message in self._pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            project_id = data["project_id"]
                            ws_message = data["message"]
                            
                            logger.debug(f"Received message from Redis: project={project_id}")
                            await on_message_callback(project_id, ws_message)
                        except Exception as e:
                            logger.error(f"Error processing Redis message: {e}")
            except asyncio.CancelledError:
                logger.info("Redis subscriber task cancelled")
                raise
        
        self._subscriber_task = asyncio.create_task(_listener())


# Global broadcaster instance
redis_broadcaster = RedisBroadcaster()


# Convenience function for publishing from anywhere (including Celery workers)
async def publish_to_websocket(project_id: int, message: Dict[str, Any]) -> None:
    """Publish a message to be broadcast via WebSocket.
    
    This is the main function to call from Celery workers or anywhere
    that needs to send WebSocket messages.
    
    Args:
        project_id: Project ID to broadcast to
        message: Message to broadcast (will have timestamp added if missing)
    """
    from datetime import datetime
    
    # Add timestamp if not present
    if "timestamp" not in message:
        message["timestamp"] = datetime.utcnow().isoformat()
    
    await redis_broadcaster.publish(project_id, message)
