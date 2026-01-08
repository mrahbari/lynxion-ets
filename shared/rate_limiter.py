"""
Rate limiter for API requests to prevent exceeding rate limits.
"""
import time
import threading
from typing import Dict, Optional
from shared.logger import EnhancedLogger


class RateLimiter:
    """
    A thread-safe rate limiter that implements token bucket algorithm.
    """
    
    def __init__(self, max_requests: int, time_window: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window: Time window in seconds (default 60 seconds)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_refill = time.time()
        self.lock = threading.Lock()
        self.logger = EnhancedLogger("RateLimiter")
        
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        time_passed = now - self.last_refill
        
        # Calculate how many tokens to add based on time passed
        tokens_to_add = (time_passed / self.time_window) * self.max_requests
        
        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def acquire(self, num_tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens. Returns True if successful, False if rate limited.
        
        Args:
            num_tokens: Number of tokens to acquire (default 1)
            
        Returns:
            True if tokens were acquired, False if rate limited
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= num_tokens:
                self.tokens -= num_tokens
                return True
            else:
                return False
    
    def wait_for_tokens(self, num_tokens: int = 1):
        """
        Wait until tokens are available.
        
        Args:
            num_tokens: Number of tokens to wait for (default 1)
        """
        while not self.acquire(num_tokens):
            time.sleep(0.1)  # Wait 100ms before checking again


class GlobalRateLimiter:
    """
    Global rate limiter that can be used across the application.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        # Default rate limits for different exchanges
        self.limiters: Dict[str, RateLimiter] = {
            'bingx': RateLimiter(max_requests=5, time_window=60),  # Very conservative for BingX
            'binance': RateLimiter(max_requests=10, time_window=60),
            'mexc': RateLimiter(max_requests=10, time_window=60),
            'phemex': RateLimiter(max_requests=10, time_window=60),
        }
        self.logger = EnhancedLogger("GlobalRateLimiter")
    
    def get_limiter(self, exchange: str) -> RateLimiter:
        """Get rate limiter for specific exchange."""
        exchange_lower = exchange.lower()
        if exchange_lower not in self.limiters:
            # Use a conservative default for unknown exchanges
            self.limiters[exchange_lower] = RateLimiter(max_requests=5, time_window=60)
        return self.limiters[exchange_lower]
    
    def acquire(self, exchange: str, num_tokens: int = 1) -> bool:
        """Acquire tokens for specific exchange."""
        limiter = self.get_limiter(exchange)
        return limiter.acquire(num_tokens)
    
    def wait_for_tokens(self, exchange: str, num_tokens: int = 1):
        """Wait for tokens for specific exchange."""
        limiter = self.get_limiter(exchange)
        limiter.wait_for_tokens(num_tokens)


# Global instance
global_rate_limiter = GlobalRateLimiter()