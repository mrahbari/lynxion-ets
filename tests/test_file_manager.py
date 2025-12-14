"""
Unit tests for file_manager.py
"""
import os
import tempfile
import unittest
from datetime import datetime
from file_manager import FileManager, GapRange
import csv


class TestFileManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_manager = FileManager(base_data_dir=self.temp_dir)
        self.test_symbol = "TEST-USDT"
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_csv(self, symbol, data_rows):
        """Helper to create a test CSV file"""
        file_path = self.file_manager.get_raw_file_path(symbol)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume'])  # header
            for row in data_rows:
                writer.writerow(row)
        
        return file_path
    
    def test_validate_csv_schema_valid(self):
        """Test that valid CSV files pass validation"""
        # Create a valid CSV file
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0, 1000],  # 2021-01-01 00:00:00
            [1609459260, 104.0, 108.0, 103.0, 107.0, 1200],  # 2021-01-01 00:01:00
        ])
        
        self.assertTrue(self.file_manager.validate_csv_schema(file_path))
    
    def test_validate_csv_schema_invalid(self):
        """Test that invalid CSV files fail validation"""
        # Create an invalid CSV file (missing column)
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0],  # Missing volume
        ])
        
        self.assertFalse(self.file_manager.validate_csv_schema(file_path))
    
    def test_detect_missing_ranges_no_gaps(self):
        """Test that files without gaps return empty gap list"""
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0, 1000],  # 2021-01-01 00:00:00
            [1609459260, 104.0, 108.0, 103.0, 107.0, 1200],  # 2021-01-01 00:01:00
            [1609459320, 107.0, 110.0, 106.0, 109.0, 1100],  # 2021-01-01 00:02:00
        ])
        
        gaps = self.file_manager.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps), 0)
    
    def test_detect_missing_ranges_with_gaps(self):
        """Test that files with gaps correctly identify them"""
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0, 1000],  # 2021-01-01 00:00:00
            [1609459380, 107.0, 110.0, 106.0, 109.0, 1100],  # 2021-01-01 00:03:00 (gap from 00:01 to 00:02)
        ])
        
        gaps = self.file_manager.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].start, 1609459260)  # 00:01:00
        self.assertEqual(gaps[0].end, 1609459320)    # 00:02:00
    
    def test_merge_sorted_rows(self):
        """Test that rows are properly merged"""
        existing_rows = [
            ['timestamp', 'open', 'high', 'low', 'close', 'volume'],
            ['1609459200', '100.0', '105.0', '99.0', '104.0', '1000'],
            ['1609459320', '107.0', '110.0', '106.0', '109.0', '1100'],
        ]
        
        new_rows = [
            ['1609459260', '104.0', '108.0', '103.0', '107.0', '1200'],  # Should be inserted in middle
        ]
        
        merged = self.file_manager.merge_sorted_rows(existing_rows, new_rows)
        
        # Should have 3 rows (header + 2 data rows) in correct order
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0], ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.assertEqual(merged[1], ['1609459200', '100.0', '105.0', '99.0', '104.0', '1000'])
        self.assertEqual(merged[2], ['1609459260', '104.0', '108.0', '103.0', '107.0', '1200'])
    
    def test_fill_gaps_in_range(self):
        """Test that gaps in a range are properly filled"""
        # Create a file with a gap
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0, 1000],  # 2021-01-01 00:00:00
            [1609459380, 107.0, 110.0, 106.0, 109.0, 1100],  # 2021-01-01 00:03:00 (gap from 00:01 to 00:02)
        ])
        
        # Fill the gap in the range 00:00:00 to 00:03:00
        success = self.file_manager.fill_gaps_in_range(self.test_symbol, 1609459200, 1609459380)
        
        self.assertTrue(success)
        
        # Check the file now has no gaps in that range
        gaps = self.file_manager.detect_missing_ranges(file_path)
        self.assertEqual(len(gaps), 0)
    
    def test_get_file_index(self):
        """Test that file index is correctly generated"""
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0, 1000],  # 2021-01-01 00:00:00
            [1609459260, 104.0, 108.0, 103.0, 107.0, 1200],  # 2021-01-01 00:01:00
        ])
        
        index = self.file_manager.get_file_index(self.test_symbol)
        
        self.assertIsNotNone(index)
        self.assertEqual(index.earliest_timestamp, 1609459200)
        self.assertEqual(index.latest_timestamp, 1609459260)
        self.assertEqual(index.row_count, 2)
    
    def test_validate_continuous_range(self):
        """Test that continuous range validation works"""
        file_path = self.create_test_csv(self.test_symbol, [
            [1609459200, 100.0, 105.0, 99.0, 104.0, 1000],  # 2021-01-01 00:00:00
            [1609459260, 104.0, 108.0, 103.0, 107.0, 1200],  # 2021-01-01 00:01:00
        ])
        
        # This range should be continuous
        is_continuous = self.file_manager.validate_continuous_range(self.test_symbol, 1609459200, 1609459260)
        self.assertTrue(is_continuous)
        
        # This range should not be continuous (has gap)
        is_continuous = self.file_manager.validate_continuous_range(self.test_symbol, 1609459200, 1609459380)
        self.assertFalse(is_continuous)


if __name__ == '__main__':
    unittest.main()