import redis
import json
from typing import Any, Optional

class RedisClient:
    def __init__(self, host='localhost', port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        
    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """Set a value in Redis with optional expiration time"""
        serialized_value = json.dumps(value)
        return self.client.set(key, serialized_value, ex=expire)
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis"""
        value = self.client.get(key)
        if value is None:
            return None
        return json.loads(value)
        
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        return bool(self.client.exists(key))
        
    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        return bool(self.client.delete(key))
        
    def keys(self, pattern: str = "*") -> list:
        """Get all keys matching a pattern"""
        return self.client.keys(pattern)
        
    def flush_all(self):
        """Flush all keys in the database"""
        return self.client.flushall()