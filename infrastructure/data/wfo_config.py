"""
Configuration manager for WFO Downloader System.
Reads settings from the centralized Configs system.
"""
from typing import List
from bootstrap.settings.loaders import load_settings


class WFOConfigManager:
    """Configuration manager for WFO Downloader System"""

    def __init__(self, env_file: str = None):
        """Initialize the configuration manager using the centralized Configs system"""
        # Use the centralized Configs system instead of direct environment access

        # Load configuration values from the centralized Configs system
        self.wfo_enabled = load_settings().wfo.wfo_enabled if load_settings().wfo and hasattr(load_settings().wfo, 'wfo_enabled') else True
        self.coins: List[str] = load_settings().wfo.wfo_coins if load_settings().wfo and load_settings().wfo.wfo_coins else [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT',
            'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'LINKUSDT', 'LUNAUSDT',
            'TONUSDT', 'ALGOUSDT', 'XLMUSDT', 'ETCUSDT', 'BCHUSDT',
            'NEARUSDT', 'FLOWUSDT', 'MANAUSDT', 'SANDUSDT', 'AAVEUSDT'
        ]
        self.data_dir = load_settings().wfo.data_dir if load_settings().wfo and hasattr(load_settings().wfo, 'data_dir') else './data'
        self.raw_dir = load_settings().wfo.raw_dir if load_settings().wfo and hasattr(load_settings().wfo, 'raw_dir') else './data/history/raw/1m'
        self.processed_dir = load_settings().wfo.processed_dir if load_settings().wfo and hasattr(load_settings().wfo, 'processed_dir') else './data/history/processed'
        self.sync_days = load_settings().wfo.sync_days if load_settings().wfo and hasattr(load_settings().wfo, 'sync_days') else 180
        self.incremental_days = load_settings().wfo.incremental_days if load_settings().wfo and hasattr(load_settings().wfo, 'incremental_days') else 2
        self.refresh_interval_hours = load_settings().wfo.refresh_interval_hours if load_settings().wfo and hasattr(load_settings().wfo, 'refresh_interval_hours') else 24
        self.default_timeframes = load_settings().wfo.default_timeframes if load_settings().wfo and hasattr(load_settings().wfo, 'default_timeframes') else ['5m', '15m', '30m', '1h']

        # Risk management settings (compatible with existing system)
        self.risk_capital_per_symbol = load_settings().risk.capital_per_symbol if load_settings().risk and hasattr(load_settings().risk, 'capital_per_symbol') else 0.05
        self.risk_max_exposure = load_settings().risk.max_exposure if load_settings().risk and hasattr(load_settings().risk, 'max_exposure') else 0.80
        self.risk_per_trade = load_settings().risk.per_trade if load_settings().risk and hasattr(load_settings().risk, 'per_trade') else 0.02
        self.risk_max_drawdown = load_settings().risk.max_drawdown if load_settings().risk and hasattr(load_settings().risk, 'max_drawdown') else 0.15

        # API settings
        self.binance_api_url = load_settings().broker.binance_api_url if load_settings().broker and hasattr(load_settings().broker, 'binance_api_url') else 'https://api.binance.com'
        self.binance_retry_attempts = load_settings().broker.binance_retry_attempts if load_settings().broker and hasattr(load_settings().broker, 'binance_retry_attempts') else 3
        self.binance_rate_limit_delay = load_settings().broker.binance_rate_limit_delay if load_settings().broker and hasattr(load_settings().broker, 'binance_rate_limit_delay') else 0.2

        # RETUNE configuration integration (existing system)
        self.retune_enabled = load_settings().optimization.retune_enabled if load_settings().optimization and hasattr(load_settings().optimization, 'retune_enabled') else True
        self.retune_interval_hours = load_settings().optimization.retune_interval_hours if load_settings().optimization and hasattr(load_settings().optimization, 'retune_interval_hours') else 6
        self.retune_performance_threshold = load_settings().optimization.retune_performance_threshold if load_settings().optimization and hasattr(load_settings().optimization, 'retune_performance_threshold') else 0.15
        self.retune_evals_per_cycle = load_settings().optimization.retune_evals_per_retune if load_settings().optimization and hasattr(load_settings().optimization, 'retune_evals_per_retune') else 20

    def _get_bool(self, key: str, default: bool) -> bool:
        """Get a boolean value from the centralized Configs system"""
        # Map environment variable names to Configs attributes
        if key == 'WFO_ENABLED':
            return load_settings().wfo.wfo_enabled if load_settings().wfo and hasattr(load_settings().wfo, 'wfo_enabled') else default
        elif key == 'RETUNE_ENABLED':
            return load_settings().optimization.retune_enabled if load_settings().optimization and hasattr(load_settings().optimization, 'retune_enabled') else default
        else:
            return default

    def _get_list(self, key: str, default: List[str]) -> List[str]:
        """Get a list value from the centralized Configs system"""
        # Map environment variable names to Configs attributes
        if key == 'WFO_COINS':
            return load_settings().wfo.wfo_coins if load_settings().wfo and load_settings().wfo.wfo_coins else default
        elif key == 'WFO_DEFAULT_TIMEFRAMES':
            return load_settings().wfo.default_timeframes if load_settings().wfo and hasattr(load_settings().wfo, 'default_timeframes') else default
        else:
            return default

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