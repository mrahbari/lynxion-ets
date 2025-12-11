"""
Unit tests for downloader_async.py
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from downloader_async import AsyncDownloader, TokenBucketRateLimiter


class TestTokenBucketRateLimiter(unittest.TestCase):
    def setUp(self):
        self.rate_limiter = TokenBucketRateLimiter(1.0)  # 1 token per second
    
    def test_initial_tokens(self):
        """Test that rate limiter starts with correct number of tokens"""
        self.assertEqual(self.rate_limiter.tokens_per_second, 1.0)
    
    @unittest.skip("Requires async test")  # Will be tested properly below
    def test_acquire_immediate(self):
        """Test that we can acquire tokens immediately if available"""
        pass


class TestAsyncDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = AsyncDownloader()
    
    @patch('ccxt.async_support.bingx')
    @patch('aiohttp.ClientSession')
    def test_fetch_with_retry_success(self, mock_session, mock_exchange_class):
        """Test successful fetch with retry logic"""
        # Setup mock exchange
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1609459200000, 100.0, 105.0, 99.0, 104.0, 1000],  # timestamp in milliseconds
            [1609459260000, 104.0, 108.0, 103.0, 107.0, 1200],
        ])
        mock_exchange_class.return_value = mock_exchange
        
        # Test the fetch_range method
        async def run_test():
            # Since we have replaced the exchange instances, we need to clear the cache
            self.downloader.exchange_instances.clear()
            
            result = await self.downloader.fetch_range("BTC-USDT", 1609459200, 1609459300)
            
            # Check that the result is formatted correctly
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['timestamp'], 1609459200)
            self.assertEqual(result[1]['timestamp'], 1609459260)
        
        # Run the async test
        asyncio.run(run_test())
    
    @patch('ccxt.async_support.bingx')
    def test_fetch_range_batch(self, mock_exchange_class):
        """Test fetching a range in batches"""
        # Setup mock exchange
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1609459200000, 100.0, 105.0, 99.0, 104.0, 1000],
        ])
        mock_exchange_class.return_value = mock_exchange
        
        async def run_test():
            self.downloader.exchange_instances.clear()
            
            result = await self.downloader._fetch_range_batch("BTC-USDT", 1609459200, 1609459260)
            
            self.assertIsInstance(result, list)
        
        asyncio.run(run_test())


# Additional async tests that need to be run properly
class TestAsyncDownloaderAsync(unittest.IsolatedAsyncioTestCase):
    @patch('ccxt.async_support.bingx')
    async def test_fetch_range_integration(self, mock_exchange_class):
        """Integration test for fetch_range method"""
        from downloader_async import AsyncDownloader
        
        # Setup mock exchange
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1609459200000, 100.0, 105.0, 99.0, 104.0, 1000],
            [1609459260000, 104.0, 108.0, 103.0, 107.0, 1200],
        ])
        mock_exchange.close = AsyncMock()
        mock_exchange_class.return_value = mock_exchange
        
        downloader = AsyncDownloader()
        async with downloader:
            result = await downloader.fetch_range("BTC-USDT", 1609459200, 1609459300)
        
        # Check that the result is formatted correctly
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['timestamp'], 1609459200)
        self.assertEqual(result[1]['timestamp'], 1609459260)
        self.assertEqual(result[0]['open'], 100.0)
        self.assertEqual(result[1]['close'], 107.0)


class TestTokenBucketRateLimiterAsync(unittest.IsolatedAsyncioTestCase):
    async def test_rate_limiter_acquire(self):
        """Test that the rate limiter properly delays when tokens are exhausted"""
        import time
        from downloader_async import TokenBucketRateLimiter
        
        rate_limiter = TokenBucketRateLimiter(0.5)  # 0.5 tokens per second = 2 seconds per token
        
        start_time = time.time()
        await rate_limiter.acquire(1)
        first_call_time = time.time()
        
        # The second call should be delayed until tokens are replenished
        await rate_limiter.acquire(1)
        end_time = time.time()
        
        # Should take at least ~2 seconds due to rate limiting
        self.assertGreater(end_time - start_time, 1.5)  # Allow some tolerance


if __name__ == '__main__':
    unittest.main()