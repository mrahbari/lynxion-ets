"""
Infrastructure adapter for downloading data from exchanges.
"""
import asyncio
import aiohttp
import time
import random
from typing import List, Dict, Any, Optional
from collections import deque
import ccxt.async_support as ccxt_async
from application.configs.sync_settings import settings
from application.configs.symbol_config import get_symbol_config
from domain.ports.sync import DataDownloader
from utils.logger import logger, OperationType, StatusType


class RateLimitState:
    """Track rate limit state for token bucket algorithm"""
    def __init__(self, tokens_per_second: float):
        self.tokens = tokens_per_second
        self.last_refill = time.time()


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API requests"""
    
    def __init__(self, tokens_per_second: float):
        self.tokens_per_second = tokens_per_second
        self.state = RateLimitState(tokens_per_second)
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens from the bucket, waiting if necessary"""
        async with self._lock:
            now = time.time()
            # Refill tokens based on time elapsed
            time_passed = now - self.state.last_refill
            new_tokens = time_passed * self.tokens_per_second
            self.state.tokens = min(self.tokens_per_second, self.state.tokens + new_tokens)
            self.state.last_refill = now
            
            # If not enough tokens, wait for refill
            if self.state.tokens < tokens:
                sleep_time = (tokens - self.state.tokens) / self.tokens_per_second
                await asyncio.sleep(sleep_time)
                self.state.tokens = max(0, self.state.tokens - tokens)
            else:
                self.state.tokens -= tokens


