"""
Data Integrity Checker - Validates market data quality before backtesting
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List
import logging


class DataIntegrityChecker:
    """Validates data quality before allowing backtesting to proceed."""
    
    def __init__(self):
        self.logger = logging.getLogger("DataIntegrityChecker")
    
    def calculate_missing_candle_ratio(self, df: pd.DataFrame, start_time: datetime, end_time: datetime, 
                                     timeframe: str = "1d") -> float:
        """
        Calculate the ratio of missing candles in the dataset.
        
        Args:
            df: DataFrame with timestamp column
            start_time: Expected start time
            end_time: Expected end time
            timeframe: Expected timeframe (e.g., '1d', '1h', '1m')
            
        Returns:
            Ratio of missing candles (0.0 to 1.0)
        """
        if df.empty:
            return 1.0  # 100% missing if no data
        
        # Convert timestamp to datetime if it exists as column
        if 'timestamp' in df.columns:
            timestamps = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        else:
            # Assume index is datetime
            timestamps = pd.to_datetime(df.index, utc=True)
        
        # Calculate expected count based on timeframe
        if timeframe == '1d':
            interval_days = 1
            expected_count = int((end_time - start_time).days / interval_days) + 1
        elif timeframe == '1h':
            interval_hours = 1
            expected_count = int((end_time - start_time).total_seconds() / 3600) + 1
        elif timeframe == '1m':
            interval_minutes = 1
            expected_count = int((end_time - start_time).total_seconds() / 60) + 1
        else:
            # Default to daily if unrecognized
            expected_count = (end_time - start_time).days + 1
        
        actual_count = len(timestamps)
        
        # Calculate missing ratio
        if expected_count > 0:
            missing_ratio = 1 - (actual_count / expected_count)
            # Ensure ratio is between 0 and 1
            missing_ratio = max(0.0, min(1.0, missing_ratio))
        else:
            missing_ratio = 1.0  # If no expected count, assume all missing
            
        return missing_ratio
    
    def validate_symbol_data(self, df: pd.DataFrame, symbol: str, start_time: datetime, 
                           end_time: datetime, timeframe: str = "1d", max_missing_ratio: float = 0.05) -> bool:
        """
        Validate data quality for a specific symbol.
        
        Args:
            df: DataFrame with the symbol's data
            symbol: Trading symbol
            start_time: Expected start time
            end_time: Expected end time
            timeframe: Expected timeframe
            max_missing_ratio: Maximum allowed missing ratio (default 5%)
            
        Returns:
            True if data quality is acceptable, False otherwise
        """
        if df.empty:
            self.logger.error(f"No data available for {symbol}")
            return False
        
        missing_ratio = self.calculate_missing_candle_ratio(df, start_time, end_time, timeframe)
        
        if missing_ratio > max_missing_ratio:
            self.logger.error(
                f"Data quality validation failed for {symbol}: "
                f"{missing_ratio:.2%} missing data exceeds {max_missing_ratio:.2%} threshold. "
                f"Date range: {start_time.date()} to {end_time.date()}"
            )
            return False
        
        self.logger.info(
            f"Data quality validation passed for {symbol}: "
            f"{missing_ratio:.2%} missing data is below {max_missing_ratio:.2%} threshold"
        )
        return True
    
    def validate_multiple_symbols(self, data_dict: Dict[str, pd.DataFrame], symbols: List[str],
                                start_time: datetime, end_time: datetime, timeframe: str = "1d",
                                max_missing_ratio: float = 0.05) -> Dict[str, bool]:
        """
        Validate data quality for multiple symbols.
        
        Args:
            data_dict: Dictionary mapping symbol to DataFrame
            symbols: List of symbols to validate
            start_time: Expected start time
            end_time: Expected end time
            timeframe: Expected timeframe
            max_missing_ratio: Maximum allowed missing ratio
            
        Returns:
            Dictionary mapping symbol to validation result
        """
        results = {}
        for symbol in symbols:
            if symbol not in data_dict:
                self.logger.error(f"Symbol {symbol} not found in data dictionary")
                results[symbol] = False
                continue
                
            df = data_dict[symbol]
            results[symbol] = self.validate_symbol_data(df, symbol, start_time, end_time, 
                                                     timeframe, max_missing_ratio)
        
        return results
    
    def generate_integrity_report(self, data_dict: Dict[str, pd.DataFrame], symbols: List[str],
                                start_time: datetime, end_time: datetime, timeframe: str = "1d") -> Dict:
        """
        Generate a comprehensive data integrity report.
        
        Args:
            data_dict: Dictionary mapping symbol to DataFrame
            symbols: List of symbols to report on
            start_time: Expected start time
            end_time: Expected end time
            timeframe: Expected timeframe
            
        Returns:
            Dictionary with integrity report
        """
        report = {
            'validation_timestamp': datetime.now().isoformat(),
            'date_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'timeframe': timeframe,
            'symbols': {}
        }
        
        for symbol in symbols:
            if symbol not in data_dict:
                report['symbols'][symbol] = {
                    'status': 'MISSING',
                    'missing_ratio': 1.0,
                    'message': f'Symbol {symbol} not found in data'
                }
                continue
            
            df = data_dict[symbol]
            if df.empty:
                report['symbols'][symbol] = {
                    'status': 'EMPTY',
                    'missing_ratio': 1.0,
                    'message': f'No data available for {symbol}'
                }
                continue
            
            missing_ratio = self.calculate_missing_candle_ratio(df, start_time, end_time, timeframe)
            
            status = 'PASS' if missing_ratio <= 0.05 else 'FAIL'
            message = f'Missing ratio: {missing_ratio:.2%} ({status})'
            
            report['symbols'][symbol] = {
                'status': status,
                'missing_ratio': missing_ratio,
                'message': message,
                'total_rows': len(df),
                'date_range': {
                    'data_start': df['timestamp'].min() if 'timestamp' in df.columns else str(df.index.min()),
                    'data_end': df['timestamp'].max() if 'timestamp' in df.columns else str(df.index.max())
                }
            }
        
        return report