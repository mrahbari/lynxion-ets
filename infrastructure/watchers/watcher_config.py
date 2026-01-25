"""
Standardized Configuration for Watchers
Provides consistent access to configuration through the Configs system
"""
import os
from typing import Union
from application.configs.configs import Configs


class WatcherConfig:
    """
    Standardized configuration class for all watchers.
    Provides consistent environment variable naming and default values.
    """
    
    # Common watcher settings
    @staticmethod
    def get_watcher_enabled(watcher_name: str) -> bool:
        """Get if a watcher is enabled"""
        # Map watcher names to config attributes
        config_map = {
            'market_pulse': lambda: Configs.watcher.market_pulse_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'market_pulse_watcher_enabled') else True,
            'volatility': lambda: Configs.watcher.volatility_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'volatility_watcher_enabled') else True,
            'trend_mtf': lambda: Configs.watcher.trend_mtf_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'trend_mtf_watcher_enabled') else True,
            'anomaly_ml': lambda: Configs.watcher.anomaly_ml_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'anomaly_ml_watcher_enabled') else True,
            'orderflow_ws': lambda: Configs.watcher.orderflow_ws_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'orderflow_ws_watcher_enabled') else True,
            'cmc_screener': lambda: Configs.watcher.cmc_screener_enabled if Configs.watcher and hasattr(Configs.watcher, 'cmc_screener_enabled') else True,
            'funding_rate': lambda: Configs.watcher.funding_rate_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'funding_rate_watcher_enabled') else True,
            'liquidity': lambda: Configs.watcher.liquidity_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'liquidity_watcher_enabled') else True,
            'historical_candle': lambda: Configs.watcher.historical_candle_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'historical_candle_watcher_enabled') else True,
            'tick': lambda: Configs.watcher.tick_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'tick_watcher_enabled') else False,
        }

        if watcher_name.lower() in config_map:
            return config_map[watcher_name.lower()]()
        else:
            # Default to True if watcher name is not recognized
            return True
    
    @staticmethod
    def get_watcher_lookback(watcher_name: str, default: int = 20) -> int:
        """Get lookback period for a watcher"""
        # Map watcher names to config attributes
        config_map = {
            'market_pulse': lambda: Configs.watcher.market_pulse_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'market_pulse_lookback_period') else default,
            'volatility': lambda: Configs.watcher.volatility_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'volatility_lookback_period') else default,
            'trend_mtf': lambda: Configs.watcher.trend_mtf_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'trend_mtf_lookback_period') else default,
            'anomaly_ml': lambda: Configs.watcher.anomaly_ml_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'anomaly_ml_lookback_period') else default,
            'orderflow_ws': lambda: Configs.watcher.orderflow_ws_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'orderflow_ws_lookback_period') else default,
            'cmc_screener': lambda: Configs.watcher.cmc_screener_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'cmc_screener_lookback_period') else default,
            'funding_rate': lambda: Configs.watcher.funding_rate_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'funding_rate_lookback_period') else default,
            'liquidity': lambda: Configs.watcher.liquidity_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'liquidity_lookback_period') else default,
            'historical_candle': lambda: Configs.watcher.historical_candle_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'historical_candle_lookback_period') else default,
            'tick': lambda: Configs.watcher.tick_lookback_period if Configs.watcher and hasattr(Configs.watcher, 'tick_lookback_period') else default,
        }

        if watcher_name.lower() in config_map:
            return config_map[watcher_name.lower()]()
        else:
            # Default to provided default if watcher name is not recognized
            return default
    
    @staticmethod
    def get_watcher_min_confidence(watcher_name: str = None, default: float = 0.05) -> float:
        """Get minimum confidence threshold for a watcher"""
        if watcher_name:
            # Map specific watcher names to config attributes
            config_map = {
                'market_pulse': lambda: Configs.watcher.market_pulse_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'market_pulse_min_confidence_threshold') else default,
                'volatility': lambda: Configs.watcher.volatility_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'volatility_min_confidence_threshold') else default,
                'trend_mtf': lambda: Configs.watcher.trend_mtf_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'trend_mtf_min_confidence_threshold') else default,
                'anomaly_ml': lambda: Configs.watcher.anomaly_ml_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'anomaly_ml_min_confidence_threshold') else default,
                'orderflow_ws': lambda: Configs.watcher.orderflow_ws_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'orderflow_ws_min_confidence_threshold') else default,
                'cmc_screener': lambda: Configs.watcher.cmc_screener_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'cmc_screener_min_confidence_threshold') else default,
                'funding_rate': lambda: Configs.watcher.funding_rate_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'funding_rate_min_confidence_threshold') else default,
                'liquidity': lambda: Configs.watcher.liquidity_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'liquidity_min_confidence_threshold') else default,
                'historical_candle': lambda: Configs.watcher.historical_candle_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'historical_candle_min_confidence_threshold') else default,
                'tick': lambda: Configs.watcher.tick_min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'tick_min_confidence_threshold') else default,
            }

            if watcher_name.lower() in config_map:
                return config_map[watcher_name.lower()]()
            else:
                return default
        else:
            # Use general watcher min confidence threshold
            return Configs.watcher.min_confidence_threshold if Configs.watcher and hasattr(Configs.watcher, 'min_confidence_threshold') else default
    
    @staticmethod
    def get_watcher_max_confidence(watcher_name: str = None, default: float = 0.95) -> float:
        """Get maximum confidence threshold for a watcher"""
        if watcher_name:
            env_var = f'{watcher_name.upper()}_MAX_CONFIDENCE_THRESHOLD'
        else:
            env_var = 'WATCHER_MAX_CONFIDENCE_THRESHOLD'
        return float(os.getenv(env_var, str(default)))
    
    @staticmethod
    def get_watcher_adaptive_sensitivity(watcher_name: str) -> bool:
        """Get if a watcher should use adaptive sensitivity"""
        env_var = f'{watcher_name.upper()}_ADAPTIVE_SENSITIVITY'
        return os.getenv(env_var, 'false').lower() == 'true'
    
    @staticmethod
    def get_watcher_target_broker(watcher_name: str, default: str = 'binance') -> str:
        """Get target broker for a watcher"""
        env_var = f'TARGET_BROKER_{watcher_name.upper()}'
        return os.getenv(env_var, default)
    
    @staticmethod
    def get_watcher_pattern_weight(watcher_name: str = None, default: float = 0.4) -> float:
        """Get pattern weight for a watcher"""
        if watcher_name:
            env_var = f'{watcher_name.upper()}_PATTERN_WEIGHT'
        else:
            env_var = 'WATCHER_PATTERN_WEIGHT'
        return float(os.getenv(env_var, str(default)))
    
    @staticmethod
    def get_watcher_momentum_weight(watcher_name: str = None, default: float = 0.3) -> float:
        """Get momentum weight for a watcher"""
        if watcher_name:
            env_var = f'{watcher_name.upper()}_MOMENTUM_WEIGHT'
        else:
            env_var = 'WATCHER_MOMENTUM_WEIGHT'
        return float(os.getenv(env_var, str(default)))
    
    @staticmethod
    def get_watcher_volatility_boost(watcher_name: str, boost_type: str = 'normal', default: float = 0.1) -> float:
        """Get volatility boost for a watcher"""
        env_var = f'{watcher_name.upper()}_VOLATILITY_{boost_type.upper()}_BOOST'
        return float(os.getenv(env_var, str(default)))
    
    @staticmethod
    def get_watcher_momentum_lookback(watcher_name: str = None, default: int = 10) -> int:
        """Get momentum lookback period for a watcher"""
        if watcher_name:
            env_var = f'{watcher_name.upper()}_MOMENTUM_LOOKBACK_PERIOD'
        else:
            env_var = 'WATCHER_MOMENTUM_LOOKBACK_PERIOD'
        return int(os.getenv(env_var, str(default)))
    
    @staticmethod
    def get_watcher_momentum_sensitivity(watcher_name: str = None, default: float = 10.0) -> float:
        """Get momentum sensitivity factor for a watcher"""
        if watcher_name:
            env_var = f'{watcher_name.upper()}_MOMENTUM_SENSITIVITY_FACTOR'
        else:
            env_var = 'WATCHER_MOMENTUM_SENSITIVITY_FACTOR'
        return float(os.getenv(env_var, str(default)))


