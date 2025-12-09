"""
Market Data Loader following Hedge Fund standards for Backtest, Hyperopt, WFO.
Supports multi-timeframe access and training/testing window selection.
"""
import os
import pandas as pd
from datetime import datetime
from shared.logger import logger


class MarketDataLoader:
    """
    Universal loader for any timeframe.
    Works for Backtest, Hyperopt, WFO.
    """

    def __init__(self, root_raw="./data/history/raw/", root_processed="./data/history/processed/"):
        self.root_raw = root_raw
        self.root_processed = root_processed
        logger.info(f"MarketDataLoader initialized. Raw: {self.root_raw}, Processed: {self.root_processed}")

    def _path(self, symbol, timeframe):
        """
        Get path for data file based on timeframe:
        - raw/1m
        - processed/5m, 15m, 1h, etc.
        """
        if timeframe == "1m":
            return f"{self.root_raw}/1m/{symbol}.csv"
        return f"{self.root_processed}/{timeframe}/{symbol}.csv"

    def load(self, symbol: str, timeframe="1m"):
        """
        Load any timeframe.
        Output: Cleaned DataFrame (timestamp sorted).
        """
        path = self._path(symbol, timeframe)

        if not os.path.exists(path):
            raise Exception(f"Data not found: {path}")

        df = pd.read_csv(path)

        # Ensure proper formatting
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        for c in required_cols:
            if c not in df.columns:
                raise Exception(f"Invalid data format in {symbol} {timeframe}")

        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)

        logger.info(f"Loaded {len(df)} records for {symbol} {timeframe}")
        return df

    def load_range(self, symbol, timeframe, start_date, end_date):
        """
        Load only the specific training/testing window.
        Perfect for WFO.
        """
        df = self.load(symbol, timeframe)

        start_ms = self._to_ms(start_date)
        end_ms = self._to_ms(end_date)

        # Filter by timestamp range
        mask = (df["timestamp"] >= start_ms) & (df["timestamp"] <= end_ms)
        result = df.loc[mask].reset_index(drop=True)
        
        logger.info(f"Loaded range for {symbol} {timeframe} from {start_date} to {end_date}: {len(result)} records")
        return result

    def _to_ms(self, s: str):
        """
        Convert '2024-01-01' → ms timestamp
        """
        dt = datetime.strptime(s, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)

    def gap_check(self, df, timeframe):
        """
        Detect missing candles.
        Only for safety-check in Backtest/WFO.
        """
        tf_map = {
            "1m": 60_000,
            "5m": 300_000,
            "15m": 900_000,
            "30m": 1_800_000,
            "1h": 3_600_000,
        }

        if timeframe not in tf_map:
            logger.warning(f"Unknown timeframe {timeframe}, using 1m gap size for gap check")
            step = 60_000
        else:
            step = tf_map[timeframe]
        
        ts = df["timestamp"].values

        gaps = []
        for i in range(1, len(ts)):
            diff = ts[i] - ts[i - 1]
            if diff > step:
                gaps.append((ts[i - 1], ts[i], diff))

        logger.info(f"Gap check for {len(df)} records of {timeframe}: {len(gaps)} gaps found")
        return gaps

    def load_multiple_timeframes(self, symbol, timeframes):
        """
        Load multiple timeframes for a single symbol.
        Useful for multi-timeframe strategies.
        """
        results = {}
        for tf in timeframes:
            try:
                results[tf] = self.load(symbol, tf)
                logger.info(f"Loaded timeframe {tf} for {symbol}: {len(results[tf])} records")
            except Exception as e:
                logger.error(f"Failed to load {symbol} {tf}: {e}")
                results[tf] = pd.DataFrame()  # Return empty DataFrame on error
        return results


if __name__ == "__main__":
    # Example usage
    loader = MarketDataLoader()
    
    # Example: Load data 
    try:
        # This will work if you have data files in the expected locations
        # df = loader.load("BTCUSDT", "5m")
        # print(f"Loaded {len(df)} records")
        
        # Example range loading (for WFO)
        # df_range = loader.load_range("BTCUSDT", "5m", "2024-01-01", "2024-01-31")
        # print(f"Loaded {len(df_range)} records in range")
        
        pass
    except Exception as e:
        logger.error(f"Example usage error: {e}")