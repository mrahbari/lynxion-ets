"""
Data Integrity Report Module - Institutional-grade market data validation
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path


class DataIntegrityReport:
    """Generates institutional-grade data integrity reports for market data validation."""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger("DataIntegrityReport")
        
    def calculate_missing_candle_stats(self, df: pd.DataFrame, start_time: datetime, end_time: datetime, 
                                     timeframe: str = "1d") -> Dict[str, float]:
        """
        Calculate missing candle statistics for a given dataset.
        
        Args:
            df: DataFrame with timestamp column
            start_time: Start time of expected data range
            end_time: End time of expected data range
            timeframe: Expected timeframe (e.g., '1d', '1h', '1m')
            
        Returns:
            Dictionary with missing candle statistics
        """
        if df.empty:
            return {
                'expected_count': 0,
                'actual_count': 0,
                'missing_count': 0,
                'missing_ratio': 1.0,
                'gap_percentage': 100.0,
                'longest_gap_minutes': (end_time - start_time).total_seconds() / 60 if start_time and end_time else 0
            }
        
        # Convert timestamp to datetime if it's not already
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
            timestamps = df['timestamp'].sort_values()
        else:
            # If no timestamp column, assume index is datetime
            timestamps = pd.to_datetime(df.index).sort_values()
        
        # Calculate expected count based on timeframe
        if timeframe == '1d':
            interval_minutes = 24 * 60
        elif timeframe == '1h':
            interval_minutes = 60
        elif timeframe == '1m':
            interval_minutes = 1
        else:
            # For other timeframes, try to estimate from the data
            if len(timestamps) > 1:
                avg_interval = (timestamps.iloc[1:] - timestamps.iloc[:-1]).mean()
                interval_minutes = avg_interval.total_seconds() / 60
            else:
                interval_minutes = 24 * 60  # Default to daily
        
        # Calculate expected number of candles
        duration_minutes = (end_time - start_time).total_seconds() / 60
        expected_count = max(1, int(duration_minutes / interval_minutes))
        
        actual_count = len(timestamps)
        missing_count = expected_count - actual_count
        missing_ratio = max(0, missing_count / expected_count) if expected_count > 0 else 0
        gap_percentage = missing_ratio * 100
        
        # Calculate longest gap
        if len(timestamps) > 1:
            gaps = timestamps.iloc[1:] - timestamps.iloc[:-1]
            longest_gap_minutes = gaps.max().total_seconds() / 60
        else:
            longest_gap_minutes = duration_minutes if duration_minutes > 0 else 0
        
        return {
            'expected_count': expected_count,
            'actual_count': actual_count,
            'missing_count': missing_count,
            'missing_ratio': missing_ratio,
            'gap_percentage': gap_percentage,
            'longest_gap_minutes': longest_gap_minutes
        }
    
    def generate_symbol_report(self, symbol: str, timeframe: str = "1d", 
                             start_date: Optional[datetime] = None, 
                             end_date: Optional[datetime] = None) -> Dict:
        """
        Generate a data integrity report for a specific symbol and timeframe.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1d', '1h', '1m')
            start_date: Start date for the report (optional)
            end_date: End date for the report (optional)
            
        Returns:
            Dictionary with integrity report
        """
        # Try to load data from both raw and processed directories
        formatted_symbol = symbol.replace('USDT', '-USDT') if 'USDT' in symbol else symbol
        
        # Check both possible locations
        raw_path = self.base_path / "history" / "raw" / timeframe / f"{formatted_symbol}.csv"
        processed_path = self.base_path / "history" / "processed" / timeframe / f"{formatted_symbol}.csv"
        
        data_path = None
        if raw_path.exists():
            data_path = raw_path
        elif processed_path.exists():
            data_path = processed_path
        
        if not data_path:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'FILE_NOT_FOUND',
                'error': f'Data file not found for {symbol} in {timeframe}',
                'stats': {}
            }
        
        try:
            df = pd.read_csv(data_path)
            
            # Determine date range if not provided
            if start_date is None or end_date is None:
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                    if start_date is None:
                        start_date = df['timestamp'].min()
                    if end_date is None:
                        end_date = df['timestamp'].max()
                else:
                    # If no timestamp column, use the index
                    if start_date is None:
                        start_date = pd.to_datetime(df.index.min())
                    if end_date is None:
                        start_date = pd.to_datetime(df.index.max())
            
            stats = self.calculate_missing_candle_stats(df, start_date, end_date, timeframe)
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'SUCCESS',
                'file_path': str(data_path),
                'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'stats': stats
            }
            
        except Exception as e:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'ERROR_LOADING',
                'error': str(e),
                'stats': {}
            }
    
    def generate_multi_symbol_report(self, symbols: List[str], timeframe: str = "1d",
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Generate data integrity reports for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            timeframe: Timeframe for all symbols
            start_date: Start date for all reports (optional)
            end_date: End date for all reports (optional)
            
        Returns:
            List of integrity reports for each symbol
        """
        reports = []
        for symbol in symbols:
            report = self.generate_symbol_report(symbol, timeframe, start_date, end_date)
            reports.append(report)
        return reports
    
    def validate_data_quality(self, reports: List[Dict], max_missing_ratio: float = 0.05) -> Tuple[bool, List[str]]:
        """
        Validate if data quality meets institutional standards.
        
        Args:
            reports: List of data integrity reports
            max_missing_ratio: Maximum allowed missing ratio (default 5%)
            
        Returns:
            Tuple of (is_valid, list_of_problematic_symbols)
        """
        invalid_symbols = []
        
        for report in reports:
            if report['status'] != 'SUCCESS':
                invalid_symbols.append(f"{report['symbol']}: {report['status']}")
                continue
                
            missing_ratio = report['stats'].get('missing_ratio', 1.0)
            if missing_ratio > max_missing_ratio:
                gap_pct = report['stats'].get('gap_percentage', 0)
                invalid_symbols.append(
                    f"{report['symbol']}: {gap_pct:.2f}% missing data (threshold: {max_missing_ratio*100:.2f}%)"
                )
        
        is_valid = len(invalid_symbols) == 0
        return is_valid, invalid_symbols