"""
Configuration settings for the Downloader/Sync Engine.

This module manages configuration settings for the sync system with support for
centralized configuration and validation.
"""
from dataclasses import dataclass
from typing import Optional
from application.configs.configs import Configs


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
        """Load configuration from centralized Configs system"""
        self.sync_interval_seconds = Configs.data.sync_interval_seconds if Configs.data and hasattr(Configs.data, 'sync_interval_seconds') else int(self.sync_interval_seconds)
        self.async_concurrency = Configs.data.async_concurrency if Configs.data and hasattr(Configs.data, 'async_concurrency') else int(self.async_concurrency)
        self.download_threadpool_workers = Configs.data.download_threadpool_workers if Configs.data and hasattr(Configs.data, 'download_threadpool_workers') else int(self.download_threadpool_workers)
        self.retry_max_attempts = Configs.data.retry_max_attempts if Configs.data and hasattr(Configs.data, 'retry_max_attempts') else int(self.retry_max_attempts)
        self.retry_backoff_base = Configs.data.retry_backoff_base if Configs.data and hasattr(Configs.data, 'retry_backoff_base') else float(self.retry_backoff_base)
        self.retry_backoff_factor = Configs.data.retry_backoff_factor if Configs.data and hasattr(Configs.data, 'retry_backoff_factor') else float(self.retry_backoff_factor)
        self.rate_limit_tokens_per_second = Configs.data.rate_limit_tokens_per_second if Configs.data and hasattr(Configs.data, 'rate_limit_tokens_per_second') else float(self.rate_limit_tokens_per_second)
        self.temp_file_suffix = Configs.data.temp_file_suffix if Configs.data and hasattr(Configs.data, 'temp_file_suffix') else self.temp_file_suffix
        self.data_dir = Configs.data.data_dir if Configs.data and hasattr(Configs.data, 'data_dir') else self.data_dir
        self.max_gap_fill_minutes = Configs.data.max_gap_fill_minutes if Configs.data and hasattr(Configs.data, 'max_gap_fill_minutes') else int(self.max_gap_fill_minutes)
        self.raw_retention_days = Configs.data.raw_retention_days if Configs.data and hasattr(Configs.data, 'raw_retention_days') else int(self.raw_retention_days)
        self.processed_retention_days = Configs.data.processed_retention_days if Configs.data and hasattr(Configs.data, 'processed_retention_days') else int(self.processed_retention_days)


# Global configuration instance
settings = SyncSettings()
