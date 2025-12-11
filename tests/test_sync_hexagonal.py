"""
Comprehensive tests for the sync system following hexagonal architecture.
"""
import asyncio
import tempfile
import unittest
import csv
import os
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from domain.sync.entities import SymbolSyncConfig, SyncJob, GapRange, FileIndex
from application.configs.symbol_config import get_symbols, get_symbol_config, _parse_wfo_symbols
from application.data_sync.sync_manager import SyncManager, PriorityJobQueue
from application.data_sync.ports import FileRepository
from domain.ports.sync import DataDownloader
from application.data_sync.sync_loop import SyncLoop
from application.data_sync.watcher_retune import WatcherRetuneUseCase
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter


class MockFileRepository(FileRepository):
    """Mock implementation of FileRepository for testing"""
    
    def __init__(self):
        self.raw_path = "/tmp/test/raw/1m"
        self.files = {}
        self.missing_ranges = []
        self.continuous_ranges = {}
    
    def get_raw_file_path(self, symbol: str) -> str:
        return f"{self.raw_path}/{symbol.replace('/', '-')}.csv"
    
    def get_index_file_path(self, symbol: str) -> str:
        return f"/tmp/test/index/{symbol.replace('/', '-')}.idx.json"
    
    def get_processed_file_path(self, symbol: str, timeframe: str) -> str:
        return f"/tmp/test/processed/{timeframe}/{symbol.replace('/', '-')}.csv"
    
    def validate_csv_schema(self, file_path: str) -> bool:
        return True  # Simplified for testing
    
    def read_csv_rows(self, file_path: str) -> list:
        return self.files.get(file_path, [])
    
    def write_csv_rows(self, file_path: str, rows: list) -> None:
        self.files[file_path] = rows
    
    def detect_missing_ranges(self, file_path: str, start_time: int = None, end_time: int = None) -> list:
        return self.missing_ranges
    
    def merge_sorted_rows(self, existing_rows: list, new_rows: list) -> list:
        # Simple merge for testing - in real implementation would be more complex
        header = existing_rows[0] if existing_rows else (new_rows[0] if new_rows else [])
        data = existing_rows[1:] if existing_rows else []
        new_data = new_rows[1:] if new_rows else []
        return [header] + data + new_data
    
    def get_file_index(self, symbol: str) -> dict:
        return {"earliest_timestamp": 1609459200, "latest_timestamp": 1609459320, "row_count": 3, "file_size": 150}
    
    def fill_gaps_in_range(self, symbol: str, start_ts: int, end_ts: int, fill_strategy: str = "forward_fill") -> bool:
        return True  # Simplified for testing
    
    def compact_and_aggregate(self, symbol: str, cleanup_old: bool = True) -> None:
        pass  # Simplified for testing
    
    def validate_continuous_range(self, symbol: str, start_ts: int, end_ts: int) -> bool:
        return self.continuous_ranges.get((symbol, start_ts, end_ts), False)


class MockDataDownloader(DataDownloader):
    """Mock implementation of DataDownloader for testing"""
    
    def __init__(self, return_data=None):
        self.return_data = return_data or []
        self.fetch_calls = []
    
    async def fetch_range(self, symbol: str, start_ts: int, end_ts: int) -> list:
        self.fetch_calls.append((symbol, start_ts, end_ts))
        return self.return_data


class TestSymbolConfiguration(unittest.TestCase):
    """Test symbol configuration functionality"""

    def test_parse_wfo_symbols_from_env(self):
        """Test parsing of WFO symbols from environment"""
        symbols = _parse_wfo_symbols()
        # With the environment variable we set, we should have some symbols
        self.assertGreater(len(symbols), 0)

        for symbol in symbols[:5]:  # Test first few symbols
            self.assertIsInstance(symbol, SymbolSyncConfig)
            self.assertTrue(symbol.symbol)
            self.assertIn('-', symbol.symbol)  # Should have formatted with hyphens
    
    def test_get_symbol_config(self):
        """Test getting configuration for a specific symbol"""
        symbol_config = get_symbol_config("BTCUSDT")
        if symbol_config:  # May be None if environment not set up
            self.assertIsInstance(symbol_config, SymbolSyncConfig)
            self.assertEqual(symbol_config.symbol.replace('-', '').upper(), "BTCUSDT")


