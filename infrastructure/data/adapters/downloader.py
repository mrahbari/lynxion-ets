import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from shared.logger import logger
import time


class DataDownloader:
    def __init__(self, base_url: str = "https://api.binance.com"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def fetch_historical_klines(
        self, 
        symbol: str, 
        interval: str, 
        start_time: str, 
        end_time: Optional[str] = None,
        limit: int = 1000
    ) -> List[List]:
        """Fetch historical klines from exchange"""
        endpoint = f"{self.base_url}/api/v3/klines"
        
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": start_time,
            "limit": min(limit, 1000)  # Binance max limit is 1000
        }
        
        if end_time:
            params["endTime"] = end_time
            
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched {len(data)} klines for {symbol}")
            return data
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
            
    def fetch_current_price(self, symbol: str) -> Optional[float]:
        """Fetch current price for a symbol"""
        endpoint = f"{self.base_url}/api/v3/ticker/price"
        
        params = {"symbol": symbol.upper()}
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            return float(data["price"])
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
            
    def fetch_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict]:
        """Fetch orderbook data"""
        endpoint = f"{self.base_url}/api/v3/depth"
        
        params = {
            "symbol": symbol.upper(),
            "limit": min(limit, 5000)  # Max limit for Binance
        }
        
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return None
            
    def klines_to_dataframe(self, klines: List[List]) -> pd.DataFrame:
        """Convert klines to pandas DataFrame"""
        columns = [
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ]
        
        df = pd.DataFrame(klines, columns=columns)
        
        # Convert timestamp to datetime
        df["open_time"] = pd.to_datetime(df["open_time"], unit='ms')
        df["close_time"] = pd.to_datetime(df["close_time"], unit='ms')
        
        # Convert numeric columns
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
            
        return df