# Convenience functions for specific watchers
def get_historical_candle_config() -> dict:
    """Get configuration for HistoricalCandleWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('HISTORICAL_CANDLE'),
        'lookback': WatcherConfig.get_watcher_lookback('HISTORICAL_CANDLE', 50),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('HISTORICAL_CANDLE', 0.05),
        'max_confidence': WatcherConfig.get_watcher_max_confidence('HISTORICAL_CANDLE', 0.95),
        'adaptive_sensitivity': WatcherConfig.get_watcher_adaptive_sensitivity('HISTORICAL_CANDLE'),
        'pattern_weight': WatcherConfig.get_watcher_pattern_weight('HISTORICAL_CANDLE', 0.4),
        'momentum_weight': WatcherConfig.get_watcher_momentum_weight('HISTORICAL_CANDLE', 0.3),
        'high_volatility_boost': WatcherConfig.get_watcher_volatility_boost('HISTORICAL_CANDLE', 'HIGH', 0.2),
        'low_volatility_boost': WatcherConfig.get_watcher_volatility_boost('HISTORICAL_CANDLE', 'LOW', 0.05),
        'normal_volatility_boost': WatcherConfig.get_watcher_volatility_boost('HISTORICAL_CANDLE', 'NORMAL', 0.1),
        'momentum_lookback': WatcherConfig.get_watcher_momentum_lookback('HISTORICAL_CANDLE', 10),
        'momentum_sensitivity': WatcherConfig.get_watcher_momentum_sensitivity('HISTORICAL_CANDLE', 10.0),
    }


def get_market_pulse_config() -> dict:
    """Get configuration for MarketPulseWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('MARKET_PULSE'),
        'lookback': WatcherConfig.get_watcher_lookback('MARKET_PULSE', 20),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('MARKET_PULSE', 0.05),
        'max_confidence': WatcherConfig.get_watcher_max_confidence('MARKET_PULSE', 0.95),
        'adaptive_sensitivity': WatcherConfig.get_watcher_adaptive_sensitivity('MARKET_PULSE'),
    }


