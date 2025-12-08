"""
Multi-Timeframe Synchronization Engine based on Enterprise Hedge Fund Architecture
Ensures proper alignment between different timeframes without lookahead bias
"""
import pandas as pd
from typing import Dict, Tuple, Optional
import numpy as np


class MultiTimeframeSynchronizer:
    """
    Synchronization engine for aligning different timeframes
    """
    def __init__(self):
        pass

    def resample_to_timeframe(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Resample dataframe to target timeframe using OHLC aggregation
        """
        if df.empty:
            return df

        # Ensure the index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be a DatetimeIndex")

        # Define the aggregation rules
        aggregation = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        # Add any other numeric columns to aggregate as sum
        for col in df.columns:
            if col not in aggregation and pd.api.types.is_numeric_dtype(df[col]):
                aggregation[col] = 'last'  # Use last value for other columns

        # Resample using the aggregation rules
        resampled = df.resample(target_timeframe).agg(aggregation)
        
        # Drop any rows with NaN values that may have been created
        resampled = resampled.dropna()
        
        return resampled

    def forward_fill_align(self, low_tf_df: pd.DataFrame, high_tf_df: pd.DataFrame) -> pd.DataFrame:
        """
        Align high timeframe data to low timeframe using forward fill
        This ensures high TF data is aligned to the appropriate low TF timestamps
        without lookahead bias
        """
        # Ensure both dataframes are sorted by timestamp
        low_tf_df = low_tf_df.sort_index()
        high_tf_df = high_tf_df.sort_index()
        
        # Remove duplicates
        low_tf_df = low_tf_df[~low_tf_df.index.duplicated(keep='first')]
        high_tf_df = high_tf_df[~high_tf_df.index.duplicated(keep='first')]
        
        # Forward fill high_tf data to align with low_tf timestamps
        aligned_high_tf = high_tf_df.reindex(low_tf_df.index, method='ffill')
        
        # Ensure no forward fill beyond the original high_tf range
        # (no future data beyond the last available)
        last_valid_idx = high_tf_df.index[-1] if len(high_tf_df) > 0 else low_tf_df.index[0]
        mask = aligned_high_tf.index > last_valid_idx
        aligned_high_tf.loc[mask] = np.nan
        
        return aligned_high_tf

    def prevent_lookahead_bias(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Shift data by 1 period to prevent lookahead bias
        This ensures that indicators calculated at time T
        are not used for decisions until time T+1
        """
        if df.empty:
            return df
            
        # Shift all data (except timestamp index) by 1 period back
        df_shifted = df.shift(1)
        
        # The first row will have NaN values after shifting
        # This prevents using future information for past decisions
        return df_shifted

    def align_multitimeframe_data(self, 
                                  timeframe_data: Dict[str, pd.DataFrame],
                                  reference_timeframe: str) -> Dict[str, pd.DataFrame]:
        """
        Align multiple timeframes to a reference timeframe
        All higher timeframes are forward-filled to match the reference timeframe
        """
        if reference_timeframe not in timeframe_data:
            raise ValueError(f"Reference timeframe {reference_timeframe} not found in data")
        
        aligned_data = {}
        reference_df = timeframe_data[reference_timeframe]
        
        for timeframe, df in timeframe_data.items():
            if timeframe == reference_timeframe:
                # Apply lookahead prevention to the reference timeframe
                aligned_data[timeframe] = self.prevent_lookahead_bias(reference_df)
            elif self._is_higher_timeframe(timeframe, reference_timeframe):
                # Higher timeframe data needs to be forward-filled to lower timeframe
                aligned_high_tf = self.forward_fill_align(reference_df, df)
                # Then apply lookahead prevention
                aligned_data[timeframe] = self.prevent_lookahead_bias(aligned_high_tf)
            else:
                # Lower timeframe data is used as is (with lookahead prevention)
                aligned_data[timeframe] = self.prevent_lookahead_bias(df)
        
        return aligned_data

    def _is_higher_timeframe(self, tf1: str, tf2: str) -> bool:
        """
        Determine if tf1 represents a higher timeframe than tf2
        """
        # Define timeframe multipliers in minutes
        timeframe_multipliers = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '2h': 120,
            '4h': 240,
            '6h': 360,
            '12h': 720,
            '1d': 1440,
            '1w': 10080,
            '1M': 43200  # Approximate month
        }
        
        tf1_minutes = self._parse_timeframe_to_minutes(tf1)
        tf2_minutes = self._parse_timeframe_to_minutes(tf2)
        
        return tf1_minutes > tf2_minutes

    def _parse_timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe string to minutes
        """
        try:
            # Handle common formats like '1h', '4h', '1d', etc.
            number = int(''.join(filter(str.isdigit, timeframe)))
            unit = ''.join(filter(str.isalpha, timeframe)).lower()
            
            if unit == 'm':
                return number
            elif unit == 'h':
                return number * 60
            elif unit == 'd':
                return number * 24 * 60
            elif unit == 'w':
                return number * 7 * 24 * 60
            else:
                # Default to minutes if format is not recognized
                return number
        except:
            # If parsing fails, default to a safe value
            return 60  # 1 hour default


class DataPipeline:
    """
    Enhanced Data Pipeline with Multi-Timeframe Support
    """
    def __init__(self):
        self.data_store: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.sync_engine = MultiTimeframeSynchronizer()
        self.feature_store: Dict[str, Dict[str, pd.DataFrame]] = {}

    def load_data(self, symbol: str, timeframe: str, df: pd.DataFrame):
        """
        Load raw market data for a symbol and timeframe
        """
        if symbol not in self.data_store:
            self.data_store[symbol] = {}
        
        # Sort data and ensure no duplicates
        df = df.sort_index().drop_duplicates()
        self.data_store[symbol][timeframe] = df

    def align_timeframes(self, symbol: str, target_timeframe: str) -> Dict[str, pd.DataFrame]:
        """
        Align all available timeframes for a symbol to the target timeframe
        """
        if symbol not in self.data_store:
            raise ValueError(f"Symbol {symbol} not found in data store")
        
        all_timeframes = self.data_store[symbol]
        if target_timeframe not in all_timeframes:
            raise ValueError(f"Target timeframe {target_timeframe} not available for symbol {symbol}")
        
        # Align all timeframes to the target timeframe
        aligned_data = self.sync_engine.align_multitimeframe_data(all_timeframes, target_timeframe)
        return aligned_data

    def apply_feature_engineering(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply basic feature engineering to the data
        """
        if df.empty:
            return df

        df_features = df.copy()
        
        # Add basic technical indicators as features
        # Moving averages
        df_features['ma_5'] = df_features['close'].rolling(window=5).mean()
        df_features['ma_20'] = df_features['close'].rolling(window=20).mean()
        
        # Volatility (ATR approximation)
        df_features['high_low_diff'] = df_features['high'] - df_features['low']
        df_features['volatility'] = df_features['high_low_diff'].rolling(window=14).mean()
        
        # Price change
        df_features['price_change'] = df_features['close'].pct_change()
        
        # High/Low relative position
        df_features['hl_position'] = (df_features['close'] - df_features['low']) / (df_features['high'] - df_features['low'] + 1e-8)
        
        return df_features

    def get_aligned_features(self, symbol: str, target_timeframe: str) -> pd.DataFrame:
        """
        Get aligned data with features for the target timeframe
        """
        aligned_data = self.align_timeframes(symbol, target_timeframe)
        
        # Apply feature engineering to the target timeframe
        target_df = aligned_data[target_timeframe]
        features_df = self.apply_feature_engineering(target_df)
        
        # Store features
        if symbol not in self.feature_store:
            self.feature_store[symbol] = {}
        self.feature_store[symbol][target_timeframe] = features_df
        
        return features_df

    def get_data_for_analysis(self, symbol: str, timeframes: list) -> Dict[str, pd.DataFrame]:
        """
        Get properly aligned data across multiple timeframes for analysis
        """
        result = {}
        for timeframe in timeframes:
            if symbol in self.data_store and timeframe in self.data_store[symbol]:
                df = self.data_store[symbol][timeframe]
                # Apply lookahead prevention
                df_aligned = self.sync_engine.prevent_lookahead_bias(df)
                result[timeframe] = df_aligned
        
        return result