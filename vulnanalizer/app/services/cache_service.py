"""
Cache service for Redis operations
"""
import json
import pickle
import asyncio
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from ..database import get_db


class CacheService:
    """Service for caching data in Redis"""
    
    def __init__(self):
        self.redis_client = None
        self.db = None
        self._lock = asyncio.Lock()
    
    async def get_redis_client(self):
        """Get Redis client with connection pooling"""
        if self.redis_client is None:
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                db=0,
                decode_responses=False,  # Keep as bytes for pickle
                max_connections=20
            )
        return self.redis_client
    
    async def get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = get_db()
        return self.db
    
    def _get_cache_key(self, prefix: str, key: str) -> str:
        """Generate cache key"""
        return f"vulnanalizer:{prefix}:{key}"
    
    async def get_cached_data(self, prefix: str, key: str) -> Optional[Any]:
        """Get data from cache"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = self._get_cache_key(prefix, key)
            data = await redis_client.get(cache_key)
            
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            print(f"Cache get error for {prefix}:{key}: {e}")
            return None
    
    async def set_cached_data(self, prefix: str, key: str, data: Any, ttl: int = 3600) -> bool:
        """Set data in cache with TTL"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = self._get_cache_key(prefix, key)
            serialized_data = pickle.dumps(data)
            
            await redis_client.setex(cache_key, ttl, serialized_data)
            return True
        except Exception as e:
            print(f"Cache set error for {prefix}:{key}: {e}")
            return False
    
    async def delete_cached_data(self, prefix: str, key: str) -> bool:
        """Delete data from cache"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = self._get_cache_key(prefix, key)
            await redis_client.delete(cache_key)
            return True
        except Exception as e:
            print(f"Cache delete error for {prefix}:{key}: {e}")
            return False
    
    async def clear_cache_prefix(self, prefix: str) -> bool:
        """Clear all cache entries with specific prefix"""
        try:
            redis_client = await self.get_redis_client()
            pattern = self._get_cache_key(prefix, "*")
            keys = await redis_client.keys(pattern)
            
            if keys:
                await redis_client.delete(*keys)
                print(f"Cleared {len(keys)} cache entries for prefix: {prefix}")
            return True
        except Exception as e:
            print(f"Cache clear error for prefix {prefix}: {e}")
            return False
    
    async def get_epss_data(self, cve: str) -> Optional[Dict[str, Any]]:
        """Get EPSS data with caching"""
        # Try cache first
        cached_data = await self.get_cached_data("epss", cve)
        if cached_data:
            return cached_data
        
        # If not in cache, get from database
        async with self._lock:
            # Double-check cache after acquiring lock
            cached_data = await self.get_cached_data("epss", cve)
            if cached_data:
                return cached_data
            
            try:
                db = await self.get_db()
                epss_data = await db.get_epss_by_cve(cve)
                
                if epss_data:
                    # Cache for 1 hour
                    await self.set_cached_data("epss", cve, epss_data, 3600)
                
                return epss_data
            except Exception as e:
                print(f"Error getting EPSS data for {cve}: {e}")
                return None
    
    async def get_cve_data(self, cve: str) -> Optional[Dict[str, Any]]:
        """Get CVE data with caching"""
        # Try cache first
        cached_data = await self.get_cached_data("cve", cve)
        if cached_data:
            return cached_data
        
        # If not in cache, get from database
        async with self._lock:
            # Double-check cache after acquiring lock
            cached_data = await self.get_cached_data("cve", cve)
            if cached_data:
                return cached_data
            
            try:
                db = await self.get_db()
                cve_data = await db.get_cve_by_id(cve)
                
                if cve_data:
                    # Cache for 1 hour
                    await self.set_cached_data("cve", cve, cve_data, 3600)
                
                return cve_data
            except Exception as e:
                print(f"Error getting CVE data for {cve}: {e}")
                return None
    
    async def get_exploitdb_data(self, cve: str) -> List[Dict[str, Any]]:
        """Get ExploitDB data with caching"""
        # Try cache first
        cached_data = await self.get_cached_data("exploitdb", cve)
        if cached_data:
            return cached_data
        
        # If not in cache, get from database
        async with self._lock:
            # Double-check cache after acquiring lock
            cached_data = await self.get_cached_data("exploitdb", cve)
            if cached_data:
                return cached_data
            
            try:
                db = await self.get_db()
                exploitdb_data = await db.get_exploitdb_by_cve(cve)
                
                # Cache for 1 hour (even empty results)
                await self.set_cached_data("exploitdb", cve, exploitdb_data, 3600)
                
                return exploitdb_data
            except Exception as e:
                print(f"Error getting ExploitDB data for {cve}: {e}")
                return []
    
    async def invalidate_epss_cache(self):
        """Invalidate EPSS cache"""
        await self.clear_cache_prefix("epss")
    
    async def invalidate_cve_cache(self):
        """Invalidate CVE cache"""
        await self.clear_cache_prefix("cve")
    
    async def invalidate_exploitdb_cache(self):
        """Invalidate ExploitDB cache"""
        await self.clear_cache_prefix("exploitdb")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            redis_client = await self.get_redis_client()
            info = await redis_client.info()
            
            stats = {
                'total_keys': info.get('db0', {}).get('keys', 0),
                'memory_usage': info.get('used_memory_human', 'N/A'),
                'hit_rate': info.get('keyspace_hits', 0),
                'miss_rate': info.get('keyspace_misses', 0)
            }
            
            # Count keys by prefix
            prefixes = ['epss', 'cve', 'exploitdb']
            for prefix in prefixes:
                pattern = self._get_cache_key(prefix, "*")
                keys = await redis_client.keys(pattern)
                stats[f'{prefix}_cached'] = len(keys)
            
            return stats
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return {}


# Global cache service instance
cache_service = CacheService()

