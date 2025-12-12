"""
Sync loop as application service for the Downloader/Sync Engine.

Handles periodic scheduling and cycle orchestration.
"""
import asyncio
import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
import signal

from application.configs.sync_settings import settings
from application.data_sync.sync_manager import SyncManager
from application.configs.symbol_config import get_symbols
from utils.logger import logger


class SyncLoop:
    """Manages the periodic sync cycles - application service"""
    
    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.running = True
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def run_continuous_sync(self):
        """Run the continuous sync loop"""
        print("Starting continuous sync loop...")
        
        cycle_count = 0
        while self.running:
            try:
                cycle_count += 1
                print(f"Starting sync cycle #{cycle_count}")
                
                start_time = datetime.utcnow()
                
                # Run the sync cycle using the sync manager
                result = await self.sync_manager.run_sync_cycle()
                
                # Save cycle report to reports directory
                cycle_report = {
                    "cycle_start": start_time.isoformat(),
                    "cycle_end": datetime.utcnow().isoformat(),
                    "cycle_number": cycle_count,
                    "symbols_scanned": result['symbols_scanned'],
                    "symbols_fixed": result['symbols_fixed'],
                    "rows_written": result['rows_written'],
                    "bytes_written": result['bytes_written'],
                    "errors": result['errors'],
                    "duration_ms": result['duration_ms']
                }
                
                # Create reports directory if it doesn't exist
                reports_dir = os.path.join(settings.data_dir, "..", "reports")
                os.makedirs(reports_dir, exist_ok=True)
                
                # Save report file
                report_filename = f"cycle-{start_time.strftime('%Y%m%d-%H%M%S')}.json"
                report_path = os.path.join(reports_dir, report_filename)
                
                with open(report_path, 'w') as f:
                    json.dump(cycle_report, f, indent=2)
                
                print(f"Cycle #{cycle_count} completed. Report saved to {report_path}")
                
                # Wait for the next cycle if still running
                if self.running:
                    print(f"Waiting {settings.sync_interval_seconds} seconds until next cycle...")
                    await asyncio.sleep(settings.sync_interval_seconds)
                
            except Exception as e:
                print(f"Error in sync cycle: {e}")
                import traceback
                traceback.print_exc()
                # Continue to next cycle even if one fails
        
        print("Sync loop stopped.")
    
    async def run_single_cycle(self, symbol: Optional[str] = None):
        """Run a single sync cycle for testing or specific symbol"""
        print(f"Running single sync cycle{' for ' + symbol if symbol else ''}...")
        
        symbols = None
        if symbol:
            symbols = [symbol]
        
        start_time = datetime.utcnow()
        
        # Run the sync cycle using the sync manager
        result = await self.sync_manager.run_sync_cycle(symbols)
        
        # Log the results
        print(f"Single cycle completed:")
        print(f"  Symbols scanned: {result['symbols_scanned']}")
        print(f"  Symbols fixed: {result['symbols_fixed']}")
        print(f"  Rows written: {result['rows_written']}")
        print(f"  Bytes written: {result['bytes_written']}")
        print(f"  Duration: {result['duration_ms']}ms")
        print(f"  Errors: {len(result['errors'])}")
        
        if result['errors']:
            print("Errors:")
            for error in result['errors']:
                print(f"    {error}")
        
        # Save cycle report
        cycle_report = {
            "cycle_start": start_time.isoformat(),
            "cycle_end": datetime.utcnow().isoformat(),
            "cycle_type": "single",
            "symbols_scanned": result['symbols_scanned'],
            "symbols_fixed": result['symbols_fixed'],
            "rows_written": result['rows_written'],
            "bytes_written": result['bytes_written'],
            "errors": result['errors'],
            "duration_ms": result['duration_ms']
        }
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(settings.data_dir, "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save report file
        report_filename = f"cycle-single-{start_time.strftime('%Y%m%d-%H%M%S')}.json"
        report_path = os.path.join(reports_dir, report_filename)
        
        with open(report_path, 'w') as f:
            json.dump(cycle_report, f, indent=2)
        
        print(f"Report saved to {report_path}")
        
        return result


async def run_with_resources(args):
    """Run the sync loop with proper resource management"""
    from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
    from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter

    file_repo = FileRepositoryAdapter()
    data_downloader = DataDownloaderAdapter()
    sync_manager = SyncManager(file_repo, data_downloader)
    loop = SyncLoop(sync_manager)

    # Use context manager for proper resource cleanup
    async with data_downloader:
        if args.one_cycle:
            await loop.run_single_cycle(args.symbol)
        else:
            await loop.run_continuous_sync()


def main():
    """Main entry point for the sync loop"""
    parser = argparse.ArgumentParser(description='Run the sync loop')
    parser.add_argument('--one-cycle', action='store_true',
                        help='Run a single sync cycle and exit')
    parser.add_argument('--symbol', type=str,
                        help='Specific symbol to sync (e.g. BTC-USDT)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run in dry-run mode (not implemented in this version)')

    args = parser.parse_args()

    # Run with proper resource management
    asyncio.run(run_with_resources(args))


if __name__ == "__main__":
    main()