class DataDownloaderAdapter(DataDownloader):
    """Infrastructure adapter for downloading data from exchanges"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = TokenBucketRateLimiter(settings.rate_limit_tokens_per_second)
        self.exchange_instances = {}

    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()
        # Close exchange instances
        for exchange in self.exchange_instances.values():
            if hasattr(exchange, 'close'):
                await exchange.close()
    
    async def get_exchange_instance(self, exchange_name: str):
        """Get or create an exchange instance"""
        if exchange_name not in self.exchange_instances:
            exchange_class = getattr(ccxt_async, exchange_name.lower())
            # Configure for spot trading, not futures
            exchange_config = {
                'enableRateLimit': False,  # We handle rate limiting ourselves
                'timeout': settings.api_timeout if hasattr(settings, 'api_timeout') else 30000,
            }

            # Add specific configuration for Binance to use spot API
            if exchange_name.lower() == 'binance':
                exchange_config['options'] = {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True,  # Helps with API time sync issues
                    'recvWindow': 60000,  # 60 seconds, increase if needed
                }
                # Properly configure all binance API URLs to use the spot API
                exchange_config['urls'] = {
                    'api': {
                        'rest': 'https://api.binance.com',
                        'public': 'https://api.binance.com/api/v3',
                        'private': 'https://api.binance.com/api/v3',
                    },
                    'test': {
                        'rest': 'https://testnet.binance.vision',
                        'public': 'https://testnet.binance.vision/api/v3',
                        'private': 'https://testnet.binance.vision/api/v3',
                    }
                }

            self.exchange_instances[exchange_name] = exchange_class(exchange_config)
        return self.exchange_instances[exchange_name]
    
    async def _fetch_with_retry(self, symbol: str, start_ts: int, end_ts: int) -> List[dict]:
        """Fetch data with retry logic"""
        symbol_config = get_symbol_config(symbol)
        if not symbol_config:
            # Try to get config with different format (e.g. BTC-USDT vs BTCUSDT)
            symbol_alt = symbol.replace('-', '')
            symbol_config = get_symbol_config(symbol_alt)
            if not symbol_config:
                raise ValueError(f"No configuration found for symbol: {symbol}")

        exchange_name = symbol_config.exchange if symbol_config else "bingx"
        exchange = await self.get_exchange_instance(exchange_name)

        attempt = 0
        last_error = None

        # Format symbol for exchange
        # Convert BTC-USDT to BTCUSDT for Binance (no separator)
        if exchange_name.lower() == 'binance':
            exchange_symbol = symbol.replace('-', '')
        else:
            # For other exchanges, use slash format
            exchange_symbol = symbol.replace('-', '/')

        while attempt < settings.retry_max_attempts:
            try:
                # Apply rate limiting
                await self.rate_limiter.acquire(1)

                start_time = time.time()

                # Fetch the data - CCXT uses milliseconds for timestamps
                ohlcv_data = await exchange.fetch_ohlcv(
                    exchange_symbol,
                    timeframe='1m',
                    since=start_ts * 1000,  # Convert to milliseconds
                    limit=1000  # Most exchanges support up to 1000 candles
                )

                duration_ms = int((time.time() - start_time) * 1000)

                # Log successful request
                logger.log_operation(
                    operation=OperationType.SYMBOL_DOWNLOAD,
                    symbol=symbol,
                    status=StatusType.OK,
                    duration_ms=duration_ms,
                    api_usage={"requests": 1, "rate_limit_events": 0}
                )

                # Convert CCXT format to our required format
                # CCXT returns [timestamp, open, high, low, close, volume]
                formatted_data = []
                for entry in ohlcv_data:
                    ts, o, h, l, c, v = entry
                    # Convert timestamp from milliseconds to seconds and filter by range
                    ts_sec = ts // 1000
                    if start_ts <= ts_sec <= end_ts:
                        formatted_data.append({
                            'timestamp': ts_sec,
                            'open': o,
                            'high': h,
                            'low': l,
                            'close': c,
                            'volume': v
                        })

                return formatted_data

            except Exception as e:
                last_error = e
                attempt += 1

                if attempt >= settings.retry_max_attempts:
                    break

                # Calculate backoff time with jitter
                backoff_time = settings.retry_backoff_base * (settings.retry_backoff_factor ** (attempt - 1))
                jitter = random.uniform(0, 0.1 * backoff_time)
                total_wait = backoff_time + jitter

                # Log retry attempt
                logger.log_operation(
                    operation=OperationType.SYMBOL_DOWNLOAD,
                    symbol=symbol,
                    status=StatusType.ERROR,
                    error=str(e),
                    duration_ms=int(total_wait * 1000)
                )

                await asyncio.sleep(total_wait)

        # If all retries failed, raise the last error
        if last_error:
            raise last_error
        else:
            return []  # Return empty list if no data could be fetched
    
    async def _fetch_range_batch(self, symbol: str, start_ts: int, end_ts: int) -> List[dict]:
        """Fetch a range of data, potentially in batches if the range is too large"""
        symbol_config = get_symbol_config(symbol)
        max_window_minutes = symbol_config.max_api_window_minutes if symbol_config else 1440  # Default 24 hours
        max_window_seconds = max_window_minutes * 60

        all_data = []
        current_start = start_ts

        while current_start < end_ts:
            # Calculate end for this batch
            batch_end = min(current_start + max_window_seconds, end_ts)

            # Fetch this batch
            batch_data = await self._fetch_with_retry(symbol, current_start, batch_end)
            all_data.extend(batch_data)

            # Move to the next batch
            # Add 60 seconds to avoid overlap due to potential rounding
            current_start = batch_end + 60

        return all_data
    
    async def fetch_range(self, symbol: str, start_ts: int, end_ts: int) -> List[dict]:
        """
        Fetch OHLCV data for a symbol in a given time range.
        
        Args:
            symbol: Trading symbol (e.g. "BTC-USDT") 
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)
            
        Returns:
            List of OHLCV data points
        """
        try:
            data = await self._fetch_range_batch(symbol, start_ts, end_ts)
            
            # Sort data by timestamp to ensure proper ordering
            sorted_data = sorted(data, key=lambda x: x['timestamp'])
            
            return sorted_data
        except Exception as e:
            logger.log_operation(
                operation=OperationType.SYMBOL_DOWNLOAD,
                symbol=symbol,
                status=StatusType.ERROR,
                error={
                    "message": str(e),
                    "type": type(e).__name__
                },
                fixed_ranges=[[start_ts, end_ts]]
            )
            raise