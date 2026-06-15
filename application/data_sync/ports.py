"""
Application layer ports for the sync system.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from domain.sync.entities import SyncJob


class FileRepository(ABC):
    """Port for file operations"""
    
    @abstractmethod
    def get_raw_file_path(self, symbol: str) -> str:
        """Get the path for a raw data file for a symbol"""
        pass
    
    @abstractmethod
    def get_index_file_path(self, symbol: str) -> str:
        """Get the path for an index file for a symbol"""
        pass
    
    @abstractmethod
    def get_processed_file_path(self, symbol: str, timeframe: str) -> str:
        """Get the path for a processed data file for a symbol and timeframe"""
        pass
    
    @abstractmethod
    def validate_csv_schema(self, file_path: str) -> bool:
        """Validate that a CSV file has the correct schema"""
        pass
    
    @abstractmethod
    def read_csv_rows(self, file_path: str) -> List[List[str]]:
        """Read all rows from a CSV file"""
        pass
    
    @abstractmethod
    def write_csv_rows(self, file_path: str, rows: List[List[str]]) -> None:
        """Write rows to a CSV file atomically"""
        pass
    
    @abstractmethod
    def detect_missing_ranges(self, file_path: str, start_time: int = None, end_time: int = None) -> List[Tuple[int, int]]:
        """Detect missing ranges in a CSV file"""
        pass
    
    @abstractmethod
    def merge_sorted_rows(self, existing_rows: List[List[str]], new_rows: List[List[str]]) -> List[List[str]]:
        """Merge two sets of sorted CSV rows, eliminating duplicates and maintaining order"""
        pass
    
    @abstractmethod
    def get_file_index(self, symbol: str) -> dict:
        """Get the index information for a symbol's data file"""
        pass
    
    @abstractmethod
    def fill_gaps_in_range(self, symbol: str, start_ts: int, end_ts: int, fill_strategy: str = "forward_fill") -> bool:
        """Fill gaps in a specific range for a symbol"""
        pass
    
    @abstractmethod
    def compact_and_aggregate(self, symbol: str, cleanup_old: bool = True) -> bool:
        """Generate processed (aggregated) files from raw data and optionally clean up old files"""
        pass
    
    @abstractmethod
    def validate_continuous_range(self, symbol: str, start_ts: int, end_ts: int) -> bool:
        """Check if a range is continuous (has no gaps) in a symbol's data file"""
        pass