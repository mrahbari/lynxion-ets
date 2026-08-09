from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class MonitoringConfig(BaseModel):
    """
    Configuration for system monitoring and logging.
    """
    # Original fields
    logging_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    alert_enabled: bool = Field(default=True, description="Whether alerts are enabled")
    metrics_collection: bool = Field(default=True, description="Whether metrics collection is enabled")
    heartbeat_interval: int = Field(default=60, ge=1, description="Heartbeat interval in seconds")

    # Additional monitoring fields from .env
    telegram_bot_name: str = Field(default="@LynxionNotifierBot", description="Telegram bot name")
    telegram_bot_url: str = Field(default="t.me/LynxionNotifierBot", description="Telegram bot URL")
    telegram_bot_update_url: str = Field(default="https://api.telegram.org/bot8324444752:AAGoubuQSgXp6lhQGCxcOtGT6hLg3kTgWbY/getUpdates", description="Telegram bot update URL")
    telegram_bot_token: str = Field(default="8324444752:AAGoubuQSgXp6lhQGCxcOtGT6hLg3kTgWbY", description="Telegram bot token")
    telegram_chat_id: int = Field(default=71819811, description="Telegram chat ID")
    telegram_notifications_enabled: bool = Field(default=True, description="Telegram notifications enabled")
    log_file_path: str = Field(default="./logs/trading_system.log", description="Log file path")
    log_max_file_size_mb: int = Field(default=50, description="Max log file size in MB")
    log_backup_count: int = Field(default=5, description="Number of backup log files")
    enabled: bool = Field(default=True, description="Monitoring enabled")
    metrics_reporting_interval_minutes: int = Field(default=3, description="Metrics reporting interval in minutes")
    forensic_logging_enabled: bool = Field(default=True, description="Forensic logging enabled")
    trade_journal_collector_enabled: bool = Field(default=True, description="Persistent trade journal collector enabled")
    enable_metrics: bool = Field(default=True, description="Enable metrics")

    @validator('logging_level')
    def validate_logging_level(cls, v):
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f'logging_level must be one of {valid_levels}')
        return v.upper()

    class Config:
        extra = "forbid"