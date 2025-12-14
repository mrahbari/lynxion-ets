"""
Structured JSON logger for the Downloader/Sync Engine.

Implements structured logging with JSON format as required by the specification.
"""
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from enum import Enum


class OperationType(str, Enum):
    CYCLE = "cycle"
    SYMBOL_DOWNLOAD = "symbol_download"
    WATCHER_REPAIR = "watcher_repair"


class StatusType(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    ERROR = "error"


class SyncLogger:
    """Structured JSON logger for sync operations"""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the logger
        
        Args:
            log_file: Optional file path to write logs to (default: stdout)
        """
        self.log_file = log_file
    
    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """Write a log entry in JSON format"""
        # Ensure timestamp is ISO format
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        json_line = json.dumps(log_entry)
        
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json_line + '\n')
        else:
            print(json_line, flush=True)
    
    def log_operation(
        self,
        operation: Union[OperationType, str],
        symbol: Optional[str] = None,
        status: Union[StatusType, str] = StatusType.OK,
        fixed_ranges: Optional[list] = None,
        api_usage: Optional[Dict[str, int]] = None,
        duration_ms: Optional[int] = None,
        rows_written: Optional[int] = None,
        bytes_written: Optional[int] = None,
        error: Optional[Union[Exception, str, Dict[str, str]]] = None,
        **kwargs
    ) -> None:
        """
        Log an operation with structured JSON format
        
        Args:
            operation: Type of operation (cycle, symbol_download, watcher_repair)
            symbol: Symbol being operated on (optional)
            status: Status of the operation (ok, partial, error)
            fixed_ranges: List of [start_ts, end_ts] intervals that were fixed
            api_usage: Dictionary with API usage stats (requests, rate_limit_events)
            duration_ms: Duration of operation in milliseconds
            rows_written: Number of rows written
            bytes_written: Number of bytes written
            error: Error object, message, or dict with message/backtrace
            **kwargs: Additional fields to include in the log
        """
        log_entry = {
            "operation": str(operation),
            "status": str(status),
        }
        
        if symbol:
            log_entry["symbol"] = symbol
            
        if fixed_ranges is not None:
            log_entry["fixed_ranges"] = fixed_ranges
            
        if api_usage is not None:
            log_entry["api_usage"] = api_usage
            
        if duration_ms is not None:
            log_entry["duration_ms"] = duration_ms
            
        if rows_written is not None:
            log_entry["rows_written"] = rows_written
            
        if bytes_written is not None:
            log_entry["bytes_written"] = bytes_written
            
        if error:
            if isinstance(error, Exception):
                log_entry["error"] = {
                    "message": str(error),
                    "backtrace": traceback.format_exc()
                }
            elif isinstance(error, str):
                log_entry["error"] = {
                    "message": error,
                    "backtrace": ""
                }
            elif isinstance(error, dict):
                log_entry["error"] = error
            else:
                log_entry["error"] = {
                    "message": str(error),
                    "backtrace": ""
                }
        
        # Add any additional fields
        log_entry.update(kwargs)
        
        self._write_log(log_entry)
    
    def log_cycle_report(
        self,
        cycle_start: datetime,
        cycle_end: datetime,
        symbols_scanned: int,
        symbols_fixed: int,
        rows_written: int,
        bytes_written: int,
        errors: Optional[list] = None
    ) -> None:
        """
        Log a cycle report
        
        Args:
            cycle_start: Start time of the cycle
            cycle_end: End time of the cycle
            symbols_scanned: Number of symbols scanned
            symbols_fixed: Number of symbols fixed
            rows_written: Total rows written in the cycle
            bytes_written: Total bytes written in the cycle
            errors: List of errors during the cycle
        """
        log_entry = {
            "operation": OperationType.CYCLE,
            "cycle_start": cycle_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cycle_end": cycle_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "symbols_scanned": symbols_scanned,
            "symbols_fixed": symbols_fixed,
            "rows_written": rows_written,
            "bytes_written": bytes_written,
            "errors": errors or []
        }
        
        self._write_log(log_entry)
    
    def log_symbol_sync(
        self,
        symbol: str,
        success: bool,
        fixed_ranges: Optional[list] = None,
        duration_ms: Optional[int] = None,
        rows_written: Optional[int] = None,
        bytes_written: Optional[int] = None,
        error: Optional[Union[Exception, str]] = None
    ) -> None:
        """
        Log a symbol synchronization event
        
        Args:
            symbol: Symbol being synced
            success: Whether the sync was successful
            fixed_ranges: Ranges that were fixed
            duration_ms: Duration of sync in milliseconds
            rows_written: Number of rows written
            bytes_written: Number of bytes written
            error: Error if any occurred
        """
        self.log_operation(
            operation=OperationType.SYMBOL_DOWNLOAD,
            symbol=symbol,
            status=StatusType.OK if success else StatusType.ERROR,
            fixed_ranges=fixed_ranges,
            duration_ms=duration_ms,
            rows_written=rows_written,
            bytes_written=bytes_written,
            error=error
        )


# Global logger instance
logger = SyncLogger(log_file="logs/sync.log")