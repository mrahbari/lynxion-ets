"""CSV History Loader for multi-asset data loading compatible with existing architecture."""

import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import os
import logging
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

        # Initialize logger
        self.logger = logging.getLogger("CSVHistoryLoaderAdapter")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

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
            # Convert datetime index back to Unix timestamp
            unix_timestamp = int(idx.timestamp())
            result.append({
                'timestamp': unix_timestamp,
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
        df = self.load_symbol_data(symbol, timeframe)

        # Reset index to convert datetime index back to timestamp column as integer
        df_reset = df.reset_index()
        df_reset['timestamp'] = df_reset['timestamp'].astype('int64') // 10**9  # Convert to Unix timestamp

        # Set timestamp as column instead of index to maintain Unix timestamp format
        return df_reset

    def load_symbol_data(self, symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """
        Load data for a specific symbol and timeframe as DataFrame.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT', 'ETHUSDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')

        Returns:
            DataFrame with OHLCV data
        """
        # Look for data in the correct path structure: data/history/raw/timeframe/formatted_symbol.csv
        # Format symbol for storage (e.g., BTCUSDT -> BTC-USDT.csv)
        formatted_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol else symbol
        file_path = self.base_path / "history" / "raw" / timeframe / f"{formatted_symbol}.csv"

        if not file_path.exists():
            # Try alternative path structure: data/history/raw/timeframe/symbol.csv (without formatting)
            alt_path = self.base_path / "history" / "raw" / timeframe / f"{symbol}.csv"
            if alt_path.exists():
                file_path = alt_path
            else:
                # Try alternative path structure: data/symbol/timeframe.csv
                alt_path2 = self.base_path / symbol / f"{timeframe}.csv"
                if alt_path2.exists():
                    file_path = alt_path2
                else:
                    # Try the format that matches the existing files (e.g., BTC-USDT.csv format)
                    formatted_symbol_alt = symbol.replace('USDT', '-USDT')  # Convert BTCUSDT to BTC-USDT
                    formatted_path = self.base_path / f"{formatted_symbol_alt}.csv"
                    if formatted_path.exists():
                        file_path = formatted_path
                    else:
                        # Try the exact format from the data directory
                        exact_path = self.base_path / f"{symbol}.csv"
                        if exact_path.exists():
                            file_path = exact_path
                        else:
                            # Define default values for paths that might not be defined in all code paths
                            alt_path_val = str(alt_path) if 'alt_path' in locals() else 'N/A'
                            alt_path2_val = str(alt_path2) if 'alt_path2' in locals() else 'N/A'
                            formatted_path_val = str(formatted_path) if 'formatted_path' in locals() else 'N/A'
                            exact_path_val = str(exact_path) if 'exact_path' in locals() else 'N/A'
                            raise FileNotFoundError(f"Data file not found: {file_path}, {alt_path_val}, {alt_path2_val}, {formatted_path_val}, or {exact_path_val}")
        
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
        
        # Ensure timestamp column is integer Unix timestamp
        if df['timestamp'].dtype in ['object', 'float64']:
            # Handle mixed formats - could be datetime string or numeric value
            def convert_timestamp_format(ts):
                if pd.isna(ts):
                    return ts
                if isinstance(ts, (int, float)):
                    # If it's already numeric, convert to int
                    ts_int = int(float(ts))
                    # Check if it looks like milliseconds (too large for seconds)
                    if ts_int > 1e10:  # Likely milliseconds
                        return ts_int // 1000
                    else:
                        return ts_int
                else:
                    # It's a string, try to parse as datetime
                    try:
                        # Parse the datetime string and convert to Unix timestamp
                        dt = pd.to_datetime(str(ts), utc=True)
                        return int(dt.timestamp())
                    except:
                        # If parsing fails, raise an error
                        raise ValueError(f"Unable to parse timestamp: {ts}")

            df['timestamp'] = df['timestamp'].apply(convert_timestamp_format)
        elif df['timestamp'].dtype == 'int64':
            # Already integer, assume it's Unix timestamp - verify it looks like a valid timestamp
            max_timestamp = df['timestamp'].max() if len(df) > 0 else 0
            if max_timestamp > 1e10:  # Likely milliseconds, convert to seconds
                df['timestamp'] = df['timestamp'].astype('int64') // 1000

        # Now convert Unix timestamps to datetime for the index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

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

    def save_historical_data(self, symbol: str, data: List[Dict[str, Any]], timeframe: str = "1m"):
        """
        Save historical data to CSV file for local caching.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            data: List of historical data points
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
        """
        if not data:
            return

        # Create directory if it doesn't exist
        # Use the correct path structure: data/history/raw/timeframe/
        # Save file as: data/history/raw/timeframe/SOL-USDT.csv
        timeframe_dir = self.base_path / "history" / "raw" / timeframe
        timeframe_dir.mkdir(parents=True, exist_ok=True)

        # Create DataFrame from data
        df = pd.DataFrame(data)

        # Ensure required columns exist
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in required_cols:
            if col not in df.columns:
                if col == "open":
                    df[col] = 0.0
                elif col == "high":
                    df[col] = 0.0
                elif col == "low":
                    df[col] = 0.0
                elif col == "close":
                    df[col] = 0.0
                elif col == "volume":
                    df[col] = 0.0
                elif col == "timestamp":
                    df[col] = int(datetime.now().timestamp())

        # Ensure timestamp is in Unix timestamp integer format (seconds since epoch)
        if 'timestamp' in df.columns:
            # Convert timestamp to integer Unix timestamp if it's not already
            if df['timestamp'].dtype in ['object', 'float64']:
                try:
                    # If it's a datetime string, convert to Unix timestamp
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).astype('int64') // 10**9
                except:
                    # If it's numeric but not int64, convert directly
                    try:
                        df['timestamp'] = df['timestamp'].astype('int64')
                    except:
                        # If it's still not working, try to interpret as float seconds
                        df['timestamp'] = df['timestamp'].astype(float).astype('int64')
            elif df['timestamp'].dtype == 'int64':
                # Already integer, ensure it's a Unix timestamp (not milliseconds)
                max_timestamp = df['timestamp'].max() if len(df) > 0 else 0
                if max_timestamp > 1e10:  # Likely milliseconds, convert to seconds
                    df['timestamp'] = df['timestamp'].astype('int64') // 1000

        # Format symbol for storage (e.g., BTCUSDT -> BTC-USDT)
        formatted_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol else symbol
        # Save to CSV file with the correct format: e.g., SOL-USDT.csv in the timeframe directory
        file_path = timeframe_dir / f"{formatted_symbol}.csv"

        # If file already exists, load it and merge with new data
        if file_path.exists():
            try:
                existing_df = pd.read_csv(file_path)

                # Handle mixed timestamp formats in existing file
                if 'timestamp' in existing_df.columns:
                    # Convert timestamp column to proper Unix timestamp format
                    def convert_timestamp_format(ts):
                        if pd.isna(ts):
                            return ts
                        if isinstance(ts, (int, float)):
                            # If it's already numeric, convert to int
                            ts_int = int(float(ts))
                            # Check if it looks like milliseconds (too large for seconds)
                            if ts_int > 1e10:  # Likely milliseconds
                                return ts_int // 1000
                            else:
                                return ts_int
                        else:
                            # It's a string, try to parse as datetime
                            try:
                                # Parse the datetime string and convert to Unix timestamp
                                dt = pd.to_datetime(str(ts), utc=True)
                                return int(dt.timestamp())
                            except:
                                # If parsing fails, return original value (will cause error later)
                                return ts

                    existing_df['timestamp'] = existing_df['timestamp'].apply(convert_timestamp_format)

                    # Remove any rows where timestamp conversion failed
                    existing_df = existing_df[pd.to_numeric(existing_df['timestamp'], errors='coerce').notna()]
                    existing_df['timestamp'] = existing_df['timestamp'].astype('int64')

                # Combine new data with existing data
                combined_df = pd.concat([existing_df, df])

                # Remove duplicates, keeping the latest values
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')

                # Sort by timestamp to maintain chronological order
                combined_df = combined_df.sort_values('timestamp')

                # Save the combined data with Unix timestamps
                combined_df.to_csv(file_path, index=False)

                print(f"Updated {symbol} data: {len(existing_df)} existing rows, {len(df)} new rows, {len(combined_df)} total rows in {file_path}")
            except Exception as e:
                self.logger.warning(f"Could not update existing file for {symbol}, overwriting: {e}")
                # If there's an issue with merging, just save the new data
                df.to_csv(file_path, index=False)
                print(f"Saved {len(data)} data points for {symbol} to {file_path}")
        else:
            # If file doesn't exist, save as new
            df.to_csv(file_path, index=False)
            print(f"Saved {len(data)} data points for {symbol} to {file_path}")


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