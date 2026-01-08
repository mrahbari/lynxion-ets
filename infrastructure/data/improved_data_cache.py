"""
Improved Data caching system to prevent duplicate API calls and rate limiting issues.
This cache stores recently fetched data by broker, symbol, and timeframe.
Addresses cache coherency, memory growth, and cache penetration issues.
"""
import time
import threading
from collections import OrderedDict
from typing import Dict, Any, Optional, List
from datetime import datetime
from shared.logger import EnhancedLogger


class ImprovedDataCache:
    """
    An improved cache for market data to prevent duplicate API calls and rate limiting.
    Stores data by broker, symbol, and timeframe with TTL.
    Features: LRU eviction, size limits, and cache warming strategies.
    """

    def __init__(self, default_ttl: int = 60, max_size: int = 1000, warm_up_strategy: Optional[callable] = None):  # 60 seconds default TTL, 1000 max entries
        # Use OrderedDict for LRU eviction
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()  # {cache_key: {data, timestamp, ttl}}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.warm_up_strategy = warm_up_strategy
        self.logger = EnhancedLogger("ImprovedDataCache")
        self._lock = threading.RLock()  # Use reentrant lock for thread safety

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

        with self._lock:
            if cache_key in self.cache:
                cached_item = self.cache[cache_key]
                current_time = time.time()

                # Check if cache is still valid (not expired)
                if current_time - cached_item['timestamp'] <= cached_item['ttl']:
                    # Move to end to mark as recently used (LRU)
                    self.cache.move_to_end(cache_key)
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
        """Store data in cache with TTL, enforcing size limits."""
        cache_key = self._generate_cache_key(broker, symbol, timeframe, start_time, end_time)
        actual_ttl = ttl if ttl is not None else self.default_ttl

        with self._lock:
            # Check if we need to evict entries due to size limit
            while len(self.cache) >= self.max_size:
                # Remove the oldest (least recently used) entry
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.logger.debug(f"Cache EVICTED oldest entry: {oldest_key}")

            # Add the new entry
            self.cache[cache_key] = {
                'data': data,
                'timestamp': time.time(),
                'ttl': actual_ttl
            }
            # Move to end to mark as recently used
            self.cache.move_to_end(cache_key)
            self.logger.debug(f"Cache SET for {cache_key}, TTL: {actual_ttl}s, Size: {len(self.cache)}/{self.max_size}")

    def invalidate(self, broker: str, symbol: str, timeframe: str):
        """Invalidate specific cache entry."""
        cache_key = self._generate_cache_key(broker, symbol, timeframe)
        with self._lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                self.logger.debug(f"Cache INVALIDATED for {cache_key}")

    def invalidate_prefix(self, prefix: str):
        """Invalidate all cache entries with a given prefix (for bulk invalidation)."""
        with self._lock:
            keys_to_remove = []
            for key in self.cache.keys():
                if key.startswith(prefix):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.cache[key]
                self.logger.debug(f"Cache INVALIDATED for prefix match: {key}")

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.logger.debug("Cache CLEARED")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
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
                'max_size': self.max_size,
                'utilization_percent': (len(self.cache) / self.max_size) * 100 if self.max_size > 0 else 0,
                'keys': list(self.cache.keys())
            }

    def clean_expired(self):
        """Manually clean expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, item in self.cache.items():
                if current_time - item['timestamp'] > item['ttl']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                self.logger.debug(f"Expired entry cleaned: {key}")
            
            return len(expired_keys)

    def warm_up(self, broker: str, symbols: List[str], timeframes: List[str]):
        """Warm up cache with commonly accessed data."""
        if self.warm_up_strategy:
            for symbol in symbols:
                for timeframe in timeframes:
                    try:
                        # Use the warm-up strategy to pre-populate cache
                        data = self.warm_up_strategy(broker, symbol, timeframe)
                        if data:
                            self.set(broker, symbol, timeframe, data)
                            self.logger.info(f"Warm-up cache populated for {broker}:{symbol}:{timeframe}")
                    except Exception as e:
                        self.logger.error(f"Error during cache warm-up for {broker}:{symbol}:{timeframe}: {e}")
        else:
            self.logger.warning("No warm-up strategy defined")

    def get_memory_usage(self) -> int:
        """Estimate memory usage of the cache."""
        with self._lock:
            import sys
            total_size = sys.getsizeof(self.cache)
            for key, value in self.cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(value)
            return total_size


# Global improved data cache instance
improved_data_cache = ImprovedDataCache()