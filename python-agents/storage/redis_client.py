"""
Redis Client for Message Storage and Retrieval
Provides caching and message queue functionality
"""
from typing import Optional, List, Dict, Any
import json
import redis.asyncio as redis
from datetime import timedelta
from config.settings import Settings
from utils.logger import logger


class RedisClient:
    """Async Redis client for message storage and retrieval"""
    
    def __init__(self, settings: Settings):
        """
        Initialize Redis client
        
        Args:
            settings: Application settings containing REDIS_URL
        """
        self.settings = settings
        self.client: Optional[redis.Redis] = None
        
    async def connect(self):
        """Establish connection to Redis"""
        try:
            self.client = await redis.from_url(
                self.settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
    
    async def ping(self) -> bool:
        """Check if Redis is responsive"""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    # ===== Message Storage =====
    
    async def save_message(
        self,
        conversation_id: int,
        message: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Save a message to a conversation
        
        Args:
            conversation_id: Unique conversation identifier (integer)
            message: Message data (role, content, timestamp, etc.)
            ttl: Optional time-to-live in seconds
            
        Returns:
            bool: Success status
        """
        try:
            key = f"conversation:{conversation_id}:messages"
            message_json = json.dumps(message)
            
            # Add message to list
            await self.client.rpush(key, message_json)
            
            # Set expiration if specified
            if ttl:
                await self.client.expire(key, ttl)
            
            logger.debug(f"Saved message to {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    async def get_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve messages from a conversation
        
        Args:
            conversation_id: Unique conversation identifier (integer)
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip from start
            
        Returns:
            List of message dictionaries
        """
        try:
            key = f"conversation:{conversation_id}:messages"
            
            # Determine range
            end = -1 if limit is None else offset + limit - 1
            
            # Get messages
            messages_json = await self.client.lrange(key, offset, end)
            
            # Parse JSON
            messages = [json.loads(msg) for msg in messages_json]
            
            logger.debug(f"Retrieved {len(messages)} messages from {key}")
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []
    
    async def get_message_count(self, conversation_id: str) -> int:
        """
        Get total number of messages in a conversation
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            Message count
        """
        try:
            key = f"conversation:{conversation_id}:messages"
            count = await self.client.llen(key)
            return count
        except Exception as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete all messages in a conversation
        
        Args:
            conversation_id: Unique conversation identifier
            
        Returns:
            bool: Success status
        """
        try:
            key = f"conversation:{conversation_id}:messages"
            await self.client.delete(key)
            logger.info(f"Deleted conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False
    
    # ===== General Key-Value Storage =====
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store a key-value pair
        
        Args:
            key: Key name
            value: Value to store (will be JSON serialized)
            ttl: Optional time-to-live in seconds
            
        Returns:
            bool: Success status
        """
        try:
            value_json = json.dumps(value)
            
            if ttl:
                await self.client.setex(key, ttl, value_json)
            else:
                await self.client.set(key, value_json)
            
            logger.debug(f"Set key {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value by key
        
        Args:
            key: Key name
            
        Returns:
            Stored value or None if not found
        """
        try:
            value_json = await self.client.get(key)
            
            if value_json is None:
                return None
            
            return json.loads(value_json)
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        Delete a key
        
        Args:
            key: Key name
            
        Returns:
            bool: Success status
        """
        try:
            await self.client.delete(key)
            logger.debug(f"Deleted key {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists
        
        Args:
            key: Key name
            
        Returns:
            bool: True if key exists
        """
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    # ===== List Operations =====
    
    async def list_conversations(self, pattern: str = "conversation:*:messages") -> List[str]:
        """
        List all conversation IDs matching a pattern
        
        Args:
            pattern: Redis key pattern
            
        Returns:
            List of conversation IDs
        """
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                # Extract conversation ID from key
                # Format: conversation:{conversation_id}:messages
                parts = key.split(":")
                if len(parts) >= 2:
                    keys.append(parts[1])
            
            logger.debug(f"Found {len(keys)} conversations")
            return keys
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    # ===== Cache Operations =====
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Cache a value with automatic expiration
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 1 hour)
            
        Returns:
            bool: Success status
        """
        return await self.set(f"cache:{key}", value, ttl)
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        return await self.get(f"cache:{key}")
    
    async def cache_delete(self, key: str) -> bool:
        """
        Delete a cached value
        
        Args:
            key: Cache key
            
        Returns:
            bool: Success status
        """
        return await self.delete(f"cache:{key}")


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client(settings: Settings) -> RedisClient:
    """
    Get or create Redis client instance (singleton pattern)
    
    Args:
        settings: Application settings
        
    Returns:
        RedisClient instance
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient(settings)
        await _redis_client.connect()
    
    return _redis_client


async def close_redis_client():
    """Close the global Redis client connection"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None
