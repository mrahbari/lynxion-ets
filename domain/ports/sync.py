"""
Domain ports for the sync system.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from domain.sync.entities import SymbolSyncConfig, SyncJob, GapRange, FileIndex, SyncCycleReport


class SymbolConfigRepository(ABC):
    """Port for accessing symbol configuration"""
    
    @abstractmethod
    def get_symbols(self) -> List[SymbolSyncConfig]:
        """Get all configured symbols"""
        pass
    
    @abstractmethod
    def get_symbol_config(self, symbol: str) -> Optional[SymbolSyncConfig]:
        """Get configuration for a specific symbol"""
        pass


class FileRepository(ABC):
    """Port for file operations"""
    
    @abstractmethod
    def validate_csv_schema(self, file_path: str) -> bool:
        """Validate CSV schema"""
        pass
    
    @abstractmethod
    def detect_missing_ranges(self, file_path: str, start_time: Optional[int] = None, 
                              end_time: Optional[int] = None) -> List[GapRange]:
        """Detect missing ranges in a file"""
        pass
    
    @abstractmethod
    def read_csv_rows(self, file_path: str) -> List[List[str]]:
        """Read CSV rows from a file"""
        pass
    
    @abstractmethod
    def write_csv_rows(self, file_path: str, rows: List[List[str]]) -> None:
        """Write CSV rows to a file"""
        pass
    
    @abstractmethod
    def get_file_index(self, symbol: str) -> Optional[FileIndex]:
        """Get file index information"""
        pass
    
    @abstractmethod
    def fill_gaps_in_range(self, symbol: str, start_ts: int, end_ts: int, 
                          fill_strategy: str = "forward_fill") -> bool:
        """Fill gaps in a specific range"""
        pass
    
    @abstractmethod
    def compact_and_aggregate(self, symbol: str, cleanup_old: bool = True) -> None:
        """Compact and aggregate data"""
        pass
    
    @abstractmethod
    def validate_continuous_range(self, symbol: str, start_ts: int, end_ts: int) -> bool:
        """Validate if a range is continuous"""
        pass


class DataDownloader(ABC):
    """Port for downloading data from exchanges"""
    
    @abstractmethod
    async def fetch_range(self, symbol: str, start_ts: int, end_ts: int, exchange: Optional[str] = None) -> List[dict]:
        """Fetch OHLCV data for a symbol in a given time range"""
        pass