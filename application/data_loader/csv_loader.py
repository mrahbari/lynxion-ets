"""CSV History Loader for multi-asset data loading."""

import pandas as pd
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import os


class CSVHistoryLoader:
    """Load historical market data from CSV files for multiple assets and timeframes."""

    def __init__(self, base_path: str = "./data"):
        """
        Initialize the CSV history loader.
        
        Args:
            base_path: Base directory path for data files
        """
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def load(self, symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """
        Load historical data for a specific symbol and timeframe.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT', 'ETHUSDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            
        Returns:
            DataFrame with OHLCV data
        """
        file_path = self.base_path / symbol / f"{timeframe}.csv"
        
        if not file_path.exists():
            # Try alternative naming convention
            alt_path = self.base_path / f"{symbol}_{timeframe}.csv"
            if alt_path.exists():
                file_path = alt_path
            else:
                raise FileNotFoundError(f"Data file not found: {file_path} or {alt_path}")
        
        df = pd.read_csv(file_path)
        
        # Ensure required columns exist
        required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset(set(df.columns.str.lower())):
            # Try common variations
            col_mapping = {}
            for col in required_cols:
                found = False
                for df_col in df.columns:
                    if col.lower() in df_col.lower() or df_col.lower() in col.lower():
                        col_mapping[df_col] = col
                        found = True
                        break
                if not found:
                    raise ValueError(f"Required column '{col}' not found in data")
            
            df = df.rename(columns=col_mapping)
        
        # Convert timestamp to datetime if it's not already
        if df['timestamp'].dtype == 'object':
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            except:
                # Try to handle timestamp in milliseconds or seconds
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                except:
                    try:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                    except:
                        raise ValueError("Unable to parse timestamp column")
        
        # Set timestamp as index and sort
        df = df.set_index('timestamp').sort_index()
        
        # Validate data quality
        df = self._validate_and_clean(df)
        
        return df

    def load_multi_assets(self, symbols: list, timeframe: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        Load historical data for multiple symbols and timeframes.
        
        Args:
            symbols: List of trading symbols
            timeframe: Timeframe for all symbols
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        datasets = {}
        for symbol in symbols:
            try:
                df = self.load(symbol, timeframe)
                if not df.empty:
                    datasets[symbol] = df
            except FileNotFoundError:
                print(f"Warning: Data file for {symbol} not found, skipping...")
                continue
        
        return datasets

    def _validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean the loaded data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Cleaned DataFrame
        """
        # Remove any rows with missing OHLCV data
        df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
        
        # Validate OHLC relationships
        # High should be >= Open, Low, Close
        df['high'] = df[['high', 'open', 'low', 'close']].max(axis=1)
        df['low'] = df[['high', 'open', 'low', 'close']].min(axis=1)
        
        # Volume should be non-negative
        df['volume'] = df['volume'].clip(lower=0)
        
        # Remove any remaining invalid rows
        df = df[df['high'] >= df['low']]
        df = df[df['volume'] >= 0]
        
        # Reset index and ensure proper sorting
        df = df.sort_index()
        
        return df