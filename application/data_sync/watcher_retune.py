"""
Watcher retune as application use case for the Downloader/Sync Engine.

Provides on-demand validation and priority repair functionality for strategies/watchers.
"""
import asyncio
import time
import argparse
from typing import Optional
from datetime import datetime

from application.configs.sync_settings import settings
from application.data_sync.ports import FileRepository
from domain.ports.sync import DataDownloader
from application.data_sync.sync_manager import SyncManager
from utils.logger import logger, OperationType, StatusType


class WatcherRetuneUseCase:
    """Application use case for watcher retune functionality"""
    
    def __init__(self, file_repo: FileRepository, data_downloader: DataDownloader, sync_manager: SyncManager):
        self.file_repo = file_repo
        self.data_downloader = data_downloader
        self.sync_manager = sync_manager
    
    def request_repair_sync(self, symbol: str, start_ts: int, end_ts: int, timeout: int = 300) -> bool:
        """
        Synchronous request for priority repair of a symbol and interval.

        Args:
            symbol: The symbol to repair
            start_ts: Start timestamp of the interval
            end_ts: End timestamp of the interval
            timeout: Maximum time to wait for repair in seconds (default 300 = 5 minutes)

        Returns:
            True when the requested interval is confirmed gap-free, False if timeout
        """
        import time
        from domain.sync.entities import SyncJob

        # Start time for timeout tracking
        start_time = time.time()

        # Log the repair request
        logger.log_operation(
            operation=OperationType.WATCHER_REPAIR,
            symbol=symbol,
            status=StatusType.OK,
            duration_ms=0,
            fixed_ranges=[[start_ts, end_ts]],
            description="Priority repair requested"
        )

        # Replicate the async logic directly in sync form
        # Add to job queue with high priority (replicating request_priority_repair logic)
        job = SyncJob(
            symbol=symbol,
            start_ts=start_ts,
            end_ts=end_ts,
            priority=20,  # Higher than normal jobs
            is_priority_repair=True
        )
        self.sync_manager.job_queue.push(job)

        # Also try to fill gaps in the range immediately
        success = self.file_repo.fill_gaps_in_range(symbol, start_ts, end_ts)

        if not success:
            # If immediate fill didn't work, queue for full repair (replicating add_symbol_to_queue logic)
            # Create a job for the symbol with normal priority
            symbol_job = SyncJob(
                symbol=symbol,
                start_ts=start_ts,
                end_ts=end_ts,
                priority=10,  # Normal priority
                is_priority_repair=False
            )
            self.sync_manager.job_queue.push(symbol_job)

        # Wait until the requested interval is gap-free (with timeout)
        while time.time() - start_time < timeout:
            # Check if the range is now continuous
            is_continuous = self.file_repo.validate_continuous_range(symbol, start_ts, end_ts)

            if is_continuous:
                duration_ms = int((time.time() - start_time) * 1000)

                logger.log_operation(
                    operation=OperationType.WATCHER_REPAIR,
                    symbol=symbol,
                    status=StatusType.OK,
                    duration_ms=duration_ms,
                    fixed_ranges=[[start_ts, end_ts]],
                    description="Priority repair completed successfully"
                )

                return True

            # Wait a bit before checking again
            time.sleep(1)

        # If we get here, we timed out
        duration_ms = int((time.time() - start_time) * 1000)

        logger.log_operation(
            operation=OperationType.WATCHER_REPAIR,
            symbol=symbol,
            status=StatusType.ERROR,
            duration_ms=duration_ms,
            fixed_ranges=[[start_ts, end_ts]],
            error="Timeout waiting for gap-free data after priority repair request"
        )

        return False
    
    async def request_repair_async(self, symbol: str, start_ts: int, end_ts: int, timeout: int = 300) -> bool:
        """
        Asynchronous request for priority repair of a symbol and interval.
        
        Args:
            symbol: The symbol to repair
            start_ts: Start timestamp of the interval
            end_ts: End timestamp of the interval
            timeout: Maximum time to wait for repair in seconds (default 300 = 5 minutes)
            
        Returns:
            True when the requested interval is confirmed gap-free, False if timeout
        """
        start_time = time.time()
        
        # Log the repair request
        logger.log_operation(
            operation=OperationType.WATCHER_REPAIR,
            symbol=symbol,
            status=StatusType.OK,
            duration_ms=0,
            fixed_ranges=[[start_ts, end_ts]],
            description="Priority repair requested"
        )
        
        # Add to priority queue via sync manager
        success = await self.sync_manager.request_priority_repair(symbol, start_ts, end_ts)
        
        if not success:
            # If immediate fill didn't work, queue for full repair
            await self.sync_manager.add_symbol_to_queue(symbol, priority_repair=True)
        
        # Wait until the requested interval is gap-free (with timeout)
        while time.time() - start_time < timeout:
            # Check if the range is now continuous
            is_continuous = self.file_repo.validate_continuous_range(symbol, start_ts, end_ts)
            
            if is_continuous:
                duration_ms = int((time.time() - start_time) * 1000)
                
                logger.log_operation(
                    operation=OperationType.WATCHER_REPAIR,
                    symbol=symbol,
                    status=StatusType.OK,
                    duration_ms=duration_ms,
                    fixed_ranges=[[start_ts, end_ts]],
                    description="Priority repair completed successfully"
                )
                
                return True
            
            # Wait a bit before checking again
            await asyncio.sleep(1)
        
        # If we get here, we timed out
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.log_operation(
            operation=OperationType.WATCHER_REPAIR,
            symbol=symbol,
            status=StatusType.ERROR,
            duration_ms=duration_ms,
            fixed_ranges=[[start_ts, end_ts]],
            error="Timeout waiting for gap-free data after priority repair request"
        )
        
        return False
    
    def validate_interval(self, symbol: str, start_ts: int, end_ts: int) -> bool:
        """
        Validate that a specific interval is gap-free without performing repair.
        
        Args:
            symbol: The symbol to validate
            start_ts: Start timestamp of the interval
            end_ts: End timestamp of the interval
            
        Returns:
            True if the interval is gap-free, False otherwise
        """
        return self.file_repo.validate_continuous_range(symbol, start_ts, end_ts)
    
    async def force_repair_range(self, symbol: str, start_ts: int, end_ts: int, max_gap_fill_minutes: Optional[int] = None) -> bool:
        """
        Force repair a range by detecting gaps and filling them if possible.
        
        Args:
            symbol: The symbol to repair
            start_ts: Start timestamp of the range
            end_ts: End timestamp of the range
            max_gap_fill_minutes: Max gap size to auto-fill (defaults to settings)
            
        Returns:
            True if repair was successful, False otherwise
        """
        if max_gap_fill_minutes is None:
            max_gap_fill_minutes = settings.max_gap_fill_minutes
        
        gap_size = end_ts - start_ts
        max_gap_seconds = max_gap_fill_minutes * 60
        
        # Check if the gap is too large to auto-fill
        if gap_size > max_gap_seconds:
            # For large gaps, we need to download actual data rather than fill
            # Add to priority queue for proper repair
            await self.sync_manager.request_priority_repair(symbol, start_ts, end_ts)
            return False
        
        # For smaller gaps, attempt to fill
        success = self.file_repo.fill_gaps_in_range(symbol, start_ts, end_ts)
        return success


