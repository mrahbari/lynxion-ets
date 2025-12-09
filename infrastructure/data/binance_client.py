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
        Download candlesticks from Binance with retry & rate control.
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": min(limit, 1000)  # Binance max limit is 1000
        }

        for i in range(self.retry):
            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=10)
                if resp.status_code == 200:
                    logger.info(f"Successfully downloaded {len(resp.json())} klines for {symbol} {interval}")
                    return resp.json()
                else:
                    logger.error(f"Error downloading klines for {symbol} {interval}: {resp.status_code} - {resp.text}")
                time.sleep(self.sleep)
            except Exception as e:
                logger.error(f"Exception downloading klines for {symbol} {interval}: {str(e)}")
                time.sleep(self.sleep)

        logger.error(f"Failed to download klines for {symbol} {interval} after {self.retry} attempts")
        return []