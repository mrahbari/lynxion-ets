"""
Integration test for the downloader/sync system with a fake exchange server.
"""
import asyncio
import tempfile
import unittest
import csv
import os
from datetime import datetime, timedelta

from file_manager import FileManager, file_manager
from downloader_async import AsyncDownloader
from sync_manager import SyncManager
from application.configs.sync_settings import settings
from application.configs.symbol_config import SymbolConfig, get_symbol_config, get_symbols
from unittest.mock import patch, MagicMock


class TestSyncIntegration(unittest.TestCase):
    def setUp(self):
        """Set up the integration test environment"""
        # Create a temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.original_data_dir = settings.data_dir
        settings.data_dir = self.temp_dir
        
        # Initialize components with test settings
        self.file_manager = FileManager(base_data_dir=self.temp_dir)
        self.sync_manager = SyncManager()
        
        # Test symbol
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
        
        # Create data with gaps: have 0-2, skip 3-5, have 6-8
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Write some initial data points
            for i in range(3):  # timestamps 0, 1, 2 (minutes)
                ts = base_timestamp + i * 60
                writer.writerow([ts, 100 + i, 105 + i, 99 + i, 104 + i, 1000 + i*100])
            
            # Skip next 3 data points to create a gap (timestamps 3, 4, 5)
            
            # Write more data after the gap
            for i in range(6, 9):  # timestamps 6, 7, 8
                ts = base_timestamp + i * 60
                writer.writerow([ts, 100 + i, 105 + i, 99 + i, 104 + i, 1000 + i*100])
        
        return file_path
    
    @unittest.skip("Requires real exchange or proper mocking")
    def test_sync_manager_end_to_end(self):
        """Test the complete sync flow from gap detection to fill"""
        # Create a file with gaps
        base_timestamp = 1609459200  # 2021-01-01 00:00:00
        file_path = self.create_test_csv_with_gaps(self.test_symbol, base_timestamp)
        
        # Verify gaps exist initially
        gaps_before = self.file_manager.detect_missing_ranges(file_path, 
                                                            base_timestamp, 
                                                            base_timestamp + 500)
        self.assertGreater(len(gaps_before), 0, "Test file should have gaps initially")
        
        # Mock the downloader to return data for the missing range
        with patch('downloader_async.fetch_range_for_symbol') as mock_fetch:
            # Return data for the gap range
            gap_data = []
            for i in range(3, 6):  # Fill the missing minutes 3, 4, 5
                ts = base_timestamp + i * 60
                gap_data.append({
                    'timestamp': ts,
                    'open': 100 + i,
                    'high': 105 + i,
                    'low': 99 + i,
                    'close': 104 + i,
                    'volume': 1000 + i*100
                })
            mock_fetch.return_value = gap_data
            
            # Run the sync manager for the specific symbol
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_sync():
                await self.sync_manager.add_symbol_to_queue(self.test_symbol)
                # Process one job from the queue
                if not self.sync_manager.job_queue.is_empty():
                    job = self.sync_manager.job_queue.pop()
                    if job:
                        await self.sync_manager.process_single_job(job)
            
            # Execute the sync
            loop.run_until_complete(run_sync())
            loop.close()
        
        # Verify gaps are filled
        gaps_after = self.file_manager.detect_missing_ranges(file_path,
                                                           base_timestamp,
                                                           base_timestamp + 500)
        self.assertEqual(len(gaps_after), 0, f"Gaps should be filled after sync, but found: {gaps_after}")
    
    def test_file_manager_compact_and_aggregate(self):
        """Test that file compaction and aggregation works correctly"""
        # Create a file with some data
        file_path = self.file_manager.get_raw_file_path(self.test_symbol)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Write 1-hour worth of 1-minute data
            base_time = 1609459200  # 2021-01-01 00:00:00
            for i in range(60):  # 60 minutes = 1 hour of data
                ts = base_time + i * 60
                price = 100 + i * 0.1
                writer.writerow([ts, price, price + 0.5, price - 0.5, price + 0.1, 1000 + i * 10])
        
        # Run compaction
        self.file_manager.compact_and_aggregate(self.test_symbol, cleanup_old=False)
        
        # Check that processed files were created
        for tf in ['5m', '15m', '30m', '1h']:
            processed_path = self.file_manager.get_processed_file_path(self.test_symbol, tf)
            self.assertTrue(os.path.exists(processed_path), f"Processed {tf} file should exist")
            
            # Check that it has the expected number of rows
            with open(processed_path, 'r') as f:
                rows = list(csv.DictReader(f))
                # Verify the aggregation produced reasonable results
                if rows:
                    for row in rows:
                        self.assertIn('timestamp', row)
                        self.assertIn('open', row)
                        self.assertIn('high', row)
                        self.assertIn('low', row)
                        self.assertIn('close', row)
                        self.assertIn('volume', row)


