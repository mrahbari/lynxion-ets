import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import os
from shared.logger import logger


class HistoricalDataLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
    def load_csv_data(self, symbol: str, timeframe: str = "1h") -> Optional[pd.DataFrame]:
        """Load historical data from CSV file"""
        filename = f"{self.data_dir}/{symbol.upper()}_{timeframe}.csv"
        
        if not os.path.exists(filename):
            logger.warning(f"Data file not found: {filename}")
            return None
            
        try:
            df = pd.read_csv(filename)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Loaded {len(df)} records for {symbol} from {filename}")
            return df
        except Exception as e:
            logger.error(f"Error loading data from {filename}: {e}")
            return None
            
    def save_csv_data(self, df: pd.DataFrame, symbol: str, timeframe: str = "1h") -> bool:
        """Save data to CSV file"""
        filename = f"{self.data_dir}/{symbol.upper()}_{timeframe}.csv"
        
        try:
            df.to_csv(filename)
            logger.info(f"Saved {len(df)} records for {symbol} to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {e}")
            return False
            
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features from historical data"""
        if df is None or df.empty:
            return df
            
        # Add technical indicators
        df = self.add_rsi(df, period=14)
        df = self.add_macd(df)
        df = self.add_bollinger_bands(df)
        df = self.add_stochastic(df)
        df = self.add_volume_indicators(df)
        
        # Add price change features
        df['price_change_pct'] = df['close'].pct_change()
        df['high_low_pct'] = (df['high'] - df['low']) / df['close']
        df['volume_change_pct'] = df['volume'].pct_change()
        
        # Add volatility
        df['volatility'] = df['close'].rolling(window=20).std()
        
        # Add momentum
        df['momentum'] = df['close'] - df['close'].shift(10)
        
        return df
        
    def add_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        return df
        
    def add_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Add MACD indicator"""
        exp1 = df['close'].ewm(span=fast).mean()
        exp2 = df['close'].ewm(span=slow).mean()
        df[f'macd_line'] = exp1 - exp2
        df[f'macd_signal'] = df[f'macd_line'].ewm(span=signal).mean()
        df[f'macd_histogram'] = df[f'macd_line'] - df[f'macd_signal']
        return df
        
    def add_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        """Add Bollinger Bands"""
        df[f'ma_{period}'] = df['close'].rolling(window=period).mean()
        rolling_std = df['close'].rolling(window=period).std()
        df[f'bb_upper'] = df[f'ma_{period}'] + (rolling_std * std_dev)
        df[f'bb_lower'] = df[f'ma_{period}'] - (rolling_std * std_dev)
        df[f'bb_width'] = df[f'bb_upper'] - df[f'bb_lower']
        df[f'bb_position'] = (df['close'] - df[f'bb_lower']) / df[f'bb_width']
        return df
        
    def add_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """Add Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        df[f'stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df[f'stoch_d'] = df[f'stoch_k'].rolling(window=d_period).mean()
        return df
        
    def add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based indicators"""
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        return df
        
    def get_train_test_split(self, df: pd.DataFrame, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Split data into train and test sets"""
        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()
        return train_df, test_df