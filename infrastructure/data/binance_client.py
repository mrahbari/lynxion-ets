"""
Binance Client for downloading candlestick data with rate limit handling.
Following Hedge Fund standards for production-level data acquisition.
"""
import time
import requests
from datetime import datetime
from shared.logger import logger


class BinanceClient:
    BASE_URL = "https://api.binance.com/api/v3/klines"

    def __init__(self, retry=3, sleep=1):
        self.retry = retry
        self.sleep = sleep

    def get_klines(self, symbol: str, interval: str, start_ms: int, end_ms: int, limit=1000):
        """
        Download candlesticks from Binance with exponential backoff & rate control.
        """
        import random
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": min(limit, 1000)  # Binance max limit is 1000
        }

        # Exponential backoff parameters
        max_retries = 5
        base_delay = 1  # Start with 1 second

        for attempt in range(max_retries):
            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=15)  # Increased timeout
                if resp.status_code == 200:
                    logger.info(f"Successfully downloaded {len(resp.json())} klines for {symbol} {interval}")
                    return resp.json()
                elif resp.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff and jitter
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Rate limited for {symbol} {interval}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error(f"Rate limited for {symbol} {interval} after {max_retries} attempts")
                        break
                elif resp.status_code in [502, 503, 504]:  # Server errors
                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff and jitter
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Server error {resp.status_code} for {symbol} {interval}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error(f"Server error {resp.status_code} for {symbol} {interval} after {max_retries} attempts")
                        break
                else:
                    if resp.status_code == 400 and ("-1121" in resp.text or "Invalid symbol" in resp.text):
                        logger.debug(f"Symbol {symbol} is not listed on Binance Spot/Futures: {resp.text}")
                        return []
                    logger.error(f"Error downloading klines for {symbol} {interval}: {resp.status_code} - {resp.text}")
                    # Don't retry on other error codes
                    break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Request timeout for {symbol} {interval}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"Request timeout for {symbol} {interval} after {max_retries} attempts")
                    break
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Connection error for {symbol} {interval}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"Connection error for {symbol} {interval} after {max_retries} attempts")
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.error(f"Exception downloading klines for {symbol} {interval}: {str(e)}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"Exception downloading klines for {symbol} {interval} after {max_retries} attempts: {str(e)}")
                    break

        logger.warning(f"No klines obtained from Binance for {symbol} {interval}; triggering fallback data sources.")
        return []