"""
Infrastructure adapter for file operations in the sync system.
"""
import csv
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional
from application.configs.sync_settings import settings
from domain.ports.sync import FileRepository as DomainFileRepository
from application.data_sync.ports import FileRepository as AppFileRepository
import pandas as pd


class FileRepositoryAdapter(AppFileRepository, DomainFileRepository):
    """Infrastructure adapter implementing both application and domain file repository ports"""

    def __init__(self, base_data_dir: Optional[str] = None):
        """
        Initialize the file repository adapter

        Args:
            base_data_dir: Base directory for data files (defaults to settings.data_dir)
        """
        self.base_data_dir = base_data_dir or settings.data_dir
        # Use the existing project data directory structure
        if self.base_data_dir == "./data/history":
            self.base_data_dir = os.path.join(os.getcwd(), "data", "history")

        self.raw_dir = os.path.join(self.base_data_dir, "raw", "1m")
        self.processed_dir = os.path.join(self.base_data_dir, "processed")
        self.index_dir = os.path.join(self.base_data_dir, "index")
        self.reports_dir = os.path.join(os.path.dirname(self.base_data_dir), "reports")

        # Configuration attributes that were missing
        self.temp_file_suffix = ".tmp"
        self.raw_retention_days = getattr(settings, 'raw_retention_days', 365)  # Default to 1 year

        # Create directories if they don't exist
        for directory in [self.raw_dir, self.processed_dir, self.index_dir, self.reports_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def get_raw_file_path(self, symbol: str) -> str:
        """Get the path for a raw data file for a symbol"""
        # Normalize symbol format to ensure consistent file naming
        # Convert formats like BTC/USDT or BTCUSDT to BTC-USDT
        normalized_symbol = self._normalize_symbol_for_file(symbol)
        return os.path.join(self.raw_dir, f"{normalized_symbol}.csv")

    def _normalize_symbol_for_file(self, symbol: str) -> str:
        """Normalize symbol format for consistent file naming"""
        # If symbol contains '/', convert to '-' format (e.g. BTC/USDT -> BTC-USDT)
        if '/' in symbol:
            symbol = symbol.replace('/', '-')

        # If symbol is in BTCUSDT format but doesn't have separator, convert to BTC-USDT format
        # Only if it doesn't already have separator
        if not ('-' in symbol or '/' in symbol) and 'USDT' in symbol:
            # Format like BTCUSDT -> BTC-USDT
            base_part = symbol.replace('USDT', '')
            symbol = f"{base_part}-USDT"
        elif not ('-' in symbol or '/' in symbol) and 'USD' in symbol and len(symbol) > 6:
            # Handle other USD formats
            if symbol.endswith('USD'):
                base_part = symbol.replace('USD', '')
                symbol = f"{base_part}-USD"

        return symbol
    
    def get_index_file_path(self, symbol: str) -> str:
        """Get the path for an index file for a symbol"""
        normalized_symbol = self._normalize_symbol_for_file(symbol)
        return os.path.join(self.index_dir, f"{normalized_symbol}.idx.json")

    def get_processed_file_path(self, symbol: str, timeframe: str) -> str:
        """Get the path for a processed data file for a symbol and timeframe"""
        normalized_symbol = self._normalize_symbol_for_file(symbol)
        return os.path.join(self.processed_dir, timeframe, f"{normalized_symbol}.csv")
    
    def validate_csv_schema(self, file_path: str) -> bool:
        """
        Validate that a CSV file has the correct schema
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            True if the schema is valid, False otherwise
        """
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        
        try:
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                
                # Check header row
                header = next(reader, None)
                if not header:
                    return False
                
                # Check for required columns
                if header != required_columns:
                    return False
                
                # Validate each row
                for row in reader:
                    if len(row) != len(required_columns):
                        return False
                    
                    # Validate timestamp is integer
                    try:
                        timestamp = int(row[0])
                        if timestamp <= 0:
                            return False
                    except ValueError:
                        return False
                    
                    # Validate numeric values for OHLCV
                    for col_idx in range(1, 6):  # open, high, low, close, volume
                        try:
                            float(row[col_idx])
                        except ValueError:
                            return False
        
        except FileNotFoundError:
            return False
        except Exception:
            return False
        
        return True
    
    def read_csv_rows(self, file_path: str) -> List[List[str]]:
        """Read all rows from a CSV file, returning them as a list of lists."""
        rows = []
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                rows.append(row)
        return rows
    
    def write_csv_rows(self, file_path: str, rows: List[List[str]]) -> None:
        """Write rows to a CSV file atomically."""
        # Create temporary file
        temp_path = file_path + self.temp_file_suffix
        
        with open(temp_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)
        
        # Validate the temporary file
        if not self.validate_csv_schema(temp_path):
            os.remove(temp_path)
            raise ValueError(f"Invalid schema in temporary file: {temp_path}")
        
        # Perform atomic replacement using os.replace
        os.replace(temp_path, file_path)
    
    def detect_missing_ranges(
        self, 
        file_path: str, 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None
    ) -> List[Tuple[int, int]]:
        """
        Detect missing ranges in a CSV file.
        
        Args:
            file_path: Path to the CSV file
            start_time: Optional start time to check from
            end_time: Optional end time to check to
            
        Returns:
            List of tuples representing missing ranges (start, end)
        """
        if not os.path.exists(file_path):
            return []
        
        gaps = []
        prev_timestamp = None
        
        # Read timestamps from the file
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Validate headers
            required_fields = {"timestamp", "open", "high", "low", "close", "volume"}
            if not required_fields.issubset(set(reader.fieldnames or [])):
                raise ValueError("Invalid CSV format - missing required fields")
            
            for row in reader:
                try:
                    current_timestamp = int(row['timestamp'])
                    
                    # Apply time filters if provided
                    if start_time is not None and current_timestamp < start_time:
                        continue
                    if end_time is not None and current_timestamp > end_time:
                        break
                    
                    # Check for gaps if we have a previous timestamp
                    if prev_timestamp is not None:
                        expected_next = prev_timestamp + 60  # One minute increment
                        if current_timestamp > expected_next:
                            # Found a gap
                            gaps.append((expected_next, current_timestamp - 60))
                    
                    prev_timestamp = current_timestamp
                except (ValueError, TypeError):
                    # Skip invalid rows
                    continue
        
        return gaps
    
    def merge_sorted_rows(self, existing_rows: List[List[str]], new_rows: List[List[str]]) -> List[List[str]]:
        """
        Merge two sets of sorted CSV rows, eliminating duplicates and maintaining order.
        
        Args:
            existing_rows: Existing rows from the file (with header)
            new_rows: New rows to merge (with or without header)
            
        Returns:
            Merged rows in chronological order
        """
        if not existing_rows:
            return new_rows
        
        if not new_rows:
            return existing_rows
        
        # Determine which list has the header
        existing_has_header = existing_rows and len(existing_rows[0]) == 6 and existing_rows[0][0] == 'timestamp'
        new_has_header = new_rows and len(new_rows[0]) == 6 and new_rows[0][0] == 'timestamp'
        
        # Extract data rows, handling headers
        if existing_has_header:
            existing_data = existing_rows[1:]
            header = existing_rows[0]
        else:
            existing_data = existing_rows
            header = ['timestamp', 'open', 'high', 'low', 'close', 'volume']  # default header
        
        if new_has_header:
            new_data = new_rows[1:]
            # If new file has header but existing doesn't, use the new header
            if not existing_has_header:
                header = new_rows[0]
        else:
            new_data = new_rows
        
        # Extract timestamps and create mapping for duplicate detection
        existing_map = {int(row[0]): row for row in existing_data if len(row) >= 6}
        new_map = {int(row[0]): row for row in new_data if len(row) >= 6}
        
        # Merge maps, preferring newer data for conflicts
        all_timestamps = set(existing_map.keys()) | set(new_map.keys())
        sorted_timestamps = sorted(all_timestamps)
        
        merged_data = []
        for ts in sorted_timestamps:
            # Prefer new data in case of timestamp collision
            if ts in new_map:
                merged_data.append(new_map[ts])
            elif ts in existing_map:
                merged_data.append(existing_map[ts])
        
        # Add header back to the result
        return [header] + merged_data
    
    def get_file_index(self, symbol: str) -> Dict[str, Any]:
        """Get the index information for a symbol's data file"""
        import json
        csv_file_path = self.get_raw_file_path(symbol)
        idx_file_path = self.get_index_file_path(symbol)

        # Try to load from index file first, BUT only if the CSV file still exists
        if os.path.exists(idx_file_path) and os.path.exists(csv_file_path):
            try:
                with open(idx_file_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass  # Fall back to scanning the file

        # If no index file exists or CSV file has been updated since index was created, scan the CSV file
        if os.path.exists(csv_file_path):
            try:
                with open(csv_file_path, 'r', newline='') as csvfile:
                    reader = csv.DictReader(csvfile)

                    # Validate headers
                    required_fields = {"timestamp", "open", "high", "low", "close", "volume"}
                    if not required_fields.issubset(set(reader.fieldnames or [])):
                        return {}

                    timestamps = []
                    for row in reader:
                        try:
                            timestamp = int(row['timestamp'])
                            timestamps.append(timestamp)
                        except (ValueError, TypeError):
                            continue

                    if timestamps:
                        earliest = min(timestamps)
                        latest = max(timestamps)
                        row_count = len(timestamps)
                        file_size = os.path.getsize(csv_file_path)

                        # Update index file
                        self._update_index_file(symbol, earliest, latest, row_count, file_size)

                        return {
                            "earliest_timestamp": earliest,
                            "latest_timestamp": latest,
                            "row_count": row_count,
                            "file_size": file_size
                        }
            except Exception:
                pass

        # If the CSV file doesn't exist, return empty dict to indicate missing file
        elif os.path.exists(idx_file_path) and not os.path.exists(csv_file_path):
            # CSV file doesn't exist but index file does - this means CSV was deleted
            # Remove the stale index file
            try:
                os.remove(idx_file_path)
            except:
                pass  # Ignore errors when removing index file
            return {}

        return {}
    
    def _update_index_file(self, symbol: str, earliest: int, latest: int, row_count: int, file_size: int) -> None:
        """Update the index file for a symbol"""
        import json
        idx_file_path = self.get_index_file_path(symbol)
        
        index_data = {
            "earliest_timestamp": earliest,
            "latest_timestamp": latest,
            "row_count": row_count,
            "file_size": file_size,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        temp_path = idx_file_path + self.temp_file_suffix
        with open(temp_path, 'w') as f:
            json.dump(index_data, f)
        
        os.replace(temp_path, idx_file_path)
    
    def fill_gaps_in_range(
        self, 
        symbol: str, 
        start_ts: int, 
        end_ts: int, 
        fill_strategy: str = "forward_fill"
    ) -> bool:
        """
        Fill gaps in a specific range for a symbol.
        
        Args:
            symbol: The symbol to fill gaps for
            start_ts: Start timestamp of the range
            end_ts: End timestamp of the range
            fill_strategy: Strategy to use for filling ("forward_fill" or "zero_fill")
            
        Returns:
            True if gaps were filled, False otherwise
        """
        file_path = self.get_raw_file_path(symbol)
        if not os.path.exists(file_path):
            return False
        
        # Read existing data
        all_rows = self.read_csv_rows(file_path)
        if len(all_rows) < 2:  # Need header + at least 1 data row
            return False
        
        header = all_rows[0]
        data_rows = all_rows[1:]
        
        # Convert to timestamp -> row mapping
        row_map = {int(row[0]): row for row in data_rows if len(row) >= 6}
        
        # Find all timestamps in range that are missing
        current_ts = start_ts
        filled = False
        
        while current_ts <= end_ts:
            if current_ts not in row_map:
                # Find the previous timestamp to use for forward fill
                prev_ts = current_ts - 60
                while prev_ts >= start_ts and prev_ts not in row_map:
                    prev_ts -= 60
                
                if prev_ts in row_map and prev_ts >= start_ts:
                    # Use forward fill from previous valid data
                    prev_row = row_map[prev_ts]
                    filled_row = [
                        str(current_ts),
                        prev_row[4],  # open = close of previous
                        prev_row[4],  # high = close of previous  
                        prev_row[4],  # low = close of previous
                        prev_row[4],  # close = close of previous
                        "0"           # volume = 0
                    ]
                    row_map[current_ts] = filled_row
                    filled = True
                else:
                    # Cannot fill (no previous data), skip
                    pass
            current_ts += 60
        
        if filled:
            # Reconstruct all rows in order
            all_timestamps = sorted(row_map.keys())
            new_data_rows = [row_map[ts] for ts in all_timestamps]
            new_all_rows = [header] + new_data_rows
            
            # Write the updated file atomically
            self.write_csv_rows(file_path, new_all_rows)
        
        return filled
    
    def compact_and_aggregate(self, symbol: str, cleanup_old: bool = True) -> None:
        """
        Generate processed (aggregated) files from raw data and optionally clean up old files.

        Args:
            symbol: The symbol to process
            cleanup_old: Whether to remove old files beyond retention period
        """
        raw_file_path = self.get_raw_file_path(symbol)
        if not os.path.exists(raw_file_path):
            return

        # Read raw data
        df = pd.read_csv(raw_file_path)

        # Ensure timestamp column is integer Unix timestamp
        if 'timestamp' in df.columns:
            # Convert timestamp to integer Unix timestamp if it's not already
            if df['timestamp'].dtype in ['object', 'float64']:
                try:
                    # If it's a datetime string, convert to Unix timestamp
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).astype('int64')
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

        # Remove any rows with NaN timestamps after conversion
        df = df.dropna(subset=['timestamp'])

        if df.empty:
            print(f'Warning: No valid timestamps after conversion for {symbol}, skipping')
            return

        # Now convert to datetime for processing
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

        # Remove any remaining NaT (Not a Time) values
        df = df.dropna(subset=['timestamp'])

        if df.empty:
            print(f'Warning: No valid datetime values after conversion for {symbol}, skipping')
            return

        df.set_index('timestamp', inplace=True)
        
        # Define timeframes to aggregate
        timeframes = {'5m': '5T', '15m': '15T', '30m': '30T', '1h': '1H', '4h': '4H', '1d': '1D'}
        
        for tf_name, tf_spec in timeframes.items():
            # Create timeframe directory if it doesn't exist
            tf_dir = os.path.join(self.processed_dir, tf_name)
            os.makedirs(tf_dir, exist_ok=True)
            
            # Aggregate: open from first, high from max, low from min, close from last, volume from sum
            agg_df = df.resample(tf_spec).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            # Add timestamp column back
            agg_df.reset_index(inplace=True)
            agg_df['timestamp'] = agg_df['timestamp'].apply(lambda x: int(x.timestamp()))
            
            # Reorder columns
            agg_df = agg_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Save aggregated data
            output_path = self.get_processed_file_path(symbol, tf_name)
            agg_df.to_csv(output_path, index=False)
        
        # Optionally clean up old files beyond retention period
        if cleanup_old:
            self._cleanup_retention(symbol)
    
    def _cleanup_retention(self, symbol: str) -> None:
        """Clean up old data files based on retention settings"""
        # Clean up raw files beyond retention period
        raw_file_path = self.get_raw_file_path(symbol)
        if os.path.exists(raw_file_path):
            # Read the file and remove old entries
            df = pd.read_csv(raw_file_path)

            # Ensure timestamp column is integer Unix timestamp
            if 'timestamp' in df.columns:
                # Convert timestamp to integer Unix timestamp if it's not already
                if df['timestamp'].dtype in ['object', 'float64']:
                    try:
                        # If it's a datetime string, convert to Unix timestamp
                        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).astype('int64')
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

            # Remove any rows with NaN timestamps after conversion
            df = df.dropna(subset=['timestamp'])

            if df.empty:
                return

            # Now convert to datetime for processing
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

            # Remove any remaining NaT (Not a Time) values
            df = df.dropna(subset=['timestamp'])

            if df.empty:
                return

            cutoff_date = datetime.now() - timedelta(days=self.raw_retention_days)
            df_filtered = df[df['timestamp'] >= cutoff_date]

            if len(df_filtered) != len(df):
                # Convert back to Unix timestamp integers for saving
                df_filtered_reset = df_filtered.reset_index()
                df_filtered_reset['timestamp'] = df_filtered_reset['timestamp'].astype('int64') // 10**9
                df_filtered_reset.to_csv(raw_file_path, index=False)
    
    def validate_continuous_range(self, symbol: str, start_ts: int, end_ts: int) -> bool:
        """
        Check if a range is continuous (has no gaps) in a symbol's data file.
        
        Args:
            symbol: The symbol to check
            start_ts: Start timestamp
            end_ts: End timestamp
            
        Returns:
            True if the range is continuous, False if there are gaps
        """
        file_path = self.get_raw_file_path(symbol)
        if not os.path.exists(file_path):
            return False
        
        # Check for gaps in the specified range
        gaps = self.detect_missing_ranges(file_path, start_ts, end_ts)
        if len(gaps) > 0:
            return False
        
        # Also check if we have data for the start and end timestamps
        # If the range is fully covered, the earliest should be <= start_ts 
        # and the latest should be >= end_ts
        index = self.get_file_index(symbol)
        if not index or not index.get('earliest_timestamp') or not index.get('latest_timestamp'):
            return False
            
        # Check if the file contains data covering the range
        # If the range is [start_ts, end_ts], we need to make sure we have data in that range
        # and that there are no gaps within that range
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Validate headers
            required_fields = {"timestamp", "open", "high", "low", "close", "volume"}
            if not required_fields.issubset(set(reader.fieldnames or [])):
                return False
            
            timestamps_in_range = []
            for row in reader:
                try:
                    ts = int(row['timestamp'])
                    if start_ts <= ts <= end_ts:
                        timestamps_in_range.append(ts)
                except (ValueError, TypeError):
                    continue
        
        # Check if all expected timestamps in the range are present
        expected_timestamps = set()
        current = start_ts
        while current <= end_ts:
            expected_timestamps.add(current)
            current += 60  # One minute increments
        
        actual_timestamps = set(timestamps_in_range)
        missing_timestamps = expected_timestamps - actual_timestamps
        
        return len(missing_timestamps) == 0