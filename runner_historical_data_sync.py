#!/usr/bin/env python3
"""
Historical Data Sync Job - Downloads historical data for approved symbols
This script runs as a scheduled job to ensure historical data availability
"""

import os
import sys
import time
import schedule
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
import pandas as pd

from application.configs.configs import Configs

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain.value_objects import Symbol
from infrastructure.data.configurable_historical_data_provider import ConfigurableHistoricalDataProvider
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from application.symbol_management.centralized_symbol_manager import get_unified_symbols, get_approved_symbols, symbol_manager


class HistoricalDataSyncJob:
    """Scheduled job to sync historical data for approved symbols"""

    def __init__(self, data_dir: str = None):
        # Use the environment variable for the data path if available
        if data_dir is None:
            data_dir = Configs.data.csv_data_path if Configs.data and Configs.data.csv_data_path else './data/history/raw/1m'

        self.data_dir = data_dir
        # Extract the base path from the full path (e.g., from ./data/history/raw/1m to ./data)
        # We need to go up 3 levels: 1m -> raw -> history -> data
        path_parts = data_dir.rstrip('/').split('/')
        if len(path_parts) >= 4:
            base_path = '/'.join(path_parts[:-3])  # Go up 3 levels to get to base data dir
        else:
            base_path = './data'  # Default fallback

        # Initialize the data provider with fallback options
        fallback_sources_raw = Configs.data.historical_data_fallback_sources if Configs.data and Configs.data.historical_data_fallback_sources else 'binance,mexc,phemex'
        if isinstance(fallback_sources_raw, list):
            fallback_sources = fallback_sources_raw
        else:
            fallback_sources = fallback_sources_raw.split(',')

        self.data_provider = ConfigurableHistoricalDataProvider(
            preferred_data_source=Configs.data.preferred_historical_data_source if Configs.data and Configs.data.preferred_historical_data_source else 'binance',
            fallback_sources=fallback_sources
        )
        self.csv_loader = CSVHistoryLoaderAdapter(base_path=base_path)
        self.logger = self._setup_logger()

        # Create data directory structure if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(os.path.join(base_path, "history", "raw", "1m"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "history", "raw", "5m"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "history", "raw", "15m"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "history", "raw", "30m"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "history", "raw", "1h"), exist_ok=True)

        # Ensure the data directory structure is properly set up
        self.logger.info(f"Data directory structure created at: {self.data_dir}")

    def _setup_logger(self):
        """Setup logging for the sync job"""
        logger = logging.getLogger("HistoricalDataSync")
        logger.setLevel(logging.INFO)

        # Create file handler
        fh = logging.FileHandler(f"{self.data_dir}/sync_job.log")
        fh.setLevel(logging.INFO)

        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger
    
    def sync_approved_symbols(self):
        """Download historical data for all approved symbols"""
        self.logger.info("Starting historical data sync for approved symbols")

        try:
            # Get all approved symbols from the centralized symbol manager
            # Use all approved symbols instead of just unified symbols to sync all approved symbols
            approved_symbols = list(get_approved_symbols())  # Convert set to list
            self.logger.info(f"Found {len(approved_symbols)} approved symbols to sync")

            successful_syncs = 0
            failed_syncs = 0

            for symbol_str in approved_symbols:
                # Use the new retry logic for each symbol
                if self.sync_with_retry(symbol_str):
                    successful_syncs += 1
                else:
                    # Even if sync failed, check if we have valid cached data
                    if self.validate_data_quality(symbol_str, '1m'):
                        self.logger.info(f"Using existing valid data for {symbol_str} as fallback")
                        successful_syncs += 1
                    else:
                        failed_syncs += 1
                        self.logger.error(f"Failed to sync {symbol_str} after all retry attempts and no valid cached data available")

            self.logger.info(f"Historical data sync completed: {successful_syncs} successful, {failed_syncs} failed")

        except Exception as e:
            self.logger.error(f"Critical error in historical data sync: {e}")
            # Re-raise the exception to ensure the calling process knows about the failure
            raise
    
    def validate_data_quality(self, symbol: str, timeframe: str = '1m') -> bool:
        """Validate the quality of downloaded data"""
        try:
            # Load the data
            df = self.csv_loader.load_symbol_data(symbol, timeframe)

            if df.empty:
                self.logger.warning(f"No data found for {symbol} {timeframe}")
                return False

            # Check for minimum data points
            if len(df) < 10:
                self.logger.warning(f"Insufficient data points for {symbol} {timeframe}: {len(df)}")
                return False

            # Check for required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                self.logger.warning(f"Missing columns for {symbol} {timeframe}: {missing_cols}")
                return False

            # Check for reasonable price relationships
            invalid_rows = df[(df['high'] < df['low']) |
                             (df['high'] < df['close']) |
                             (df['low'] > df['close'])]

            if len(invalid_rows) > 0:
                self.logger.warning(f"Invalid OHLC relationships found for {symbol} {timeframe}: {len(invalid_rows)} rows")
                return False

            # Check for zero/negative prices
            zero_prices = df[(df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)]
            if len(zero_prices) > 0:
                self.logger.warning(f"Zero/negative prices found for {symbol} {timeframe}: {len(zero_prices)} rows")
                return False

            # Check for reasonable volume (should not be negative)
            negative_volume = df[df['volume'] < 0]
            if len(negative_volume) > 0:
                self.logger.warning(f"Negative volume found for {symbol} {timeframe}: {len(negative_volume)} rows")
                return False

            # Check timestamp format - ensure they are Unix timestamps (integers)
            if 'timestamp' in df.index.names or 'timestamp' in df.columns:
                # If timestamp is in the index
                if 'timestamp' in df.index.names:
                    timestamp_series = df.index.to_series()
                else:
                    timestamp_series = df['timestamp']

                # Check if timestamps look like Unix timestamps (after year 2000)
                sample_timestamp = timestamp_series.iloc[0] if len(timestamp_series) > 0 else None
                if sample_timestamp is not None:
                    try:
                        int_timestamp = int(float(sample_timestamp))
                        # Verify it looks like a Unix timestamp (after year 2000)
                        if int_timestamp < 946684800:  # Jan 1, 2000 timestamp
                            self.logger.warning(f"Timestamp format may be incorrect for {symbol} {timeframe} - values seem too small to be Unix timestamps")
                            return False
                    except (ValueError, TypeError):
                        self.logger.warning(f"Timestamp format error for {symbol} {timeframe} - cannot convert to integer")
                        return False

            # Check for data freshness (ensure we have recent data)
            if not df.empty:
                latest_timestamp = df.index.max()
                # Handle timezone-aware and naive timestamps
                if latest_timestamp.tz is not None:
                    current_time = pd.Timestamp.now(tz=latest_timestamp.tz)
                else:
                    current_time = pd.Timestamp.now().tz_localize(None)

                time_diff = (current_time - latest_timestamp).total_seconds() / 3600  # hours
                if time_diff > 24:  # More than 24 hours old
                    self.logger.warning(f"Data for {symbol} {timeframe} is {time_diff:.2f} hours old")

            self.logger.info(f"Data quality validation passed for {symbol} {timeframe}")
            return True

        except FileNotFoundError:
            self.logger.warning(f"Data file not found for {symbol} {timeframe}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating data for {symbol} {timeframe}: {e}")
            return False

    def sync_with_retry(self, symbol_str: str, max_retries: int = 3) -> bool:
        """
        Sync a single symbol with retry logic

        Args:
            symbol_str: Trading symbol to sync
            max_retries: Maximum number of retry attempts

        Returns:
            True if sync was successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Syncing data for {symbol_str} (attempt {attempt + 1}/{max_retries})")

                # Create Symbol object for the data provider
                symbol = Symbol(symbol_str)

                # Fetch latest 24h of 1m data for each symbol
                historical_data = self.data_provider.get_historical_data(
                    symbol=symbol,
                    period='30d',
                    timeframe='1m'
                )

                if historical_data and len(historical_data) > 0:
                    # Save only 1-minute data to local cache (as specified in requirements)
                    self.csv_loader.save_historical_data(
                        symbol=symbol_str,
                        data=historical_data,
                        timeframe='1m'
                    )

                    self.logger.info(f"Successfully synced 1-minute data for {symbol_str}")
                    return True
                else:
                    self.logger.warning(f"No data retrieved for {symbol_str}")
                    # Check if we have valid existing data
                    if self.validate_data_quality(symbol_str, '1m'):
                        self.logger.info(f"Valid existing data found for {symbol_str}")
                        return True
                    return False

            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed for {symbol_str}: {e}")
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue

        # If all retries failed, check if we have valid existing data as a final fallback
        if self.validate_data_quality(symbol_str, '1m'):
            self.logger.info(f"Using valid existing data for {symbol_str} as fallback after retries")
            return True
        return False
    
    def cleanup_old_cache(self, days_to_keep: int = 7):
        """Clean up old cache files to save space"""
        import shutil
        from pathlib import Path
        
        self.logger.info(f"Cleaning up cache files older than {days_to_keep} days")
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        cleaned_count = 0
        
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if file.endswith('.csv'):
                    file_path = os.path.join(root, file)
                    if os.path.getctime(file_path) < cutoff_time:
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                            self.logger.info(f"Removed old cache file: {file_path}")
                        except Exception as e:
                            self.logger.error(f"Could not remove {file_path}: {e}")
        
        self.logger.info(f"Cache cleanup completed: removed {cleaned_count} old files")
    
    def start_scheduler(self):
        """Start the hourly sync scheduler"""
        self.logger.info("Starting historical data sync scheduler")
        
        # Schedule the sync job to run every hour
        schedule.every().hour.do(self.sync_approved_symbols)
        
        # Schedule cleanup to run daily
        schedule.every().day.at("02:00").do(self.cleanup_old_cache)
        
        # Run the first sync immediately
        self.logger.info("Running initial sync...")
        self.sync_approved_symbols()
        
        # Enter the scheduling loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


def main():
    """Main function to run the historical data sync job"""
    print("Starting Historical Data Sync Job...")
    
    # Create the sync job
    sync_job = HistoricalDataSyncJob()
    
    # If run with 'now' argument, run once and exit
    if len(sys.argv) > 1 and sys.argv[1] == 'now':
        print("Running one-time sync...")
        sync_job.sync_approved_symbols()
        print("One-time sync completed.")
        return
    
    # Otherwise, start the scheduler
    try:
        sync_job.start_scheduler()
    except KeyboardInterrupt:
        print("\nHistorical Data Sync Job stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error in Historical Data Sync Job: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()