"""
Configuration settings for the Downloader/Sync Engine.

This module manages configuration settings for the sync system with support for
environment variables and validation.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SyncSettings:
    """Main configuration class for sync engine"""

    # Sync settings
    sync_interval_seconds: int = 7200  # 2 hours
    async_concurrency: int = 100
    download_threadpool_workers: int = 8
    retry_max_attempts: int = 5
    retry_backoff_base: float = 0.5
    retry_backoff_factor: float = 2.0
    rate_limit_tokens_per_second: float = 10
    temp_file_suffix: str = ".partial"

    # Data settings
    data_dir: str = "./data/history"
    max_gap_fill_minutes: int = 1440  # 24 hours

    # Retention settings
    raw_retention_days: int = 365
    processed_retention_days: int = 1095  # 3 years

    def __post_init__(self):
        # Load from environment variables if they exist
        self.load_from_env()

    def load_from_env(self):
        """Load configuration from environment variables"""
        self.sync_interval_seconds = int(os.getenv("SYNC_INTERVAL_SECONDS", str(self.sync_interval_seconds)))
        self.async_concurrency = int(os.getenv("ASYNC_CONCURRENCY", str(self.async_concurrency)))
        self.download_threadpool_workers = int(os.getenv("DOWNLOAD_THREADPOOL_WORKERS", str(self.download_threadpool_workers)))
        self.retry_max_attempts = int(os.getenv("RETRY_MAX_ATTEMPTS", str(self.retry_max_attempts)))
        self.retry_backoff_base = float(os.getenv("RETRY_BACKOFF_BASE", str(self.retry_backoff_base)))
        self.retry_backoff_factor = float(os.getenv("RETRY_BACKOFF_FACTOR", str(self.retry_backoff_factor)))
        self.rate_limit_tokens_per_second = float(os.getenv("RATE_LIMIT_TOKENS_PER_SECOND", str(self.rate_limit_tokens_per_second)))
        self.temp_file_suffix = os.getenv("TEMP_FILE_SUFFIX", self.temp_file_suffix)
        self.data_dir = os.getenv("DATA_DIR", self.data_dir)
        self.max_gap_fill_minutes = int(os.getenv("MAX_GAP_FILL_MINUTES", str(self.max_gap_fill_minutes)))
        self.raw_retention_days = int(os.getenv("RAW_RETENTION_DAYS", str(self.raw_retention_days)))
        self.processed_retention_days = int(os.getenv("PROCESSED_RETENTION_DAYS", str(self.processed_retention_days)))


# Global configuration instance
settings = SyncSettings()