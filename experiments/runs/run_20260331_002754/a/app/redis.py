"""app/redis.py — Redis client for caching, sessions, and queues.

exports: RedisClient, get_redis()
used_by: app/main.py → create_app(), services needing Redis, middleware for rate limiting
rules:   must use connection pooling; handle reconnection automatically; support Redis Cluster
agent:   Product Architect | 2024-03-30 | implemented Redis client with connection management
         message: "consider adding Redis Sentinel support for high availability in production"
"""

import asyncio
import logging
import json
from typing import Any, Optional, Union, Dict, List
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool, RedisCluster
from redis.exceptions import RedisError, ConnectionError

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[Union[Redis, RedisCluster]] = None


class RedisClient:
    """Redis client wrapper with connection management.
    
    Rules:
        Must support both standalone Redis and Redis Cluster
        Must handle connection errors gracefully
        Must use connection pooling for performance
        All public methods should include error handling
    """
    
    def __init__(self, redis_url: str, **kwargs):
        """Initialize Redis client.
        
        Args:
            redis_url: Redis connection URL (redis://, rediss://, redis+sentinel://)
            **kwargs: Additional Redis connection parameters
        """
        self.redis_url = redis_url
        self._client: Optional[Union[Redis, RedisCluster]] = None
        self._connection_params = kwargs
        self._is_cluster = "cluster" in redis_url.lower() or kwargs.get("cluster", False)
        
    async def connect(self) -> None:
        """Establish Redis connection.
        
        Rules:
            Differentiates between standalone Redis and Redis Cluster
            Uses connection pooling for standalone Redis
            Handles authentication and SSL automatically from URL
        """
        if self._client is not None:
            return
        
        try:
            if self._is_cluster:
                # Parse Redis Cluster nodes from URL
                # For simplicity, using single URL - in production use startup nodes
                self._client = RedisCluster.from_url(
                    self.redis_url,
                    **self._connection_params,
                    decode_responses=True,
                )
                logger.info(f"Connected to Redis Cluster at {self.redis_url}")
            else:
                # Create connection pool for standalone Redis
                pool = ConnectionPool.from_url(
                    self.redis_url,
                    **self._connection_params,
                    decode_responses=True,
                    max_connections=20,
                )
                self._client = Redis.from_pool(pool)
                logger.info(f"Connected to Redis at {self.redis_url}")
                
        except (RedisError, ConnectionError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis disconnected")
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._client is not None
    
    @property
    def client(self) -> Union[Redis, RedisCluster]:
        """Get raw Redis client instance.
        
        Returns:
            Raw Redis or RedisCluster client
            
        Rules:
            Must call connect() first
            Used for advanced Redis operations not covered by wrapper
        """
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client
    
    # --- Basic Operations ---
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string or None if key doesn't exist
        """
        try:
            return await self._client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration.
        
        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._client.set(key, value, ex=ex)
        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.
        
        Args:
            *keys: Redis keys to delete
            
        Returns:
            Number of keys deleted
        """
        try:
            return await self._client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            return 0
    
    async def exists(self, *keys: str) -> int:
        """Check if one or more keys exist.
        
        Args:
            *keys: Redis keys to check
            
        Returns:
            Number of keys that exist
        """
        try:
            return await self._client.exists(*keys)
        except RedisError as e:
            logger.error(f"Redis EXISTS error for keys {keys}: {e}")
            return 0
    
    # --- JSON Operations ---
    
    async def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Store JSON-serializable value.
        
        Args:
            key: Redis key
            value: JSON-serializable value
            ex: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, ex=ex)
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"JSON serialization error for key {key}: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Retrieve and parse JSON value.
        
        Args:
            key: Redis key
            
        Returns:
            Parsed JSON value or None
        """
        value = await self.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON deserialization error for key {key}: {e}")
            return None
    
    # --- Hash Operations ---
    
    async def hset(self, key: str, field: str, value: str) -> bool:
        """Set field in hash.
        
        Args:
            key: Redis key
            field: Hash field
            value: Value to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._client.hset(key, field, value)
        except RedisError as e:
            logger.error(f"Redis HSET error for key {key}, field {field}: {e}")
            return False
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get field from hash.
        
        Args:
            key: Redis key
            field: Hash field
            
        Returns:
            Field value or None
        """
        try:
            return await self._client.hget(key, field)
        except RedisError as e:
            logger.error(f"Redis HGET error for key {key}, field {field}: {e}")
            return None
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields and values from hash.
        
        Args:
            key: Redis key
            
        Returns:
            Dictionary of field-value pairs
        """
        try:
            return await self._client.hgetall(key)
        except RedisError as e:
            logger.error(f"Redis HGETALL error for key {key}: {e}")
            return {}
    
    # --- List Operations ---
    
    async def lpush(self, key: str, *values: str) -> Optional[int]:
        """Push values to the beginning of a list.
        
        Args:
            key: Redis key
            *values: Values to push
            
        Returns:
            Length of list after push or None on error
        """
        try:
            return await self._client.lpush(key, *values)
        except RedisError as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return None
    
    async def rpush(self, key: str, *values: str) -> Optional[int]:
        """Push values to the end of a list.
        
        Args:
            key: Redis key
            *values: Values to push
            
        Returns:
            Length of list after push or None on error
        """
        try:
            return await self._client.rpush(key, *values)
        except RedisError as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
            return None
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """Get range of elements from list.
        
        Args:
            key: Redis key
            start: Start index
            end: End index (-1 for all)
            
        Returns:
            List of values
        """
        try:
            return await self._client.lrange(key, start, end)
        except RedisError as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []
    
    # --- Set Operations ---
    
    async def sadd(self, key: str, *values: str) -> Optional[int]:
        """Add values to a set.
        
        Args:
            key: Redis key
            *values: Values to add
            
        Returns:
            Number of values added or None on error
        """
        try:
            return await self._client.sadd(key, *values)
        except RedisError as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return None
    
    async def smembers(self, key: str) -> List[str]:
        """Get all members of a set.
        
        Args:
            key: Redis key
            
        Returns:
            List of set members
        """
        try:
            return await self._client.smembers(key)
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return []
    
    # --- Pub/Sub ---
    
    @asynccontextmanager
    async def pubsub(self):
        """Context manager for Redis Pub/Sub.
        
        Yields:
            PubSub: Redis Pub/Sub object
            
        Rules:
            Must be used as async context manager
            Automatically closes connection on exit
        """
        if self._client is None:
            raise RuntimeError("Redis not connected")
        
        pubsub = self._client.pubsub()
        try:
            yield pubsub
        finally:
            await pubsub.close()
    
    # --- Rate Limiting ---
    
    async def rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Simple rate limiting using sliding window.
        
        Args:
            key: Rate limit key (e.g., "user:123:api_calls")
            limit: Maximum number of requests in window
            window: Time window in seconds
            
        Returns:
            True if allowed, False if rate limited
        """
        try:
            current = await self._client.get(key)
            if current is None:
                # First request in window
                await self._client.setex(key, window, 1)
                return True
            
            count = int(current)
            if count >= limit:
                return False
            
            # Increment counter
            await self._client.incr(key)
            # Reset TTL if this is the first increment after key creation
            if count == 0:
                await self._client.expire(key, window)
            return True
        except RedisError as e:
            logger.error(f"Rate limit error for key {key}: {e}")
            # Fail open - allow request if Redis is down
            return True


def get_redis() -> RedisClient:
    """Get global Redis client instance.
    
    Returns:
        RedisClient: Global Redis client
        
    Rules:
        Must be called after app initialization
    """
    global _redis_client
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call create_app() first.")
    return _redis_client


def set_redis_client(client: RedisClient) -> None:
    """Set global Redis client instance.
    
    Args:
        client: RedisClient instance
        
    Rules:
        Called by app factory during initialization
    """
    global _redis_client
    _redis_client = client