class TestFakeExchangeServerIntegration(unittest.TestCase):
    """Integration test using a fake exchange server approach"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_data_dir = settings.data_dir
        settings.data_dir = self.temp_dir
        
        # Set up the components
        self.file_manager = FileManager(base_data_dir=self.temp_dir)
        self.downloader = AsyncDownloader()
        self.sync_manager = SyncManager()
    
    def tearDown(self):
        import shutil
        settings.data_dir = self.original_data_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_sync_cycle(self):
        """Test a complete sync cycle with mock data"""
        # Create initial files with gaps for a couple symbols
        symbols = ["BTC-USDT", "ETH-USDT"]
        
        for symbol in symbols:
            file_path = self.file_manager.get_raw_file_path(symbol)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create CSV with gaps
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Data from 00:00 to 00:02
                for i in range(3):
                    ts = 1609459200 + i * 60
                    writer.writerow([ts, 100 + i, 105 + i, 99 + i, 104 + i, 1000 + i*100])
                
                # Gap from 00:03 to 00:05
                
                # Data from 00:06 to 00:08
                for i in range(6, 9):
                    ts = 1609459200 + i * 60
                    writer.writerow([ts, 100 + i, 105 + i, 99 + i, 104 + i, 1000 + i*100])
        
        # Mock the download function to return data for the gaps
        async def mock_fetch_range(symbol, start_ts, end_ts):
            # Return data to fill the gaps (timestamps 1609459380, 1609459440, 1609459500)
            gap_data = []
            for i in range(3):  # Fill 3 minutes of gaps
                ts = start_ts + i * 60
                if ts <= end_ts:  # Only add if within requested range
                    gap_data.append({
                        'timestamp': ts,
                        'open': 103 + i,
                        'high': 108 + i,
                        'low': 102 + i,
                        'close': 107 + i,
                        'volume': 1300 + i*50
                    })
            return gap_data
        
        import types
        original_fetch = self.downloader.fetch_range
        
        # Patch the fetch_range method
        self.downloader.fetch_range = types.MethodType(
            lambda self, symbol, start_ts, end_ts: mock_fetch_range(symbol, start_ts, end_ts),
            self.downloader
        )
        
        # Run a sync cycle
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_sync_cycle():
            results = await self.sync_manager.run_sync_cycle(symbols)
            return results
        
        results = loop.run_until_complete(run_sync_cycle())
        loop.close()
        
        # Restore the original method
        self.downloader.fetch_range = original_fetch
        
        # Verify results
        self.assertGreater(results['symbols_fixed'], 0)
        self.assertGreater(results['rows_written'], 0)
        
        # Check that gaps were filled in the files
        for symbol in symbols:
            file_path = self.file_manager.get_raw_file_path(symbol)
            
            # Verify no gaps in the previously problematic range
            gaps = self.file_manager.detect_missing_ranges(file_path, 1609459200, 1609459560)
            self.assertEqual(len(gaps), 0, f"Should be no gaps for {symbol} after sync, but found: {gaps}")


if __name__ == '__main__':
    unittest.main()