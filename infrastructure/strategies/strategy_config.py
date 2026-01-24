"""
Standardized Configuration for Strategies
Provides consistent environment variable naming and default values
"""
import os
from typing import Union


class StrategyConfig:
    """
    Standardized configuration class for all strategies.
    Provides consistent environment variable naming and default values.
    """

    # Common strategy settings
    @staticmethod
    def get_strategy_enabled(strategy_name: str) -> bool:
        """Get if a strategy is enabled"""
        env_var = f'{strategy_name.upper()}_STRATEGY_ENABLED'
        return os.getenv(env_var, 'true').lower() == 'true'

    @staticmethod
    def get_strategy_max_position_size(strategy_name: str, default: float = 0.05) -> float:
        """Get maximum position size for a strategy"""
        env_var = f'{strategy_name.upper()}_MAX_POSITION_SIZE'
        return float(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_min_confidence(strategy_name: str = None, default: float = 0.3) -> float:
        """Get minimum confidence threshold for a strategy"""
        if strategy_name:
            env_var = f'{strategy_name.upper()}_MIN_CONFIDENCE_THRESHOLD'
        else:
            env_var = 'STRATEGY_MIN_CONFIDENCE_THRESHOLD'
        return float(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_max_confidence(strategy_name: str = None, default: float = 0.95) -> float:
        """Get maximum confidence threshold for a strategy"""
        if strategy_name:
            env_var = f'{strategy_name.upper()}_MAX_CONFIDENCE_THRESHOLD'
        else:
            env_var = 'STRATEGY_MAX_CONFIDENCE_THRESHOLD'
        return float(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_risk_per_trade(strategy_name: str, default: float = 0.02) -> float:
        """Get risk per trade for a strategy"""
        env_var = f'{strategy_name.upper()}_RISK_PER_TRADE'
        return float(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_stop_loss_multiplier(strategy_name: str, default: float = 1.5) -> float:
        """Get stop loss multiplier for a strategy"""
        env_var = f'{strategy_name.upper()}_STOP_LOSS_MULTIPLIER'
        return float(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_take_profit_multiplier(strategy_name: str, default: float = 2.0) -> float:
        """Get take profit multiplier for a strategy"""
        env_var = f'{strategy_name.upper()}_TAKE_PROFIT_MULTIPLIER'
        return float(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_lookback_period(strategy_name: str = None, default: int = 50) -> int:
        """Get lookback period for a strategy"""
        if strategy_name:
            env_var = f'{strategy_name.upper()}_LOOKBACK_PERIOD'
        else:
            env_var = 'STRATEGY_LOOKBACK_PERIOD'
        return int(os.getenv(env_var, str(default)))

    @staticmethod
    def get_strategy_timeframe(strategy_name: str = None, default: str = '1h') -> str:
        """Get timeframe for a strategy"""
        if strategy_name:
            env_var = f'{strategy_name.upper()}_TIMEFRAME'
        else:
            env_var = 'STRATEGY_TIMEFRAME'
        return os.getenv(env_var, default)


# Convenience functions for specific strategies
def get_trend_following_config() -> dict:
    """Get configuration for TrendFollowingStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('TREND_FOLLOWING'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('TREND_FOLLOWING', 0.05),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('TREND_FOLLOWING', 0.3),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('TREND_FOLLOWING', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('TREND_FOLLOWING', 0.02),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('TREND_FOLLOWING', 1.5),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('TREND_FOLLOWING', 2.0),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('TREND_FOLLOWING', 50),
        'timeframe': StrategyConfig.get_strategy_timeframe('TREND_FOLLOWING', '1h'),
        'parameters': {
            'lookback_period': 50,
            'ma_type': 'EMA',
            'ma_period': 20,
            'trend_strength_threshold': 0.01
        }
    }


def get_mean_reversion_config() -> dict:
    """Get configuration for MeanReversionStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('MEAN_REVERSION'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('MEAN_REVERSION', 0.04),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('MEAN_REVERSION', 0.35),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('MEAN_REVERSION', 0.90),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('MEAN_REVERSION', 0.02),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('MEAN_REVERSION', 1.2),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('MEAN_REVERSION', 1.8),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('MEAN_REVERSION', 100),
        'timeframe': StrategyConfig.get_strategy_timeframe('MEAN_REVERSION', '1h'),
        'parameters': {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std_dev': 2.0
        }
    }


def get_volatility_breakout_config() -> dict:
    """Get configuration for VolatilityBreakoutStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('VOLATILITY_BREAKOUT'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('VOLATILITY_BREAKOUT', 0.03),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('VOLATILITY_BREAKOUT', 0.4),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('VOLATILITY_BREAKOUT', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('VOLATILITY_BREAKOUT', 0.015),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('VOLATILITY_BREAKOUT', 1.0),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('VOLATILITY_BREAKOUT', 2.5),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('VOLATILITY_BREAKOUT', 30),
        'timeframe': StrategyConfig.get_strategy_timeframe('VOLATILITY_BREAKOUT', '15m'),
        'parameters': {
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'volatility_threshold': 0.02
        }
    }


def get_momentum_config() -> dict:
    """Get configuration for MomentumStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('MOMENTUM'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('MOMENTUM', 0.04),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('MOMENTUM', 0.3),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('MOMENTUM', 0.90),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('MOMENTUM', 0.018),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('MOMENTUM', 1.3),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('MOMENTUM', 2.2),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('MOMENTUM', 20),
        'timeframe': StrategyConfig.get_strategy_timeframe('MOMENTUM', '1h'),
        'parameters': {
            'roc_period': 10,
            'momentum_threshold': 0.02
        }
    }


def get_scalping_config() -> dict:
    """Get configuration for ScalpingStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('SCALPING'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('SCALPING', 0.02),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('SCALPING', 0.5),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('SCALPING', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('SCALPING', 0.01),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('SCALPING', 0.8),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('SCALPING', 1.5),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('SCALPING', 50),
        'timeframe': StrategyConfig.get_strategy_timeframe('SCALPING', '1m'),
        'parameters': {
            'fast_ma': 5,
            'slow_ma': 10,
            'rsi_period': 7,
            'rsi_oversold': 20,
            'rsi_overbought': 80
        }
    }


def get_breakout_config() -> dict:
    """Get configuration for BreakoutStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('BREAKOUT'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('BREAKOUT', 0.05),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('BREAKOUT', 0.35),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('BREAKOUT', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('BREAKOUT', 0.02),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('BREAKOUT', 1.4),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('BREAKOUT', 2.8),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('BREAKOUT', 20),
        'timeframe': StrategyConfig.get_strategy_timeframe('BREAKOUT', '15m'),
        'parameters': {
            'lookback_period': 20,
            'breakout_threshold': 0.015
        }
    }


def get_liquidity_config() -> dict:
    """Get configuration for LiquidityStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('LIQUIDITY'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('LIQUIDITY', 0.03),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('LIQUIDITY', 0.4),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('LIQUIDITY', 0.90),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('LIQUIDITY', 0.015),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('LIQUIDITY', 1.1),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('LIQUIDITY', 2.0),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('LIQUIDITY', 10),
        'timeframe': StrategyConfig.get_strategy_timeframe('LIQUIDITY', '5m'),
        'parameters': {
            'liquidity_threshold': 1000000,
            'volume_spike_factor': 1.5
        }
    }


def get_mtf_trend_config() -> dict:
    """Get configuration for MTFTrendStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('MTF_TREND'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('MTF_TREND', 0.06),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('MTF_TREND', 0.45),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('MTF_TREND', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('MTF_TREND', 0.025),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('MTF_TREND', 1.6),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('MTF_TREND', 2.4),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('MTF_TREND', 50),
        'timeframe': StrategyConfig.get_strategy_timeframe('MTF_TREND', '15m'),
        'parameters': {
            'short_timeframe': '5m',
            'medium_timeframe': '15m',
            'long_timeframe': '1h',
            'alignment_threshold': 0.7
        }
    }


def get_oi_footprint_config() -> dict:
    """Get configuration for OIFootprintStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('OI_FOOTPRINT'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('OI_FOOTPRINT', 0.04),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('OI_FOOTPRINT', 0.5),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('OI_FOOTPRINT', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('OI_FOOTPRINT', 0.02),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('OI_FOOTPRINT', 1.2),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('OI_FOOTPRINT', 2.0),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('OI_FOOTPRINT', 25),
        'timeframe': StrategyConfig.get_strategy_timeframe('OI_FOOTPRINT', '1h'),
        'parameters': {
            'oi_change_threshold': 0.05,
            'price_correlation_threshold': 0.6
        }
    }


def get_sweep_scalper_config() -> dict:
    """Get configuration for SweepScalperStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('SWEEP_SCALPER'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('SWEEP_SCALPER', 0.01),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('SWEEP_SCALPER', 0.6),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('SWEEP_SCALPER', 0.95),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('SWEEP_SCALPER', 0.01),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('SWEEP_SCALPER', 0.7),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('SWEEP_SCALPER', 1.3),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('SWEEP_SCALPER', 10),
        'timeframe': StrategyConfig.get_strategy_timeframe('SWEEP_SCALPER', '1m'),
        'parameters': {
            'volume_threshold': 50000,
            'spread_threshold': 0.001
        }
    }


def get_vwap_reversal_config() -> dict:
    """Get configuration for VWAPReversalStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('VWAP_REVERSAL'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('VWAP_REVERSAL', 0.03),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('VWAP_REVERSAL', 0.4),
        'max_confidence': StrategyConfig.get_strategy_max_confidence('VWAP_REVERSAL', 0.90),
        'risk_per_trade': StrategyConfig.get_strategy_risk_per_trade('VWAP_REVERSAL', 0.018),
        'stop_loss_multiplier': StrategyConfig.get_strategy_stop_loss_multiplier('VWAP_REVERSAL', 1.0),
        'take_profit_multiplier': StrategyConfig.get_strategy_take_profit_multiplier('VWAP_REVERSAL', 1.8),
        'lookback_period': StrategyConfig.get_strategy_lookback_period('VWAP_REVERSAL', 89),
        'timeframe': StrategyConfig.get_strategy_timeframe('VWAP_REVERSAL', '5m'),
        'parameters': {
            'vwap_period': 89,
            'std_dev_multiplier': 1.5,
            'reversal_threshold': 0.01
        }
    }