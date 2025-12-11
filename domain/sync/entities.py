"""
Domain entities for the sync system.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SymbolSyncConfig:
    """Domain entity representing sync configuration for a symbol"""
    symbol: str
    exchange: str = "bingx"
    max_api_window_minutes: int = 1440
    rate_limit_requests_per_minute: int = 10
    enabled: bool = True
    priority: int = 1


@dataclass
class SyncJob:
    """Domain entity representing a synchronization job"""
    symbol: str
    start_ts: int
    end_ts: int
    priority: int = 1
    is_priority_repair: bool = False


@dataclass
class GapRange:
    """Domain entity representing a gap in data"""
    start: int
    end: int


@dataclass
class FileIndex:
    """Domain entity representing file indexing information"""
    earliest_timestamp: Optional[int] = None
    latest_timestamp: Optional[int] = None
    row_count: int = 0
    file_size: int = 0


@dataclass
class SyncCycleReport:
    """Domain entity representing a sync cycle report"""
    cycle_start: datetime
    cycle_end: datetime
    symbols_scanned: int
    symbols_fixed: int
    rows_written: int
    bytes_written: int
    errors: list
    duration_ms: int