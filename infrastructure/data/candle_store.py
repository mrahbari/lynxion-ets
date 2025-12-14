"""
Candle Store for managing storage, merge, dedup of candle data.
Following Hedge Fund standards for production-level data storage.
"""
import os
import pandas as pd
from datetime import datetime
from shared.logger import logger


class CandleStore:
    def __init__(self, root="./data/history/raw/1m/"):
        self.root = root
        os.makedirs(self.root, exist_ok=True)
        logger.info(f"CandleStore initialized with root: {self.root}")

    def _path(self, symbol):
        return f"{self.root}/{symbol}.csv"

    def load_existing(self, symbol):
        path = self._path(symbol)
        if os.path.exists(path):
            df = pd.read_csv(path)
            logger.info(f"Loaded existing data for {symbol}: {len(df)} records")
            return df
        logger.info(f"No existing data for {symbol}, creating new DataFrame")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    def save(self, symbol, df):
        """Save DataFrame to CSV"""
        path = self._path(symbol)
        df.to_csv(path, index=False)
        logger.info(f"Saved {len(df)} records for {symbol} to {path}")

    def merge_and_clean(self, symbol, new_df):
        """
        Merge new data with existing, remove duplicates, sort by timestamp.
        """
        if new_df.empty:
            logger.warning(f"No new data to merge for {symbol}")
            return self.load_existing(symbol)

        df_old = self.load_existing(symbol)
        
        if df_old.empty:
            logger.info(f"No existing data for {symbol}, returning new data as-is")
            # Just sort and deduplicate the new data
            df = new_df.copy()
            df.drop_duplicates(subset=["timestamp"], inplace=True)
            df.sort_values("timestamp", inplace=True)
            return df
        else:
            # Merge old and new data
            df = pd.concat([df_old, new_df], ignore_index=True)
            df.drop_duplicates(subset=["timestamp"], inplace=True)
            df.sort_values("timestamp", inplace=True)
            logger.info(f"Merged {len(new_df)} new records with {len(df_old)} existing records for {symbol}, resulting in {len(df)} total records after deduplication and sorting")
            return df