def main():
    """Main entry point for the watcher retune command line tool"""
    parser = argparse.ArgumentParser(description='Run watcher retune operations')
    parser.add_argument('--symbol', type=str, required=True,
                        help='Symbol to repair (e.g. BTC-USDT)')
    parser.add_argument('--from', dest='start_ts', type=int, required=True,
                        help='Start timestamp for the repair interval')
    parser.add_argument('--to', dest='end_ts', type=int, required=True,
                        help='End timestamp for the repair interval')
    parser.add_argument('--timeout', type=int, default=300,
                        help='Maximum time to wait in seconds (default: 300)')
    
    args = parser.parse_args()
    
    print(f"Requesting priority repair for {args.symbol} from {args.start_ts} to {args.end_ts}")
    
    # Create dependencies (in a real system, this would use DI)
    from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
    from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter
    from application.data_sync.sync_manager import SyncManager
    
    file_repo = FileRepositoryAdapter()
    data_downloader = DataDownloaderAdapter()
    sync_manager = SyncManager(file_repo, data_downloader)
    watcher_retune = WatcherRetuneUseCase(file_repo, data_downloader, sync_manager)
    
    # Use the synchronous method
    success = watcher_retune.request_repair_sync(
        args.symbol, 
        args.start_ts, 
        args.end_ts, 
        args.timeout
    )
    
    if success:
        print("Repair completed successfully - data is now gap-free!")
        return 0
    else:
        print("Repair timed out - data may still have gaps.")
        return 1


if __name__ == "__main__":
    exit(main())