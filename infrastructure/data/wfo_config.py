"""
Configuration manager for WFO Downloader System.
Reads settings from environment variables with .env file support.
"""
import os
from typing import List
from dotenv import load_dotenv


class WFOConfigManager:
    """Configuration manager for WFO Downloader System"""

    def __init__(self, env_file: str = ".env"):
        """Initialize the configuration manager and load environment variables"""
        # Load environment variables from .env file
        load_dotenv(env_file)

        # Load configuration values from environment variables
        self.wfo_enabled = self._get_bool('WFO_ENABLED', True)
        self.coins: List[str] = self._get_list('WFO_COINS', [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
            'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'LUNAUSDT',
            'TONUSDT', 'ALGOUSDT', 'XLMUSDT', 'ETCUSDT', 'BCHUSDT',
            'NEARUSDT', 'FLOWUSDT', 'MANAUSDT', 'SANDUSDT', 'AAVEUSDT'
        ])
        self.data_dir = os.getenv('WFO_DATA_DIR', './data')
        self.raw_dir = os.getenv('WFO_RAW_DIR', './data/history/raw/1m')
        self.processed_dir = os.getenv('WFO_PROCESSED_DIR', './data/history/processed')
        self.sync_days = int(os.getenv('WFO_SYNC_DAYS', '180'))
        self.incremental_days = int(os.getenv('WFO_INCREMENTAL_DAYS', '2'))
        self.refresh_interval_hours = int(os.getenv('WFO_REFRESH_INTERVAL_HOURS', '24'))
        self.default_timeframes = self._get_list('WFO_DEFAULT_TIMEFRAMES', ['5m', '15m', '30m', '1h'])

        # Risk management settings (compatible with existing system)
        self.risk_capital_per_symbol = float(os.getenv('RISK_CAPITAL_PER_SYMBOL', '0.05'))
        self.risk_max_exposure = float(os.getenv('RISK_MAX_EXPOSURE', '0.80'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.02'))
        self.risk_max_drawdown = float(os.getenv('RISK_MAX_DRAWDOWN', '0.15'))

        # API settings
        self.binance_api_url = os.getenv('BINANCE_API_URL', 'https://api.binance.com')
        self.binance_retry_attempts = int(os.getenv('BINANCE_RETRY_ATTEMPTS', '3'))
        self.binance_rate_limit_delay = float(os.getenv('BINANCE_RATE_LIMIT_DELAY', '0.2'))

        # RETUNE configuration integration (existing system)
        self.retune_enabled = self._get_bool('RETUNE_ENABLED', True)
        self.retune_interval_hours = int(os.getenv('RETUNE_INTERVAL_HOURS', '6'))
        self.retune_performance_threshold = float(os.getenv('RETUNE_PERFORMANCE_THRESHOLD', '0.15'))
        self.retune_evals_per_cycle = int(os.getenv('RETUNE_EVALS_PER_RETUNE', '20'))

    def _get_bool(self, key: str, default: bool) -> bool:
        """Get a boolean value from environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def _get_list(self, key: str, default: List[str]) -> List[str]:
        """Get a list value from environment variable (comma-separated)"""
        value = os.getenv(key)
        if value is None:
            return default
        return [item.strip() for item in value.split(',') if item.strip()]

    def get_coins(self) -> List[str]:
        """Get the list of configured coins"""
        return self.coins

    def get_timeframes(self) -> List[str]:
        """Get the list of configured timeframes"""
        return self.default_timeframes

    def get_data_paths(self) -> dict:
        """Get all data directory paths"""
        return {
            'data_dir': self.data_dir,
            'raw_dir': self.raw_dir,
            'processed_dir': self.processed_dir
        }

    def get_sync_settings(self) -> dict:
        """Get sync-related settings"""
        return {
            'sync_days': self.sync_days,
            'incremental_days': self.incremental_days,
            'refresh_interval_hours': self.refresh_interval_hours
        }

    def get_risk_settings(self) -> dict:
        """Get risk management settings"""
        return {
            'capital_per_symbol': self.risk_capital_per_symbol,
            'max_exposure': self.risk_max_exposure,
            'risk_per_trade': self.risk_per_trade,
            'max_drawdown': self.risk_max_drawdown
        }

    def get_api_settings(self) -> dict:
        """Get API settings"""
        return {
            'api_url': self.binance_api_url,
            'retry_attempts': self.binance_retry_attempts,
            'rate_limit_delay': self.binance_rate_limit_delay
        }

    def get_retune_settings(self) -> dict:
        """Get RETUNE settings from existing configuration"""
        return {
            'enabled': self.retune_enabled,
            'interval_hours': self.retune_interval_hours,
            'performance_threshold': self.retune_performance_threshold,
            'evals_per_cycle': self.retune_evals_per_cycle
        }


# Global instance for easy access
config = WFOConfigManager()