"""Sliding window splitter for Walk-Forward Optimization with proper train/test splitting."""

from typing import Dict, List, Tuple, Generator
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np


@dataclass
class WalkForwardWindow:
    """Represents a single walk-forward window with training and testing periods."""
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    train_data: pd.DataFrame
    test_data: pd.DataFrame
    window_number: int


class SlidingWindowSplitter:
    """
    Sliding Window Splitter for Walk-Forward Optimization.
    
    This class creates training and testing windows following the real WFO methodology:
    - Training Window: 90 steps (e.g., 3 months)
    - Testing Window: 30 steps (e.g., 1 month)  
    - Sliding Step: 30 steps (1 month)
    
    Example iteration:
    Iteration 1: Train Jan->Mar, Test Apr
    Iteration 2: Train Feb->Apr, Test May
    Iteration 3: Train Mar->May, Test Jun
    """
    
    def __init__(self, 
                 train_size: int = 90, 
                 test_size: int = 30, 
                 step: int = 30,
                 min_train_size: int = 30,
                 min_test_size: int = 10):
        """
        Initialize the sliding window splitter.
        
        Args:
            train_size: Number of data points for training window
            test_size: Number of data points for testing window
            step: Number of data points to slide forward for each iteration
            min_train_size: Minimum required training size
            min_test_size: Minimum required testing size
        """
        self.train_size = train_size
        self.test_size = test_size
        self.step = step
        self.min_train_size = min_train_size
        self.min_test_size = min_test_size
        
    def split(self, 
              df: pd.DataFrame, 
              date_col: str = 'timestamp') -> List[WalkForwardWindow]:
        """
        Split the DataFrame into walk-forward windows.
        
        Args:
            df: DataFrame with datetime index or timestamp column
            date_col: Name of the date column if using regular index
            
        Returns:
            List of WalkForwardWindow objects containing train/test splits
        """
        if df.empty:
            return []
            
        # Ensure proper datetime index
        if date_col in df.columns:
            df = df.set_index(date_col)
        
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        df = df.sort_index()
        data_points = len(df)
        
        if data_points < (self.train_size + self.test_size):
            raise ValueError(
                f"Insufficient data. Need at least {self.train_size + self.test_size} points, "
                f"but only have {data_points} points."
            )
        
        windows = []
        current_start_idx = 0
        window_num = 0
        
        while True:
            # Define training window boundaries
            train_end_idx = current_start_idx + self.train_size
            
            # Define testing window boundaries
            test_start_idx = train_end_idx
            test_end_idx = test_start_idx + self.test_size
            
            # Check if we have enough data for this window
            if test_end_idx > data_points:
                break
            
            # Extract training and testing data
            train_data = df.iloc[current_start_idx:train_end_idx]
            test_data = df.iloc[test_start_idx:test_end_idx]
            
            # Validate minimum sizes
            if len(train_data) < self.min_train_size:
                break
            if len(test_data) < self.min_test_size:
                break
            
            # Create window object
            window = WalkForwardWindow(
                train_start=train_data.index[0],
                train_end=train_data.index[-1],
                test_start=test_data.index[0], 
                test_end=test_data.index[-1],
                train_data=train_data.copy(),
                test_data=test_data.copy(),
                window_number=window_num
            )
            
            windows.append(window)
            
            # Move to next window
            current_start_idx += self.step
            window_num += 1
            
            # Prevent infinite loop if step is 0 or too small
            if self.step <= 0 or current_start_idx >= data_points:
                break
        
        return windows
    
    def split_with_overlap(self,
                          df: pd.DataFrame,
                          train_size: int = None,
                          test_size: int = None,
                          overlap_ratio: float = 0.0) -> List[WalkForwardWindow]:
        """
        Split with configurable overlap between consecutive windows.
        
        Args:
            df: DataFrame with datetime index
            train_size: Optional override for training size
            test_size: Optional override for testing size
            overlap_ratio: Ratio of overlap (0.0 = no overlap, 1.0 = full overlap)
            
        Returns:
            List of WalkForwardWindow objects
        """
        if train_size is None:
            train_size = self.train_size
        if test_size is None:
            test_size = self.test_size
            
        if df.empty or not isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()
        
        data_points = len(df)
        windows = []
        current_start_idx = 0
        window_num = 0
        
        while True:
            # Calculate overlap
            overlap_points = int(train_size * overlap_ratio)
            step_size = max(1, train_size - overlap_points)
            
            # Define training window boundaries
            train_end_idx = current_start_idx + train_size
            test_start_idx = train_end_idx
            test_end_idx = test_start_idx + test_size
            
            # Check boundaries
            if test_end_idx > data_points:
                break
            
            # Extract data
            train_data = df.iloc[current_start_idx:train_end_idx]
            test_data = df.iloc[test_start_idx:test_end_idx]
            
            # Validate sizes
            if len(train_data) < self.min_train_size or len(test_data) < self.min_test_size:
                break
                
            window = WalkForwardWindow(
                train_start=train_data.index[0],
                train_end=train_data.index[-1],
                test_start=test_data.index[0],
                test_end=test_data.index[-1],
                train_data=train_data.copy(),
                test_data=test_data.copy(),
                window_number=window_num
            )
            
            windows.append(window)
            
            # Move to next window
            current_start_idx += step_size
            window_num += 1
            
            if current_start_idx >= data_points:
                break
        
        return windows
    
    def validate_split(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate if the DataFrame has sufficient data for walk-forward splitting.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dict with validation results
        """
        if df.empty or not isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()
        
        data_points = len(df)
        
        required_points = self.train_size + self.test_size
        
        return {
            'has_sufficient_data': data_points >= required_points,
            'total_data_points': data_points,
            'required_points': required_points,
            'estimated_windows': max(0, (data_points - self.train_size - self.test_size) // self.step + 1) if self.step > 0 else 0,
            'min_train_size_met': data_points >= self.min_train_size,
            'min_test_size_met': data_points >= self.min_test_size
        }


class ExpandingWindowSplitter:
    """
    Expanding Window Splitter for Walk-Forward Optimization.
    
    Unlike sliding window where both training and testing windows move,
    in expanding window the training window keeps growing while testing window moves.
    """
    
    def __init__(self, 
                 initial_train_size: int = 90, 
                 test_size: int = 30, 
                 step: int = 30,
                 min_train_size: int = 30,
                 min_test_size: int = 10):
        """
        Initialize the expanding window splitter.
        
        Args:
            initial_train_size: Initial size of training window
            test_size: Size of testing window
            step: Step size for expanding training window
            min_train_size: Minimum required training size
            min_test_size: Minimum required testing size
        """
        self.initial_train_size = initial_train_size
        self.test_size = test_size
        self.step = step
        self.min_train_size = min_train_size
        self.min_test_size = min_test_size
    
    def split(self, 
              df: pd.DataFrame, 
              date_col: str = 'timestamp') -> List[WalkForwardWindow]:
        """
        Split the DataFrame into expanding walk-forward windows.
        
        Args:
            df: DataFrame with datetime index or timestamp column
            date_col: Name of the date column if using regular index
            
        Returns:
            List of WalkForwardWindow objects containing train/test splits
        """
        if df.empty:
            return []
            
        # Ensure proper datetime index
        if date_col in df.columns:
            df = df.set_index(date_col)
        
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame index must be DatetimeIndex")
        
        df = df.sort_index()
        data_points = len(df)
        
        if data_points < (self.initial_train_size + self.test_size):
            raise ValueError(
                f"Insufficient data. Need at least {self.initial_train_size + self.test_size} points, "
                f"but only have {data_points} points."
            )
        
        windows = []
        current_train_end_idx = self.initial_train_size
        window_num = 0
        
        while True:
            # Define training window (expanding from start to current_train_end_idx)
            train_data = df.iloc[:current_train_end_idx]
            
            # Define testing window boundaries
            test_start_idx = current_train_end_idx
            test_end_idx = test_start_idx + self.test_size
            
            # Check if we have enough data for testing
            if test_end_idx > data_points:
                break
            
            # Extract testing data
            test_data = df.iloc[test_start_idx:test_end_idx]
            
            # Validate minimum sizes
            if len(train_data) < self.min_train_size:
                break
            if len(test_data) < self.min_test_size:
                break
            
            # Create window object
            window = WalkForwardWindow(
                train_start=train_data.index[0],
                train_end=train_data.index[-1],
                test_start=test_data.index[0], 
                test_end=test_data.index[-1],
                train_data=train_data.copy(),
                test_data=test_data.copy(),
                window_number=window_num
            )
            
            windows.append(window)
            
            # Expand training window
            current_train_end_idx += self.step
            window_num += 1
            
            # Prevent infinite loop
            if self.step <= 0 or current_train_end_idx >= data_points:
                break
        
        return windows


def demonstrate_splitter_usage():
    """Demonstrate the usage of sliding and expanding window splitters."""
    # Create sample data
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.random(len(dates)) * 100,
        'high': np.random.random(len(dates)) * 100,
        'low': np.random.random(len(dates)) * 100,
        'close': np.random.random(len(dates)) * 100,
        'volume': np.random.random(len(dates)) * 1000
    }).set_index('timestamp')
    
    print("Sample data shape:", sample_data.shape)
    
    # Test sliding window splitter
    sliding_splitter = SlidingWindowSplitter(train_size=60, test_size=20, step=10)
    sliding_windows = sliding_splitter.split(sample_data)
    
    print(f"\nSliding Window Splitter Results:")
    print(f"Generated {len(sliding_windows)} windows")
    
    for i, window in enumerate(sliding_windows[:3]):  # Show first 3 windows
        print(f"Window {i+1}:")
        print(f"  Train: {window.train_start.date()} to {window.train_end.date()} ({len(window.train_data)} points)")
        print(f"  Test:  {window.test_start.date()} to {window.test_end.date()} ({len(window.test_data)} points)")
    
    # Test expanding window splitter
    expanding_splitter = ExpandingWindowSplitter(initial_train_size=60, test_size=20, step=10)
    expanding_windows = expanding_splitter.split(sample_data)
    
    print(f"\nExpanding Window Splitter Results:")
    print(f"Generated {len(expanding_windows)} windows")
    
    for i, window in enumerate(expanding_windows[:3]):  # Show first 3 windows
        print(f"Window {i+1}:")
        print(f"  Train: {window.train_start.date()} to {window.train_end.date()} ({len(window.train_data)} points)")
        print(f"  Test:  {window.test_start.date()} to {window.test_end.date()} ({len(window.test_data)} points)")


if __name__ == "__main__":
    demonstrate_splitter_usage()