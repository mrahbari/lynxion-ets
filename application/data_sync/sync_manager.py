"""
Sync manager as application use case for the Downloader/Sync Engine.

Handles per-symbol orchestration, job queuing, and prioritization.
"""
import asyncio
import threading
import time
import os
from typing import Dict, List, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from application.configs.sync_settings import settings
from application.configs.symbol_config import get_symbols
from domain.sync.entities import SyncJob
from application.data_sync.ports import FileRepository
from domain.ports.sync import DataDownloader
from shared.sync_logger import logger, OperationType, StatusType


class PriorityJobQueue:
    """Priority queue for sync jobs"""

    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()

    def push(self, job: SyncJob) -> None:
        """Add a job to the queue, maintaining priority order"""
        with self._lock:
            self._queue.append(job)
            # Sort by priority (higher numbers = higher priority) and then by timestamp
            self._queue.sort(key=lambda x: (-x.priority, x.start_ts))

    def pop(self) -> Optional[SyncJob]:
        """Get the highest priority job from the queue"""
        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)

    def is_empty(self) -> bool:
        """Check if the queue is empty"""
        with self._lock:
            return len(self._queue) == 0


class SyncManager:
    """Manages synchronization jobs for all symbols - application use case"""

    def __init__(self, file_repo: FileRepository, data_downloader: DataDownloader):
        self.file_repo = file_repo
        self.data_downloader = data_downloader
        self.symbol_locks: Dict[str, asyncio.Lock] = {}
        self.job_queue = PriorityJobQueue()
        self.executor = ThreadPoolExecutor(max_workers=settings.download_threadpool_workers)
        self.completed_jobs: Set[Tuple[str, int, int]] = set()  # Track completed ranges

    def get_symbol_lock(self, symbol: str) -> asyncio.Lock:
        """Get or create a lock for a specific symbol"""
        if symbol not in self.symbol_locks:
            self.symbol_locks[symbol] = asyncio.Lock()
        return self.symbol_locks[symbol]

    async def add_symbol_to_queue(self, symbol: str, priority_repair: bool = False) -> None:
        """Add a symbol to the sync queue by detecting missing ranges"""
        # Get raw file path using the file repository
        file_path = self.file_repo.get_raw_file_path(symbol)

        # First check if file exists and get its index information
        index_info = self.file_repo.get_file_index(symbol)

        # Get existing gaps in the file
        gaps_data = self.file_repo.detect_missing_ranges(file_path)

        # Convert to domain GapRange objects if needed, or work with the format as is
        gaps = []
        if gaps_data:  # Check if gaps_data is not empty
            gaps = [{'start': gap[0], 'end': gap[1]} for gap in gaps_data] if isinstance(gaps_data[0], tuple) else gaps_data

        # Check if we need to add a range for recent data (from file end to now)
        import time
        current_time = int(time.time())

        # Round down to nearest minute
        current_time = (current_time // 60) * 60

        # Check if file should be updated with newer data
        if index_info and 'latest_timestamp' in index_info:
            latest_ts = index_info['latest_timestamp']
            # If latest data is older than a few minutes, add range for recent data
            if current_time - latest_ts > 60 * 2:  # More than 2 minutes old
                # Add a job for the recent data range
                recent_gap = {
                    'start': latest_ts + 60,  # Next minute after latest
                    'end': current_time
                }
                gaps.append(recent_gap)
        elif not index_info or not os.path.exists(file_path):
            # If no file exists, sync a longer historical range (last 30 days)
            # This ensures we have sufficient historical data for analysis
            start_range = current_time - (30 * 24 * 60 * 60)  # 30 days ago
            initial_gap = {
                'start': start_range,
                'end': current_time
            }
            gaps.append(initial_gap)

        if not gaps:
            # If no gaps, mark as complete for this cycle
            return

        # Add each gap as a job to the queue
        for gap in gaps:
            priority = 1
            if priority_repair:
                priority = 10  # Higher priority for repair jobs

            job = SyncJob(
                symbol=symbol,
                start_ts=gap['start'] if isinstance(gap, dict) else gap[0],
                end_ts=gap['end'] if isinstance(gap, dict) else gap[1],
                priority=priority,
                is_priority_repair=priority_repair
            )
            self.job_queue.push(job)

    async def process_single_job(self, job: SyncJob) -> Dict[str, any]:
        """Process a single sync job"""
        symbol_lock = self.get_symbol_lock(job.symbol)
        start_time = time.time()

        async with symbol_lock:
            try:
                # Fetch the data using the downloader port
                data = await self.data_downloader.fetch_range(job.symbol, job.start_ts, job.end_ts)

                if not data:
                    # No data returned, log and continue
                    logger.log_operation(
                        operation=OperationType.SYMBOL_DOWNLOAD,
                        symbol=job.symbol,
                        status=StatusType.PARTIAL,
                        fixed_ranges=[[job.start_ts, job.end_ts]],
                        duration_ms=int((time.time() - start_time) * 1000),
                        error="No data returned from exchange"
                    )
                    return {
                        'success': False,
                        'error': 'No data returned from exchange',
                        'rows_written': 0,
                        'bytes_written': 0
                    }

                # Format data as CSV rows
                csv_rows = [['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                for entry in data:
                    csv_rows.append([
                        str(int(entry['timestamp'])),
                        str(entry['open']),
                        str(entry['high']),
                        str(entry['low']),
                        str(entry['close']),
                        str(entry['volume'])
                    ])

                # Read existing file data
                existing_file_path = self.file_repo.get_raw_file_path(job.symbol)
                existing_rows = []
                if self.file_repo.validate_csv_schema(existing_file_path):
                    existing_rows = self.file_repo.read_csv_rows(existing_file_path)

                # Merge with existing data using the file repository
                merged_rows = self.file_repo.merge_sorted_rows(existing_rows, csv_rows)

                # Write merged data using the file repository
                self.file_repo.write_csv_rows(existing_file_path, merged_rows)

                # Calculate statistics
                rows_written = len(data)
                bytes_written = sum(len(','.join(row)) for row in data) if data else 0

                duration_ms = int((time.time() - start_time) * 1000)

                # Log successful completion
                logger.log_operation(
                    operation=OperationType.SYMBOL_DOWNLOAD,
                    symbol=job.symbol,
                    status=StatusType.OK,
                    fixed_ranges=[[job.start_ts, job.end_ts]],
                    duration_ms=duration_ms,
                    rows_written=rows_written,
                    bytes_written=bytes_written
                )

                return {
                    'success': True,
                    'rows_written': rows_written,
                    'bytes_written': bytes_written
                }

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                logger.log_operation(
                    operation=OperationType.SYMBOL_DOWNLOAD,
                    symbol=job.symbol,
                    status=StatusType.ERROR,
                    fixed_ranges=[[job.start_ts, job.end_ts]],
                    duration_ms=duration_ms,
                    error=str(e)
                )

                return {
                    'success': False,
                    'error': str(e),
                    'rows_written': 0,
                    'bytes_written': 0
                }

    async def run_sync_cycle(self, symbols: Optional[List[str]] = None) -> Dict[str, any]:
        """Run a complete sync cycle for specified symbols or all configured symbols"""
        if symbols is None:
            symbols = [sym.symbol for sym in get_symbols() if sym.enabled]

        start_time = time.time()
        symbols_scanned = 0
        symbols_fixed = 0
        total_rows_written = 0
        total_bytes_written = 0
        cycle_errors = []

        # Add all symbols to the job queue
        for symbol in symbols:
            await self.add_symbol_to_queue(symbol)
            symbols_scanned += 1

        # Process all jobs in the queue with controlled concurrency
        semaphore = asyncio.Semaphore(settings.async_concurrency)

        async def process_job_with_semaphore(job: SyncJob):
            async with semaphore:
                return await self.process_single_job(job)

        # Collect all jobs to process
        jobs_to_process = []
        while not self.job_queue.is_empty():
            job = self.job_queue.pop()
            if job:
                jobs_to_process.append(job)

        # Process jobs concurrently
        tasks = [process_job_with_semaphore(job) for job in jobs_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle exception from gather
                cycle_errors.append({
                    'symbol': jobs_to_process[i].symbol,
                    'error': str(result),
                    'attempts': settings.retry_max_attempts
                })
            else:
                # Normal result
                job = jobs_to_process[i]
                if result['success']:
                    symbols_fixed += 1
                    total_rows_written += result.get('rows_written', 0)
                    total_bytes_written += result.get('bytes_written', 0)
                else:
                    cycle_errors.append({
                        'symbol': job.symbol,
                        'error': result.get('error', 'Unknown error'),
                        'attempts': settings.retry_max_attempts
                    })

        # Run compaction/retention after sync
        for symbol in symbols:
            try:
                self.file_repo.compact_and_aggregate(symbol, cleanup_old=True)
            except Exception as e:
                cycle_errors.append({
                    'symbol': symbol,
                    'error': f'Compaction error: {str(e)}',
                    'type': 'compaction'
                })

        duration_ms = int((time.time() - start_time) * 1000)

        # Log cycle report
        logger.log_cycle_report(
            cycle_start=datetime.fromtimestamp(start_time),
            cycle_end=datetime.fromtimestamp(time.time()),
            symbols_scanned=symbols_scanned,
            symbols_fixed=symbols_fixed,
            rows_written=total_rows_written,
            bytes_written=total_bytes_written,
            errors=cycle_errors
        )

        return {
            'symbols_scanned': symbols_scanned,
            'symbols_fixed': symbols_fixed,
            'rows_written': total_rows_written,
            'bytes_written': total_bytes_written,
            'errors': cycle_errors,
            'duration_ms': duration_ms
        }

    async def sync_symbol_data(self, symbol: str, timeframes: List[str], start_time: int, end_time: int, exchange: Optional[str] = None) -> Dict[str, any]:
        """Synchronize data for a specific symbol and timeframes within the given time range"""
        # Get raw file path using the file repository
        file_path = self.file_repo.get_raw_file_path(symbol)

        # First, download the data for the specified time range
        try:
            # Pass exchange information if provided
            if exchange:
                data = await self.data_downloader.fetch_range(symbol, start_time, end_time, exchange)
            else:
                data = await self.data_downloader.fetch_range(symbol, start_time, end_time)

            if not data:
                # No data returned, return with appropriate structure
                return {
                    'success': False,
                    'error': 'No data returned from exchange',
                    'rows_written': 0,
                    'message': f'No data available for {symbol} in range {start_time} to {end_time}'
                }

            # Count the original data length before processing
            original_data_length = len(data)

            # Format data as CSV rows
            csv_rows = [['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            for entry in data:
                csv_rows.append([
                    str(int(entry['timestamp'])),
                    str(entry['open']),
                    str(entry['high']),
                    str(entry['low']),
                    str(entry['close']),
                    str(entry['volume'])
                ])

            # Read existing file data
            existing_rows = []
            if self.file_repo.validate_csv_schema(file_path):
                existing_rows = self.file_repo.read_csv_rows(file_path)

            # Merge with existing data using the file repository
            merged_rows = self.file_repo.merge_sorted_rows(existing_rows, csv_rows)

            # Write merged data using the file repository
            self.file_repo.write_csv_rows(file_path, merged_rows)

            # Generate compacted/aggregated files for specified timeframes
            # Note: compact_and_aggregate generates ALL timeframes, so we call it once
            try:
                self.file_repo.compact_and_aggregate(symbol, cleanup_old=False)
            except Exception as e:
                logger.error(f"Error generating aggregations for {symbol}: {e}")

            # Return the original number of rows downloaded
            rows_written = original_data_length

            return {
                'success': True,
                'rows_written': rows_written,
                'message': f'Successfully synchronized {rows_written} rows for {symbol}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'rows_written': 0,
                'message': f'Error syncing data for {symbol}: {str(e)}'
            }

    async def request_priority_repair(self, symbol: str, start_ts: int, end_ts: int) -> bool:
        """Request a priority repair for a specific symbol and time range"""
        # Add to job queue with high priority
        job = SyncJob(
            symbol=symbol,
            start_ts=start_ts,
            end_ts=end_ts,
            priority=20,  # Higher than normal jobs
            is_priority_repair=True
        )
        self.job_queue.push(job)

        # Also try to fill gaps in the range immediately
        success = self.file_repo.fill_gaps_in_range(symbol, start_ts, end_ts)
        return success