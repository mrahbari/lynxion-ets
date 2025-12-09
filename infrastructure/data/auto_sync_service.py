"""
Automatic sync service for WFO Downloader System.
Handles scheduled full refresh and incremental updates.
Also integrates with RETUNE functionality.
"""
import time
import schedule
import threading
from datetime import datetime
from shared.logger import logger
from infrastructure.data.wfo_config import config
from infrastructure.data.data_sync_engine import DataSyncEngine
from infrastructure.data.binance_client import BinanceClient
from infrastructure.data.candle_store import CandleStore
from infrastructure.data.resample_engine import ResampleEngine


class AutoSyncService:
    """Automatic synchronization service for WFO Downloader"""

    def __init__(self):
        self.config = config
        self.client = BinanceClient(
            retry=self.config.get_api_settings()['retry_attempts'],
            sleep=self.config.get_api_settings()['rate_limit_delay']
        )
        self.store = CandleStore(root=self.config.get_data_paths()['raw_dir'])
        self.resample_engine = ResampleEngine(
            raw_root=self.config.get_data_paths()['raw_dir'],
            out_root=self.config.get_data_paths()['processed_dir']
        )
        self.sync_engine = DataSyncEngine(
            symbols=self.config.get_coins(),
            client=self.client,
            store=self.store
        )
        self.is_running = False
        self.sync_thread = None

        # RETUNE integration
        self.retune_settings = self.config.get_retune_settings()

        logger.info(f"AutoSyncService initialized with {len(self.config.get_coins())} coins")
        logger.info(f"Sync interval: {self.config.get_sync_settings()['refresh_interval_hours']} hours")
        logger.info(f"Retune enabled: {self.retune_settings['enabled']}, interval: {self.retune_settings['interval_hours']} hours")

    def start_auto_sync(self):
        """Start the automatic sync service"""
        if self.is_running:
            logger.warning("AutoSyncService is already running")
            return

        # Schedule jobs
        self._setup_schedule()

        # Start the scheduler in a background thread
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()

        logger.info("AutoSyncService started successfully")

    def stop_auto_sync(self):
        """Stop the automatic sync service"""
        self.is_running = False
        schedule.clear()
        logger.info("AutoSyncService stopped")

    def _setup_schedule(self):
        """Setup the sync schedule"""
        settings = self.config.get_sync_settings()

        # Schedule full refresh (6 months)
        # For production: schedule.every(180).days.do(self._full_refresh_job)
        # For testing: schedule every 3 days
        schedule.every(3).days.do(self._full_refresh_job)

        # Schedule incremental sync daily
        schedule.every().day.at("01:00").do(self._incremental_sync_job)

        # Schedule resample after each sync
        schedule.every().day.at("02:00").do(self._resample_job)

        # Schedule RETUNE trigger after data sync (if enabled)
        if self.retune_settings['enabled']:
            # Schedule retune to run after data is updated
            schedule.every(self.retune_settings['interval_hours']).hours.do(self._retune_job)
            logger.info(f"Retune scheduled every {self.retune_settings['interval_hours']} hours")

        logger.info("Sync jobs scheduled successfully")

    def _run_scheduler(self):
        """Run the scheduler in a loop"""
        logger.info("Scheduler thread started")
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)

        logger.info("Scheduler thread stopped")

    def _full_refresh_job(self):
        """Execute full refresh job"""
        try:
            logger.info("Starting scheduled full refresh...")
            start_time = datetime.now()

            self.sync_engine.full_refresh(days=self.config.get_sync_settings()['sync_days'])

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info(f"Full refresh completed in {duration}")

            # Trigger retune after successful sync if enabled
            if self.retune_settings['enabled']:
                logger.info("Triggering retune after data refresh...")
                self._trigger_retune()

        except Exception as e:
            logger.error(f"Error in full refresh job: {e}")

    def _incremental_sync_job(self):
        """Execute incremental sync job"""
        try:
            logger.info("Starting scheduled incremental sync...")
            start_time = datetime.now()

            self.sync_engine.incremental_update()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info(f"Incremental sync completed in {duration}")

            # Trigger retune after successful sync if enabled
            if self.retune_settings['enabled']:
                logger.info("Triggering retune after incremental sync...")
                self._trigger_retune()

        except Exception as e:
            logger.error(f"Error in incremental sync job: {e}")

    def _resample_job(self):
        """Execute resample job"""
        try:
            logger.info("Starting scheduled resample...")
            start_time = datetime.now()

            # Resample all coins to all timeframes
            coins = self.config.get_coins()
            self.resample_engine.resample_all(coins)

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info(f"Resample completed in {duration}")

        except Exception as e:
            logger.error(f"Error in resample job: {e}")

    def _retune_job(self):
        """Execute retune job based on the RETUNE configuration"""
        try:
            logger.info("Starting scheduled retune job...")
            self._trigger_retune()
        except Exception as e:
            logger.error(f"Error in retune job: {e}")

    def _trigger_retune(self):
        """Trigger retune process - this could interface with existing retune system"""
        try:
            # In a real implementation, this would call the retune orchestrator
            logger.info("Retune process triggered - would interface with existing retune system")
            logger.info("Fresh data is available for optimization")

            # Here we would typically call the existing retune system
            # For example, call AutoRetuneOptimizer or similar existing component
            # This is a placeholder to show where the integration point would be

        except Exception as e:
            logger.error(f"Error in retune trigger: {e}")

    def manual_full_refresh(self):
        """Execute a manual full refresh"""
        logger.info("Manual full refresh initiated")
        self._full_refresh_job()

    def manual_incremental_sync(self):
        """Execute a manual incremental sync"""
        logger.info("Manual incremental sync initiated")
        self._incremental_sync_job()

    def manual_resample(self):
        """Execute a manual resample"""
        logger.info("Manual resample initiated")
        self._resample_job()

    def manual_retune(self):
        """Execute a manual retune"""
        logger.info("Manual retune initiated")
        self._trigger_retune()


def create_auto_sync_service():
    """Factory function to create and return an AutoSyncService instance"""
    return AutoSyncService()


if __name__ == "__main__":
    # Example usage
    service = create_auto_sync_service()
    service.start_auto_sync()

    logger.info("Auto-sync service is running. Press Ctrl+C to stop.")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down auto-sync service...")
        service.stop_auto_sync()