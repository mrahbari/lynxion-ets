"""Comprehensive coin history service with caching and fallback logic."""

import os
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from pathlib import Path
from collections import OrderedDict

from shared.logger import EnhancedLogger


class LRUCache:
    """Simple LRU cache implementation to limit memory usage."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = OrderedDict()

    def get(self, key: str) -> Optional[pd.DataFrame]:
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: pd.DataFrame):
        if key in self.cache:
            # Update existing key
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used item
            self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self):
        self.cache.clear()

    def size(self):
        return len(self.cache)

    def keys(self):
        return list(self.cache.keys())


class CoinHistoryService:
    """
    Comprehensive service for fetching, caching, and managing coin historical data.
    Supports multiple timeframes, fallback logic for missing data, and intelligent caching.
    """

    def __init__(self,
                 cache_dir: str = "data/coin_history_cache",
                 max_cache_age_hours: int = 24,
                 default_timeframe: str = "1h",
                 max_cache_size: int = 50):  # Limit to 50 cached items
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_age_hours = max_cache_age_hours
        self.default_timeframe = default_timeframe
        self.logger = EnhancedLogger("CoinHistoryService")

        # Initialize LRU cache to limit memory usage
        self.memory_cache = LRUCache(max_size=max_cache_size)

        # Timeframe intervals in minutes for validation
        self.valid_timeframes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }

        # Simulated broker adapter for now (would be replaced with real broker in production)
        self.broker_adapter = SimulatedBrokerAdapter()
    
    def fetch_historical_data(self,
                            symbol: str,
                            timeframe: str = None,
                            limit: int = 1000,
                            start_date: datetime = None,
                            end_date: datetime = None,
                            use_cache: bool = True,
                            fallback_timeframes: List[str] = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a coin with caching and fallback logic.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe string (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch
            start_date: Start date for historical data (optional)
            end_date: End date for historical data (optional)
            use_cache: Whether to use cached data if available
            fallback_timeframes: List of timeframes to try if primary fails
            
        Returns:
            DataFrame with historical data or None if all attempts fail
        """
        if timeframe is None:
            timeframe = self.default_timeframe
            
        if timeframe not in self.valid_timeframes:
            self.logger.error(f"Invalid timeframe: {timeframe}. Valid options: {list(self.valid_timeframes.keys())}")
            return None
            
        if fallback_timeframes is None:
            fallback_timeframes = self._get_fallback_timeframes(timeframe)
        
        # Check cache first
        if use_cache:
            cached_df = self._load_from_cache(symbol, timeframe)
            if cached_df is not None:
                self.logger.info(f"Loaded {symbol} {timeframe} from cache")
                return cached_df
        
        # Try primary timeframe
        df = self._fetch_from_broker(symbol, timeframe, limit, start_date, end_date)
        
        # If primary fails, try fallback timeframes
        attempts = [timeframe] + fallback_timeframes
        for attempt_timeframe in attempts:
            if df is None or df.empty:
                self.logger.warning(f"Failed to fetch {symbol} {attempt_timeframe}, trying fallback...")
                df = self._fetch_from_broker(symbol, attempt_timeframe, limit, start_date, end_date)
                
            if df is not None and not df.empty:
                self.logger.info(f"Successfully fetched {symbol} {attempt_timeframe}")
                # Cache successful result
                self._save_to_cache(df, symbol, attempt_timeframe)
                return df
            else:
                self.logger.warning(f"Failed to fetch {symbol} {attempt_timeframe}")
        
        self.logger.error(f"All attempts to fetch {symbol} data failed")
        return None
    
    def _get_fallback_timeframes(self, primary_timeframe: str) -> List[str]:
        """Get appropriate fallback timeframes based on primary timeframe."""
        # More granular timeframes for smaller primary
        fallback_map = {
            '1m': ['5m', '15m', '1h'],
            '5m': ['1m', '15m', '30m', '1h'], 
            '15m': ['5m', '30m', '1h', '4h'],
            '30m': ['15m', '1h', '4h'],
            '1h': ['30m', '4h', '15m', '1d'],
            '4h': ['1h', '1d', '30m'],
            '1d': ['4h', '1h']
        }
        return fallback_map.get(primary_timeframe, ['1h', '4h'])
    
    def _load_from_cache(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load data from memory cache first, then file cache if available and not expired."""
        # Create cache key
        cache_key = f"{symbol}_{timeframe}"

        # Check memory cache first (faster access)
        cached_data = self.memory_cache.get(cache_key)
        if cached_data is not None:
            self.logger.debug(f"Loaded {len(cached_data)} rows from memory cache for {symbol} {timeframe}")
            return cached_data

        # If not in memory cache, check file cache
        cache_path = self._get_cache_path(symbol, timeframe)

        if not cache_path.exists():
            return None

        # Check if cache is expired
        cache_modified = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - cache_modified > timedelta(hours=self.max_cache_age_hours):
            self.logger.info(f"Cache expired for {symbol} {timeframe}")
            # Remove expired file
            cache_path.unlink(missing_ok=True)
            return None

        try:
            # Try to load as pickle first, then as CSV
            if cache_path.suffix == '.pkl':
                with open(cache_path, 'rb') as f:
                    file_data = pickle.load(f)
            else:
                file_data = pd.read_csv(cache_path)

            # Convert timestamp column if it exists
            if 'timestamp' in file_data.columns:
                if not pd.api.types.is_datetime64_any_dtype(file_data['timestamp']):
                    file_data['timestamp'] = pd.to_datetime(file_data['timestamp'])

            # Add to memory cache before returning
            self.memory_cache.put(cache_key, file_data)

            self.logger.info(f"Loaded {len(file_data)} rows from file cache for {symbol} {timeframe}")
            return file_data

        except Exception as e:
            self.logger.error(f"Error loading cache for {symbol} {timeframe}: {e}")
            return None
    
    def _save_to_cache(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Save data to both file cache and memory cache."""
        try:
            # Create cache key
            cache_key = f"{symbol}_{timeframe}"

            # Add to memory cache first
            self.memory_cache.put(cache_key, df)

            # Save to file cache
            cache_path = self._get_cache_path(symbol, timeframe)

            # Make sure timestamp is in the right format for caching
            df_to_save = df.copy()
            if 'timestamp' in df_to_save.columns:
                df_to_save['timestamp'] = pd.to_datetime(df_to_save['timestamp'])

            # Save as pickle for better performance
            with open(cache_path, 'wb') as f:
                pickle.dump(df_to_save, f)

            self.logger.info(f"Saved {len(df)} rows to cache (memory + file) for {symbol} {timeframe}")
        except Exception as e:
            self.logger.error(f"Error saving cache for {symbol} {timeframe}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache usage."""
        return {
            "memory_cache_size": self.memory_cache.size(),
            "memory_cache_max_size": self.memory_cache.max_size,
            "file_cache_directory": str(self.cache_dir),
            "cache_keys": self.memory_cache.keys()
        }
    
    def _get_cache_path(self, symbol: str, timeframe: str) -> Path:
        """Get cache file path for a symbol and timeframe."""
        normalized_symbol = symbol.replace('/', '_').replace(':', '_').replace('-', '_')
        return self.cache_dir / f"{normalized_symbol}_{timeframe}.pkl"
    
    def _fetch_from_broker(self, 
                          symbol: str, 
                          timeframe: str, 
                          limit: int, 
                          start_date: datetime = None, 
                          end_date: datetime = None) -> Optional[pd.DataFrame]:
        """Fetch data from broker adapter."""
        try:
            # For now, use the broker adapter; in production this would connect to real exchange
            df = self.broker_adapter.fetch_ohlcv(symbol, timeframe, limit, start_date, end_date)
            return df
        except Exception as e:
            self.logger.error(f"Error fetching {symbol} {timeframe} from broker: {e}")
            return None
    
    def validate_data_quality(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Validate the quality of historical data.

        Returns metrics about data quality.
        """
        if df is None or df.empty:
            return {
                'valid': False,
                'reason': 'No data available',
                'metrics': {}
            }

        metrics = {
            'total_candles': len(df),
            'missing_values': df.isnull().sum().to_dict(),
            'date_range': {
                'start': df['timestamp'].min() if 'timestamp' in df.columns else None,
                'end': df['timestamp'].max() if 'timestamp' in df.columns else None
            },
            'volume_zero_count': len(df[df['volume'] == 0]) if 'volume' in df.columns else 0,
            'price_anomalies': self._detect_price_anomalies(df),
            'gaps_count': self._count_gaps(df),
            'data_completeness_ratio': self._calculate_completeness_ratio(df)
        }

        # Check for reasonable data
        valid = (
            len(df) > 10 and  # At least 10 candles
            metrics['volume_zero_count'] / len(df) < 0.5 and  # Less than 50% zero volume
            metrics['price_anomalies']['suspicious_count'] / len(df) < 0.1 and  # Less than 10% anomalies
            metrics['data_completeness_ratio'] > 0.7  # At least 70% data completeness
        )

        return {
            'valid': valid,
            'reason': 'Data quality acceptable' if valid else 'Data quality issues detected',
            'metrics': metrics
        }

    def _count_gaps(self, df: pd.DataFrame) -> int:
        """Count significant gaps in the data."""
        if len(df) < 2 or 'timestamp' not in df.columns:
            return 0

        # Sort by timestamp first
        df_sorted = df.sort_values('timestamp')
        time_diffs = df_sorted['timestamp'].diff().dt.total_seconds()

        # Count gaps larger than expected based on timeframe
        # This is an estimate - assumes 1H data has ~3600s intervals
        expected_interval = 3600  # Default to 1 hour
        if len(df) > 1:
            time_range = (df_sorted['timestamp'].max() - df_sorted['timestamp'].min()).total_seconds()
            expected_interval = time_range / len(df)

        gap_threshold = expected_interval * 2  # Consider gaps 2x larger than expected as significant
        gaps_count = (time_diffs > gap_threshold).sum()

        return int(gaps_count - 1) if gaps_count > 0 else 0  # Subtract 1 because first diff is NaT

    def _calculate_completeness_ratio(self, df: pd.DataFrame) -> float:
        """Calculate the ratio of actual data vs expected complete data."""
        if len(df) < 2 or 'timestamp' not in df.columns:
            return 0.0 if len(df) == 0 else 1.0

        df_sorted = df.sort_values('timestamp').reset_index(drop=True)
        total_time_range = (df_sorted['timestamp'].max() - df_sorted['timestamp'].min()).total_seconds()

        # Estimate expected number of candles based on first few intervals
        intervals = []
        for i in range(1, min(10, len(df_sorted))):  # Check first 10 intervals
            interval = (df_sorted['timestamp'].iloc[i] - df_sorted['timestamp'].iloc[i-1]).total_seconds()
            if interval > 0:  # Avoid zero intervals
                intervals.append(interval)

        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            expected_candles = total_time_range / avg_interval if avg_interval > 0 else len(df_sorted)
            completeness = len(df_sorted) / expected_candles if expected_candles > 0 else 0.0
            return min(completeness, 1.0)  # Cap at 1.0
        else:
            return 1.0 if len(df) > 0 else 0.0

    def handle_missing_data(self, df: pd.DataFrame, symbol: str,
                          fill_method: str = 'interpolate') -> pd.DataFrame:
        """
        Handle missing data in the DataFrame using various strategies.

        Args:
            df: Input DataFrame with potentially missing data
            symbol: Symbol for logging
            fill_method: Method to handle missing data ('interpolate', 'forward', 'backward', 'drop')

        Returns:
            DataFrame with missing data handled
        """
        if df is None or df.empty:
            self.logger.warning(f"No data to handle for {symbol}")
            return df

        original_length = len(df)

        if fill_method == 'interpolate':
            # Interpolate numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df_filled = df.copy()
            df_filled[numeric_cols] = df_filled[numeric_cols].interpolate()

            # Forward fill for timestamp if missing
            if 'timestamp' in df_filled.columns:
                df_filled['timestamp'].fillna(method='ffill', inplace=True)

        elif fill_method == 'forward':
            df_filled = df.fillna(method='ffill')

        elif fill_method == 'backward':
            df_filled = df.fillna(method='bfill')

        elif fill_method == 'drop':
            df_filled = df.dropna()

        else:
            self.logger.warning(f"Unknown fill method {fill_method}, returning original data")
            return df

        self.logger.info(f"Handled missing data for {symbol}: {original_length} -> {len(df_filled)} rows")
        return df_filled
    
    def _detect_price_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect suspicious price movements or anomalies."""
        if len(df) < 2:
            return {'suspicious_count': 0, 'details': []}
        
        # Calculate price changes
        if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
            # Check for impossible price relationships
            invalid_rows = df[df['high'] < df['low']].index
            close_outside_range = df[(df['close'] > df['high']) | (df['close'] < df['low'])].index
            
            return {
                'suspicious_count': len(invalid_rows) + len(close_outside_range),
                'details': {
                    'invalid_high_low': invalid_rows.tolist(),
                    'close_outside_range': close_outside_range.tolist()
                }
            }
        
        return {'suspicious_count': 0, 'details': []}
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from cache and/or broker."""
        # First, get symbols from cache
        cached_symbols = []
        for file_path in self.cache_dir.glob("*.pkl"):
            filename = file_path.stem
            # Extract symbol from filename like BTC_USDT_1h.pkl
            parts = filename.split('_')
            if len(parts) >= 2:
                symbol = f"{parts[0]}/{parts[1]}"
                cached_symbols.append(symbol)
        
        # Then get symbols from broker if available
        broker_symbols = self.broker_adapter.get_available_symbols()
        
        # Combine and remove duplicates
        all_symbols = list(set(cached_symbols + broker_symbols))
        return all_symbols


class SimulatedBrokerAdapter:
    """
    Simulated broker adapter for testing purposes.
    In production, this would be replaced with actual broker integrations.
    """
    
    def __init__(self):
        self.logger = EnhancedLogger("SimulatedBrokerAdapter")
    
    def fetch_ohlcv(self, 
                   symbol: str, 
                   timeframe: str, 
                   limit: int = 1000, 
                   start_date: datetime = None, 
                   end_date: datetime = None) -> pd.DataFrame:
        """Simulate fetching OHLCV data."""
        try:
            # Generate synthetic data for demonstration
            if start_date is None:
                # Start from 30 days ago by default
                start_date = datetime.now() - timedelta(days=30)
            
            # Calculate the timeframe in minutes
            timeframe_minutes = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '4h': 240, '1d': 1440
            }.get(timeframe, 60)
            
            # Calculate number of periods needed
            if end_date:
                total_minutes = (end_date - start_date).total_seconds() / 60
                periods = int(total_minutes / timeframe_minutes)
                if periods > limit:
                    periods = limit
            else:
                periods = min(limit, 1000)  # Cap at 1000 for demo
            
            # Generate timestamps
            timestamps = []
            current_time = start_date
            for _ in range(periods):
                timestamps.append(current_time)
                current_time += timedelta(minutes=timeframe_minutes)
            
            # Generate synthetic OHLCV data
            np.random.seed(hash(symbol) % 2**32)  # Use symbol hash as seed for consistent data
            base_price = 100 + hash(symbol) % 1000  # Different base price per symbol
            
            opens = [base_price]
            closes = []
            highs = []
            lows = []
            volumes = []
            
            for i in range(len(timestamps)):
                # Generate price movements
                if i == 0:
                    open_price = base_price
                else:
                    # Previous close becomes this open
                    open_price = closes[-1]
                
                # Random movement
                volatility = 0.02  # 2% daily volatility
                movement = np.random.normal(0, volatility)
                close_price = open_price * (1 + movement)
                
                # High and low are around the range
                high_multiplier = 1 + abs(np.random.normal(0, 0.01))
                low_multiplier = 1 - abs(np.random.normal(0, 0.01))
                
                high_price = max(open_price, close_price) * high_multiplier
                low_price = min(open_price, close_price) * low_multiplier
                
                opens.append(open_price)
                closes.append(close_price)
                highs.append(high_price)
                lows.append(low_price)
                volumes.append(np.random.uniform(1000000, 10000000))  # Random volume
            
            # Remove first open (it was just a base)
            opens = opens[1:]
            
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            })
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error in simulated fetch for {symbol}: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
    
    def get_available_symbols(self) -> List[str]:
        """Return list of available symbols."""
        # Return some common symbols for simulation
        return [
            'BTC/USDT',
            'ETH/USDT', 
            'SOL/USDT',
            'XRP/USDT',
            'ADA/USDT',
            'DOGE/USDT'
        ]