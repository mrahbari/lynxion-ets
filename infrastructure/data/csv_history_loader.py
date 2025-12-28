"""CSV History Loader for multi-asset data loading compatible with existing architecture."""

import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import os
from domain.ports.data_ports import DataProviderPort
from domain.entities.trading_entities import MarketData
from domain.value_objects import Symbol


class CSVHistoryLoaderAdapter(DataProviderPort):
    """CSV-based historical data provider for the WFO pipeline."""

    def __init__(self, base_path: str = "./data"):
        """
        Initialize the CSV history loader.

        Args:
            base_path: Base directory path for data files
        """
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def get_current_price(self, symbol: Symbol) -> float:
        """Get the current price for a symbol from the latest CSV data."""
        try:
            df = self._load_symbol_data(symbol.value)
            if not df.empty:
                return float(df['close'].iloc[-1])
        except:
            pass
        return 0.0

    def subscribe_to_market_data(self, symbol: Symbol, callback) -> str:
        """CSV loader doesn't support real-time data, so this is not implemented."""
        # This is a historical data loader, so we can't subscribe to live data
        # Return a special subscription ID to indicate that real-time is not supported
        return f"csv_unsupported_{symbol.value}"

    def unsubscribe_from_market_data(self, subscription_id: str):
        """Unsubscribe from real-time market data."""
        # No-op for CSV loader since it doesn't support real-time data
        pass

    def get_historical_data(self, symbol: Symbol, period: str, timeframe: str = '1m') -> List[Dict[str, Any]]:
        """
        Get historical data for a symbol from CSV files.

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            period: Period string (e.g., '30d', '90d', '1y')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')

        Returns:
            List of historical data points
        """
        df = self.load_symbol_data(symbol.value, timeframe)

        # Convert period to date range if needed
        # For now, return all available data since we're loading from CSV files
        # In a real implementation, you'd filter based on the period

        # Convert to list of dictionaries format expected by system
        result = []
        for idx, row in df.iterrows():
            result.append({
                'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        return result

    def load(self, symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """
        Load historical data for a specific symbol and timeframe as DataFrame.
        This method matches the interface expected by the orchestrator.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT', 'ETHUSDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')

        Returns:
            DataFrame with OHLCV data
        """
        return self.load_symbol_data(symbol, timeframe)

    def load_symbol_data(self, symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """
        Load data for a specific symbol and timeframe as DataFrame.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT', 'ETHUSDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')

        Returns:
            DataFrame with OHLCV data
        """
        file_path = self.base_path / symbol / f"{timeframe}.csv"

        if not file_path.exists():
            # Try alternative naming convention (e.g., BTC-USDT.csv format)
            alt_path = self.base_path / f"{symbol}_{timeframe}.csv"
            if alt_path.exists():
                file_path = alt_path
            else:
                # Try the format that matches the existing files (e.g., BTC-USDT.csv)
                formatted_symbol = symbol.replace('USDT', '-USDT')  # Convert BTCUSDT to BTC-USDT
                formatted_path = self.base_path / f"{formatted_symbol}.csv"
                if formatted_path.exists():
                    file_path = formatted_path
                else:
                    # Try the exact format from the data directory
                    exact_path = self.base_path / f"{symbol}.csv"
                    if exact_path.exists():
                        file_path = exact_path
                    else:
                        raise FileNotFoundError(f"Data file not found: {file_path}, {alt_path}, {formatted_path}, or {exact_path}")
        
        df = pd.read_csv(file_path)
        
        # Ensure required columns exist
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        if not all(col in df.columns.str.lower() for col in required_cols):
            # Try to map common variations
            col_mapping = {}
            for req_col in required_cols:
                found = False
                for df_col in df.columns:
                    if req_col.lower() in df_col.lower() or df_col.lower() in req_col.lower():
                        col_mapping[df_col] = req_col
                        found = True
                        break
                if not found:
                    raise ValueError(f"Required column '{req_col}' not found in data")
            
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
        
        # Validate and clean data
        df = self._validate_and_clean(df)
        
        return df

    def load_multi_assets(self, symbols: List[str], timeframe: str = "1d") -> Dict[str, pd.DataFrame]:
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
                df = self.load_symbol_data(symbol, timeframe)
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

    def _load_symbol_data(self, symbol: str) -> pd.DataFrame:
        """Internal method to load symbol data with default settings."""
        return self.load_symbol_data(symbol, "1m")  # Use 1m data since we're looking at 1m files


def load_csv_data_direct(symbol: str, base_path: str = "./data") -> pd.DataFrame:
    """
    Direct function to load CSV data without going through the port interface.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        base_path: Base path for data files
        
    Returns:
        DataFrame with OHLCV data
    """
    loader = CSVHistoryLoaderAdapter(base_path)
    return loader.load_symbol_data(symbol)