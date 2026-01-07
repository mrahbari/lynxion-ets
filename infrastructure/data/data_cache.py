"""
Data caching system to prevent duplicate API calls and rate limiting issues.
This cache stores recently fetched data by broker, symbol, and timeframe.
"""
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from shared.logger import EnhancedLogger


class DataCache:
    """
    A cache for market data to prevent duplicate API calls and rate limiting.
    Stores data by broker, symbol, and timeframe with TTL.
    """
    
    def __init__(self, default_ttl: int = 60):  # 60 seconds default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}  # {cache_key: {data, timestamp, ttl}}
        self.default_ttl = default_ttl
        self.logger = EnhancedLogger("DataCache")
        
    def _generate_cache_key(self, broker: str, symbol: str, timeframe: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> str:
        """Generate a unique cache key for the given parameters."""
        key_parts = [broker.lower(), symbol.upper(), timeframe.lower()]
        if start_time:
            key_parts.append(str(start_time))
        if end_time:
            key_parts.append(str(end_time))
        return "_".join(key_parts)
    
    def get(self, broker: str, symbol: str, timeframe: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached data if it exists and is still valid."""
        cache_key = self._generate_cache_key(broker, symbol, timeframe, start_time, end_time)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            current_time = time.time()
            
            # Check if cache is still valid (not expired)
            if current_time - cached_item['timestamp'] <= cached_item['ttl']:
                self.logger.debug(f"Cache HIT for {cache_key}")
                return cached_item['data']
            else:
                # Cache expired, remove it
                del self.cache[cache_key]
                self.logger.debug(f"Cache EXPIRED for {cache_key}")
        
        self.logger.debug(f"Cache MISS for {cache_key}")
        return None
    
    def set(self, broker: str, symbol: str, timeframe: str, data: List[Dict[str, Any]], 
            ttl: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None):
        """Store data in cache with TTL."""
        cache_key = self._generate_cache_key(broker, symbol, timeframe, start_time, end_time)
        actual_ttl = ttl if ttl is not None else self.default_ttl
        
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': actual_ttl
        }
        self.logger.debug(f"Cache SET for {cache_key}, TTL: {actual_ttl}s")
    
    def invalidate(self, broker: str, symbol: str, timeframe: str):
        """Invalidate specific cache entry."""
        cache_key = self._generate_cache_key(broker, symbol, timeframe)
        if cache_key in self.cache:
            del self.cache[cache_key]
            self.logger.debug(f"Cache INVALIDATED for {cache_key}")
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.logger.debug("Cache CLEARED")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for key, item in self.cache.items():
            if current_time - item['timestamp'] <= item['ttl']:
                valid_entries += 1
            else:
                expired_entries += 1
                
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'keys': list(self.cache.keys())
        }


# Global data cache instance
data_cache = DataCache()