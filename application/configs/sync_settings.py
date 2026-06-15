"""
Configuration settings for the Downloader/Sync Engine.

This module manages configuration settings for the sync system with support for
centralized configuration and validation.
"""
from dataclasses import dataclass
from typing import Optional
from bootstrap.settings.loaders import load_settings


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
        # Load from centralized configuration if they exist
        self.load_from_configs()

    def load_from_configs(self):
        """Load configuration from the single settings loader (bootstrap.settings)."""
        _data = load_settings().data
        self.sync_interval_seconds = _data.sync_interval_seconds if _data and hasattr(_data, 'sync_interval_seconds') else int(self.sync_interval_seconds)
        self.async_concurrency = _data.async_concurrency if _data and hasattr(_data, 'async_concurrency') else int(self.async_concurrency)
        self.download_threadpool_workers = _data.download_threadpool_workers if _data and hasattr(_data, 'download_threadpool_workers') else int(self.download_threadpool_workers)
        self.retry_max_attempts = _data.retry_max_attempts if _data and hasattr(_data, 'retry_max_attempts') else int(self.retry_max_attempts)
        self.retry_backoff_base = _data.retry_backoff_base if _data and hasattr(_data, 'retry_backoff_base') else float(self.retry_backoff_base)
        self.retry_backoff_factor = _data.retry_backoff_factor if _data and hasattr(_data, 'retry_backoff_factor') else float(self.retry_backoff_factor)
        self.rate_limit_tokens_per_second = _data.rate_limit_tokens_per_second if _data and hasattr(_data, 'rate_limit_tokens_per_second') else float(self.rate_limit_tokens_per_second)
        self.temp_file_suffix = _data.temp_file_suffix if _data and hasattr(_data, 'temp_file_suffix') else self.temp_file_suffix
        self.data_dir = _data.data_dir if _data and hasattr(_data, 'data_dir') else self.data_dir
        self.max_gap_fill_minutes = _data.max_gap_fill_minutes if _data and hasattr(_data, 'max_gap_fill_minutes') else int(self.max_gap_fill_minutes)
        self.raw_retention_days = _data.raw_retention_days if _data and hasattr(_data, 'raw_retention_days') else int(self.raw_retention_days)
        self.processed_retention_days = _data.processed_retention_days if _data and hasattr(_data, 'processed_retention_days') else int(self.processed_retention_days)


# Global configuration instance
settings = SyncSettings()