def get_volatility_config() -> dict:
    """Get configuration for VolatilityWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('VOLATILITY'),
        'lookback': WatcherConfig.get_watcher_lookback('VOLATILITY', 20),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('VOLATILITY', 0.05),
    }


def get_trend_mtf_config() -> dict:
    """Get configuration for TrendMTFWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('TREND_MTF'),
        'short_period': int(os.getenv('TREND_MTF_SHORT_PERIOD', '5')),
        'medium_period': int(os.getenv('TREND_MTF_MEDIUM_PERIOD', '15')),
        'long_period': int(os.getenv('TREND_MTF_LONG_PERIOD', '30')),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('TREND_MTF', 0.05),
    }


def get_anomaly_ml_config() -> dict:
    """Get configuration for AnomalyMLWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('ANOMALY_ML'),
        'lookback': WatcherConfig.get_watcher_lookback('ANOMALY_ML', 50),
        'contamination': float(os.getenv('ANOMALY_ML_CONTAMINATION', '0.1')),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('ANOMALY_ML', 0.05),
    }


def get_orderflow_ws_config() -> dict:
    """Get configuration for OrderFlowWSWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('ORDERFLOW_WS'),
        'lookback': WatcherConfig.get_watcher_lookback('ORDERFLOW_WS', 100),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('ORDERFLOW_WS', 0.05),
    }


def get_funding_rate_config() -> dict:
    """Get configuration for FundingRateWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('FUNDING_RATE'),
        'lookback': WatcherConfig.get_watcher_lookback('FUNDING_RATE', 24),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('FUNDING_RATE', 0.05),
    }


def get_liquidity_config() -> dict:
    """Get configuration for LiquidityWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('LIQUIDITY'),
        'lookback': WatcherConfig.get_watcher_lookback('LIQUIDITY', 20),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('LIQUIDITY', 0.05),
    }


def get_tick_config() -> dict:
    """Get configuration for TickWatcher"""
    return {
        'enabled': WatcherConfig.get_watcher_enabled('TICK'),
        'lookback': WatcherConfig.get_watcher_lookback('TICK', 1000),
        'min_confidence': WatcherConfig.get_watcher_min_confidence('TICK', 0.05),
    }