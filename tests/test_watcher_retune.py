"""
Test for watcher repair functionality.
"""
import asyncio
import tempfile
import unittest
import csv
import os
from datetime import datetime

from watcher_retune import WatcherRetune
from file_manager import FileManager
from application.configs.sync_settings import settings


class TestWatcherRetune(unittest.TestCase):
    def setUp(self):
        """Set up the watcher retune test environment"""
        # Create a temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.original_data_dir = settings.data_dir
        settings.data_dir = self.temp_dir
        
        # Initialize components
        self.file_manager = FileManager(base_data_dir=self.temp_dir)
        self.watcher_retune = WatcherRetune()
        self.test_symbol = "BTC-USDT"
    
    def tearDown(self):
        """Clean up test data"""
        import shutil
        settings.data_dir = self.original_data_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_csv_with_gaps(self, symbol, base_timestamp=1609459200):
        """Create a test CSV file with known gaps"""
        file_path = self.file_manager.get_raw_file_path(symbol)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Write data with a gap: minutes 0, 1, then skip to 4, 5
            for i in [0, 1, 4, 5]:  # There's a gap at minutes 2 and 3
                ts = base_timestamp + i * 60
                writer.writerow([ts, 100 + i, 105 + i, 99 + i, 104 + i, 1000 + i*100])
        
        return file_path
    
    def test_validate_interval_gap_detection(self):
        """Test that validate_interval correctly detects gaps"""
        base_timestamp = 1609459200
        file_path = self.create_test_csv_with_gaps(self.test_symbol, base_timestamp)
        
        # The full range 0-5 should have gaps
        full_range_valid = self.watcher_retune.validate_interval(
            self.test_symbol, 
            base_timestamp, 
            base_timestamp + 5 * 60
        )
        self.assertFalse(full_range_valid, "Full range with gaps should be invalid")
        
        # The continuous range 0-1 should be valid
        continuous_range_valid = self.watcher_retune.validate_interval(
            self.test_symbol, 
            base_timestamp, 
            base_timestamp + 1 * 60
        )
        self.assertTrue(continuous_range_valid, "Continuous range should be valid")
    
    @unittest.skip("Requires actual download functionality to be fully tested")
    def test_request_repair_sync(self):
        """Test the synchronous repair request"""
        base_timestamp = 1609459200
        file_path = self.create_test_csv_with_gaps(self.test_symbol, base_timestamp)
        
        # Check initial state - range should have gaps
        has_gaps_before = not self.watcher_retune.validate_interval(
            self.test_symbol,
            base_timestamp + 2 * 60,  # Minute 2
            base_timestamp + 3 * 60   # Minute 3
        )
        self.assertTrue(has_gaps_before, "Should have gaps before repair")
        
        # Mock the download functionality to return data for the gap
        import types
        from downloader_async import AsyncDownloader
        
        async def mock_fetch_range(symbol, start_ts, end_ts):
            gap_data = []
            current_ts = start_ts
            while current_ts <= end_ts:
                gap_data.append({
                    'timestamp': current_ts,
                    'open': 102.0,
                    'high': 107.0,
                    'low': 101.0,
                    'close': 106.0,
                    'volume': 1200
                })
                current_ts += 60
            return gap_data
        
        # We'll need to modify the sync_manager to use our mocked function
        # For now, just test the gap filling functionality directly
        success = self.file_manager.fill_gaps_in_range(
            self.test_symbol,
            base_timestamp + 2 * 60,  # Start of gap
            base_timestamp + 3 * 60   # End of gap
        )
        
        self.assertTrue(success, "Gap fill should succeed")
        
        # Verify the range is now continuous
        is_continuous = self.watcher_retune.validate_interval(
            self.test_symbol,
            base_timestamp + 2 * 60,
            base_timestamp + 3 * 60
        )
        self.assertTrue(is_continuous, "Range should be continuous after gap fill")
    
    def test_force_repair_range(self):
        """Test the force repair functionality"""
        base_timestamp = 1609459200
        file_path = self.create_test_csv_with_gaps(self.test_symbol, base_timestamp)
        
        # Verify gaps exist initially
        before_repair_valid = self.watcher_retune.validate_interval(
            self.test_symbol,
            base_timestamp + 2 * 60,  # Start of gap (minute 2)
            base_timestamp + 3 * 60   # End of gap (minute 3)
        )
        self.assertFalse(before_repair_valid, "Range should have gaps initially")
        
        # Use the force repair function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_force_repair():
            return await self.watcher_retune.force_repair_range(
                self.test_symbol,
                base_timestamp + 2 * 60,
                base_timestamp + 3 * 60
            )
        
        success = loop.run_until_complete(run_force_repair())
        loop.close()
        
        # Verify the repair worked
        self.assertTrue(success, "Force repair should succeed for small gaps")
        
        after_repair_valid = self.watcher_retune.validate_interval(
            self.test_symbol,
            base_timestamp + 2 * 60,
            base_timestamp + 3 * 60
        )
        self.assertTrue(after_repair_valid, "Range should be valid after repair")
    
    def test_large_gap_handling(self):
        """Test that large gaps are handled properly (not auto-filled)"""
        base_timestamp = 1609459200
        file_path = self.file_manager.get_raw_file_path(self.test_symbol)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create a file with a very large gap
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Write data at start and end, but leave a huge gap in the middle
            writer.writerow([base_timestamp, 100.0, 105.0, 99.0, 104.0, 1000])
            writer.writerow([base_timestamp + 1000 * 60, 200.0, 205.0, 199.0, 204.0, 2000])  # 1000 minutes gap!
        
        # This should not be considered valid
        is_valid = self.watcher_retune.validate_interval(
            self.test_symbol,
            base_timestamp,
            base_timestamp + 1000 * 60
        )
        self.assertFalse(is_valid, "Large gap range should not be valid")
        
        # Force repair on a large gap should return False (since it can't auto-fill large gaps)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_large_gap_repair():
            return await self.watcher_retune.force_repair_range(
                self.test_symbol,
                base_timestamp,
                base_timestamp + 1000 * 60,
                max_gap_fill_minutes=10  # Very small limit
            )
        
        success = loop.run_until_complete(run_large_gap_repair())
        loop.close()
        
        # Repair should return False for large gaps that exceed the fill limit
        self.assertFalse(success, "Should not auto-fill very large gaps")


if __name__ == '__main__':
    unittest.main()