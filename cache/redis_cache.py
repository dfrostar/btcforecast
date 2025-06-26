"""
Redis Caching System
Provides Redis-based caching with connection pooling and async support.
"""

import os
import json
import asyncio
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
import logging
from config import get_config

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """Redis cache manager with connection pooling"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.pool: Optional[ConnectionPool] = None
        self.redis_client: Optional[Redis] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the Redis connection pool"""
        if self.pool is None:
            async with self._lock:
                if self.pool is None:
                    try:
                        self.pool = ConnectionPool.from_url(
                            self.redis_url,
                            max_connections=20,
                            retry_on_timeout=True,
                            socket_keepalive=True,
                            socket_keepalive_options={},
                            decode_responses=False  # Keep as bytes for pickle compatibility
                        )
                        self.redis_client = Redis(connection_pool=self.pool)
                        
                        # Test connection
                        await self.redis_client.ping()
                        logger.info("Redis connection pool initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize Redis pool: {e}")
                        raise
    
    async def close(self):
        """Close the Redis connection pool"""
        if self.redis_client:
            await self.redis_client.close()
        if self.pool:
            await self.pool.disconnect()
        self.redis_client = None
        self.pool = None
        logger.info("Redis connection pool closed")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                return default
            
            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return default
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            # Try to serialize as JSON first, fallback to pickle
            try:
                serialized_value = json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                serialized_value = pickle.dumps(value)
            
            if expire:
                await self.redis_client.setex(key, expire, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Error setting expiration for cache key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for cache key {key}: {e}")
            return -1
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in cache"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            return await self.redis_client.incr(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing cache key {key}: {e}")
            return 0
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            await self.initialize()
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0

# Global Redis cache manager instance
redis_cache = RedisCacheManager()

class CacheService:
    """High-level cache service with business logic"""
    
    # Cache key prefixes
    USER_PREFIX = "user:"
    PREDICTION_PREFIX = "prediction:"
    MODEL_PREFIX = "model:"
    DATA_PREFIX = "data:"
    RATE_LIMIT_PREFIX = "rate_limit:"
    SESSION_PREFIX = "session:"
    
    @staticmethod
    async def cache_user(user_id: int, user_data: Dict, expire: int = 3600) -> bool:
        """Cache user data"""
        key = f"{CacheService.USER_PREFIX}{user_id}"
        return await redis_cache.set(key, user_data, expire)
    
    @staticmethod
    async def get_cached_user(user_id: int) -> Optional[Dict]:
        """Get cached user data"""
        key = f"{CacheService.USER_PREFIX}{user_id}"
        return await redis_cache.get(key)
    
    @staticmethod
    async def invalidate_user_cache(user_id: int) -> bool:
        """Invalidate user cache"""
        key = f"{CacheService.USER_PREFIX}{user_id}"
        return await redis_cache.delete(key)
    
    @staticmethod
    async def cache_prediction(prediction_id: str, prediction_data: Dict, expire: int = 1800) -> bool:
        """Cache prediction data"""
        key = f"{CacheService.PREDICTION_PREFIX}{prediction_id}"
        return await redis_cache.set(key, prediction_data, expire)
    
    @staticmethod
    async def get_cached_prediction(prediction_id: str) -> Optional[Dict]:
        """Get cached prediction data"""
        key = f"{CacheService.PREDICTION_PREFIX}{prediction_id}"
        return await redis_cache.get(key)
    
    @staticmethod
    async def cache_model(model_name: str, model_data: Any, expire: int = 86400) -> bool:
        """Cache model data"""
        key = f"{CacheService.MODEL_PREFIX}{model_name}"
        return await redis_cache.set(key, model_data, expire)
    
    @staticmethod
    async def get_cached_model(model_name: str) -> Optional[Any]:
        """Get cached model data"""
        key = f"{CacheService.MODEL_PREFIX}{model_name}"
        return await redis_cache.get(key)
    
    @staticmethod
    async def cache_market_data(symbol: str, interval: str, data: Dict, expire: int = 300) -> bool:
        """Cache market data"""
        key = f"{CacheService.DATA_PREFIX}market:{symbol}:{interval}"
        return await redis_cache.set(key, data, expire)
    
    @staticmethod
    async def get_cached_market_data(symbol: str, interval: str) -> Optional[Dict]:
        """Get cached market data"""
        key = f"{CacheService.DATA_PREFIX}market:{symbol}:{interval}"
        return await redis_cache.get(key)
    
    @staticmethod
    async def increment_rate_limit(identifier: str, window: int = 3600) -> int:
        """Increment rate limit counter"""
        key = f"{CacheService.RATE_LIMIT_PREFIX}{identifier}"
        count = await redis_cache.increment(key)
        
        # Set expiration if this is the first increment
        if count == 1:
            await redis_cache.expire(key, window)
        
        return count
    
    @staticmethod
    async def get_rate_limit_count(identifier: str) -> int:
        """Get current rate limit count"""
        key = f"{CacheService.RATE_LIMIT_PREFIX}{identifier}"
        count = await redis_cache.get(key)
        return count if count is not None else 0
    
    @staticmethod
    async def cache_session(session_id: str, session_data: Dict, expire: int = 3600) -> bool:
        """Cache session data"""
        key = f"{CacheService.SESSION_PREFIX}{session_id}"
        return await redis_cache.set(key, session_data, expire)
    
    @staticmethod
    async def get_cached_session(session_id: str) -> Optional[Dict]:
        """Get cached session data"""
        key = f"{CacheService.SESSION_PREFIX}{session_id}"
        return await redis_cache.get(key)
    
    @staticmethod
    async def invalidate_session(session_id: str) -> bool:
        """Invalidate session cache"""
        key = f"{CacheService.SESSION_PREFIX}{session_id}"
        return await redis_cache.delete(key)
    
    @staticmethod
    async def clear_user_cache(user_id: int) -> bool:
        """Clear all cache related to a user"""
        patterns = [
            f"{CacheService.USER_PREFIX}{user_id}",
            f"{CacheService.PREDICTION_PREFIX}*user_{user_id}*",
            f"{CacheService.SESSION_PREFIX}*user_{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await redis_cache.clear_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted > 0
    
    @staticmethod
    async def get_cache_stats() -> Dict:
        """Get cache statistics"""
        if not redis_cache.redis_client:
            await redis_cache.initialize()
        
        try:
            info = await redis_cache.redis_client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

# Initialize Redis cache
async def init_cache():
    """Initialize the Redis cache"""
    await redis_cache.initialize()

# Cleanup Redis cache
async def cleanup_cache():
    """Cleanup the Redis cache"""
    await redis_cache.close()

# Get cache manager
def get_cache_manager() -> RedisCacheManager:
    """Get the Redis cache manager instance"""
    return redis_cache

# Get cache service
def get_cache_service() -> CacheService:
    """Get the cache service instance"""
    return CacheService() 