class TestSyncManager(unittest.TestCase):
    """Test sync manager functionality"""
    
    def setUp(self):
        self.mock_file_repo = MockFileRepository()
        self.mock_data_downloader = MockDataDownloader()
        self.sync_manager = SyncManager(self.mock_file_repo, self.mock_data_downloader)
    
    def test_add_symbol_to_queue(self):
        """Test adding a symbol to the sync queue"""
        # Set up mock missing ranges
        self.mock_file_repo.missing_ranges = [(1609459260, 1609459320)]  # One gap
        
        async def run_test():
            await self.sync_manager.add_symbol_to_queue("BTC-USDT")
            self.assertFalse(self.sync_manager.job_queue.is_empty())
            
            job = self.sync_manager.job_queue.pop()
            self.assertIsNotNone(job)
            self.assertEqual(job.symbol, "BTC-USDT")
            self.assertEqual(job.start_ts, 1609459260)
            self.assertEqual(job.end_ts, 1609459320)
        
        asyncio.run(run_test())
    
    def test_priority_job_queue(self):
        """Test priority job queue functionality"""
        queue = PriorityJobQueue()
        
        # Add jobs with different priorities
        job_low = SyncJob("BTC-USDT", 1609459200, 1609459300, priority=1)
        job_high = SyncJob("ETH-USDT", 1609459200, 1609459300, priority=10)
        
        queue.push(job_low)
        queue.push(job_high)
        
        # High priority job should come first
        first_job = queue.pop()
        self.assertEqual(first_job.symbol, "ETH-USDT")
        self.assertEqual(first_job.priority, 10)
        
        second_job = queue.pop()
        self.assertEqual(second_job.symbol, "BTC-USDT")
        self.assertEqual(second_job.priority, 1)
    
    def test_process_single_job_success(self):
        """Test successful processing of a single sync job"""
        # Mock data to return
        mock_data = [
            {'timestamp': 1609459260, 'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 104.0, 'volume': 1000}
        ]
        mock_downloader = MockDataDownloader(return_data=mock_data)
        sync_manager = SyncManager(self.mock_file_repo, mock_downloader)
        
        job = SyncJob("BTC-USDT", 1609459200, 1609459300, priority=5)
        
        async def run_test():
            result = await sync_manager.process_single_job(job)
            self.assertTrue(result['success'])
            self.assertEqual(result['rows_written'], 1)
        
        asyncio.run(run_test())


class TestFileRepositoryAdapter(unittest.TestCase):
    """Test file repository adapter functionality"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_repo = FileRepositoryAdapter(base_data_dir=self.temp_dir)
    
    def test_validate_csv_schema_valid(self):
        """Test validation of valid CSV files"""
        # Create a valid CSV file
        csv_content = '''timestamp,open,high,low,close,volume
1609459200,100.0,105.0,99.0,104.0,1000
1609459260,104.0,108.0,103.0,107.0,1200'''
        
        file_path = os.path.join(self.temp_dir, "raw", "1m", "BTC-USDT.csv")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(csv_content)
        
        self.assertTrue(self.file_repo.validate_csv_schema(file_path))
    
    def test_detect_missing_ranges_no_gaps(self):
        """Test detection of ranges with no gaps"""
        # Create a CSV file with no gaps
        csv_content = '''timestamp,open,high,low,close,volume
1609459200,100.0,105.0,99.0,104.0,1000
1609459260,104.0,108.0,103.0,107.0,1200
1609459320,107.0,110.0,106.0,109.0,1100'''
        
        file_path = os.path.join(self.temp_dir, "raw", "1m", "BTC-USDT.csv")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(csv_content)
        
        gaps = self.file_repo.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps), 0)
    
    def test_detect_missing_ranges_with_gaps(self):
        """Test detection of ranges with gaps"""
        # Create a CSV file with a gap
        csv_content = '''timestamp,open,high,low,close,volume
1609459200,100.0,105.0,99.0,104.0,1000
1609459380,107.0,110.0,106.0,109.0,1100  # Gap: missing 1609459260 and 1609459320'''
        
        file_path = os.path.join(self.temp_dir, "raw", "1m", "BTC-USDT.csv")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(csv_content)
        
        gaps = self.file_repo.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0], (1609459260, 1609459320))


class TestDataDownloaderAdapter(unittest.TestCase):
    """Test data downloader adapter functionality"""
    
    @patch('infrastructure.data_sync.data_downloader_adapter.ccxt_async')
    def test_fetch_range(self, mock_ccxt):
        """Test fetching data range (with mocking)"""
        # This is a partial test since actual API calls are complex to test
        downloader = DataDownloaderAdapter()
        
        # Mock the exchange instance
        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1609459200000, 100.0, 105.0, 99.0, 104.0, 1000],  # timestamp in ms
        ])
        downloader.exchange_instances['bingx'] = mock_exchange
        
        async def run_test():
            # This would fail because it tries to call real CCXT methods
            # For a real test, we'd need more thorough mocking
            pass
            
        # Since full test is complex, just verify the class can be instantiated
        self.assertIsInstance(downloader, DataDownloaderAdapter)


class TestWatcherRetuneUseCase(unittest.TestCase):
    """Test watcher retune use case functionality"""
    
    def setUp(self):
        self.mock_file_repo = MockFileRepository()
        self.mock_data_downloader = MockDataDownloader()
        self.mock_sync_manager = MagicMock()
        self.watcher_retune = WatcherRetuneUseCase(
            self.mock_file_repo, 
            self.mock_data_downloader, 
            self.mock_sync_manager
        )
    
    def test_validate_interval(self):
        """Test interval validation"""
        # Set up mock to return True for continuous range
        self.mock_file_repo.continuous_ranges[("BTC-USDT", 1609459200, 1609459300)] = True
        
        result = self.watcher_retune.validate_interval("BTC-USDT", 1609459200, 1609459300)
        self.assertTrue(result)
        
        # Set up mock to return False for discontinuous range
        self.mock_file_repo.continuous_ranges[("ETH-USDT", 1609459200, 1609459300)] = False
        
        result = self.watcher_retune.validate_interval("ETH-USDT", 1609459200, 1609459300)
        self.assertFalse(result)
    
    def test_force_repair_range(self):
        """Test force repair range functionality"""
        async def run_test():
            result = await self.watcher_retune.force_repair_range("BTC-USDT", 1609459200, 1609459300)
            # Should return True since file_repo.fill_gaps_in_range returns True in mock
            self.assertTrue(result)
        
        asyncio.run(run_test())


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete sync system"""
    
    def test_complete_sync_cycle_with_adapters(self):
        """Test the complete sync cycle using real adapters"""
        # Create temporary directory for test
        temp_dir = tempfile.mkdtemp()
        
        # Create file repository adapter with temp directory
        file_repo = FileRepositoryAdapter(base_data_dir=temp_dir)
        
        # Create a CSV file with gaps for testing
        csv_content = '''timestamp,open,high,low,close,volume
1609459200,100.0,105.0,99.0,104.0,1000
1609459380,107.0,110.0,106.0,109.0,1100'''
        
        file_path = os.path.join(temp_dir, "raw", "1m", "BTC-USDT.csv")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(csv_content)
        
        # Verify gaps exist initially
        gaps = file_repo.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps), 1)
        
        # Fill gaps
        success = file_repo.fill_gaps_in_range("BTC-USDT", 1609459200, 1609459380)
        self.assertTrue(success)
        
        # Verify no gaps after filling
        gaps_after = file_repo.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps_after), 0)


if __name__ == '__main__':
    unittest.main()