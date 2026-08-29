"""
Standardized Configuration for Strategies
Provides consistent access to strategy configuration through the Configs system
"""
from typing import Union
from bootstrap.settings.loaders import load_settings


class StrategyConfig:
    """
    Standardized configuration class for all strategies.
    Provides consistent access to strategy configuration through the Configs system.
    """

    # Common strategy settings
    @staticmethod
    def get_strategy_enabled(strategy_name: str) -> bool:
        """Get if a strategy is enabled"""
        # For now, return True by default since we don't have dynamic strategy configs
        # This could be extended to check for specific strategy config fields in the future
        return True

    @staticmethod
    def get_strategy_max_position_size(strategy_name: str, default: float = 0.05) -> float:
        """Get maximum position size for a strategy"""
        # Use the general max position size from the strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'max_position_size'):
                    return load_settings().strategy.max_position_size
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_min_confidence(strategy_name: str = None, default: float = 0.5) -> float:
        """Get minimum confidence threshold for a strategy"""
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'min_confidence_threshold'):
                    return load_settings().strategy.min_confidence_threshold
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_max_confidence(strategy_name: str = None, default: float = 0.95) -> float:
        """Get maximum confidence threshold for a strategy"""
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'high_confidence_threshold'):
                    return load_settings().strategy.high_confidence_threshold
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_risk_per_trade(strategy_name: str, default: float = 0.02) -> float:
        """Get risk per trade for a strategy"""
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'risk_per_trade'):
                    return load_settings().strategy.risk_per_trade
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_stop_loss_multiplier(strategy_name: str, default: float = 1.5) -> float:
        """Get stop loss multiplier for a strategy"""
        # Use a general stop loss multiplier from risk config
        if load_settings().risk:
            try:
                if hasattr(load_settings().risk, 'stop_loss_percentage'):
                    return load_settings().risk.stop_loss_percentage / 0.01 * default  # Scale appropriately
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_take_profit_multiplier(strategy_name: str, default: float = 2.0) -> float:
        """Get take profit multiplier for a strategy"""
        # Use a general take profit multiplier from risk config
        if load_settings().risk:
            try:
                if hasattr(load_settings().risk, 'take_profit_percentage'):
                    return load_settings().risk.take_profit_percentage / 0.01 * default  # Scale appropriately
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_lookback_period(strategy_name: str = None, default: int = 50) -> int:
        """Get lookback period for a strategy"""
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'lookback_period'):
                    return load_settings().strategy.lookback_period
            except AttributeError:
                pass
        return default

    # Per-strategy DESIGN timeframes (deployment routing). These are the timeframes each
    # strategy was designed for (already declared as the per-call defaults across this file
    # and documented in docs/reports/strategy_architecture_review.md). This is a routing
    # table, not a parameter change — values are the strategies' existing declared TFs.
    DESIGN_TIMEFRAMES = {
        'sweep_scalper': '1m',
        'liquidity': '5m', 'vwap_reversal': '5m',
        'breakout': '15m', 'crypto_breakout': '15m', 'volatility_breakout': '15m', 'mtf_trend': '15m',
        'trend_following': '1h', 'trend_follow': '1h', 'mean_reversion': '1h',
        'oi_footprint': '1h',
        # RETIRED-slot replacement candidates (E11 strategy-replacement program)
        'short_term_reversal': '15m', 'donchian_breakout': '1h',
    }

    @staticmethod
    def get_strategy_timeframe(strategy_name: str = None, default: str = '1h') -> str:
        """Get the timeframe for a strategy.

        DEPLOYMENT FIX (Phase A): route per-strategy to its DESIGN timeframe when the name is
        known, instead of ignoring the name and returning a single global timeframe (the prior
        behaviour forced every strategy onto one TF — see strategy_architecture_review.md). A
        known strategy's design TF takes precedence; otherwise fall back to the global setting,
        then the per-call default. No parameters/thresholds are changed.
        """
        if strategy_name:
            key = str(strategy_name).strip().lower()
            if key in StrategyConfig.DESIGN_TIMEFRAMES:
                return StrategyConfig.DESIGN_TIMEFRAMES[key]
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'timeframe') and load_settings().strategy.timeframe:
                    return load_settings().strategy.timeframe
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_min_bars_between_entries(strategy_name: str, default: int = 5) -> int:
        """Get minimum bars between entries for a strategy"""
        # Use a general minimum bars setting from strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'min_bars_between_entries'):
                    return load_settings().strategy.min_bars_between_entries
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_max_trades_per_day(strategy_name: str, default: int = 10) -> int:
        """Get maximum trades per day for a strategy"""
        # Use a general max trades per day setting from strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'max_trades_per_day'):
                    return load_settings().strategy.max_trades_per_day
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_max_consecutive_losses(strategy_name: str, default: int = 3) -> int:
        """Get maximum consecutive losses before pausing for a strategy"""
        # Use a general max consecutive losses setting from strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'max_consecutive_losses'):
                    return load_settings().strategy.max_consecutive_losses
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_min_atr_threshold(strategy_name: str, default: float = 0.001) -> float:
        """Get minimum ATR threshold for trading"""
        # Use a general minimum ATR threshold from strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'min_atr_threshold'):
                    return load_settings().strategy.min_atr_threshold
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_avoid_flat_markets(strategy_name: str, default: bool = True) -> bool:
        """Get whether to avoid trading in flat markets"""
        # Use a general flat market avoidance setting from strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'avoid_flat_markets'):
                    return load_settings().strategy.avoid_flat_markets
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_strategy_cooldown_after_exit_minutes(strategy_name: str, default: int = 5) -> int:
        """Get cooldown period after exit in minutes"""
        # Use a general cooldown setting from strategy config
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'cooldown_after_exit_minutes'):
                    return load_settings().strategy.cooldown_after_exit_minutes
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_symbol_stoploss_cooldown_minutes(strategy_name: str, default: int = 60) -> int:
        """Get per-symbol stop loss cooldown in minutes"""
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'symbol_stoploss_cooldown_minutes'):
                    return load_settings().strategy.symbol_stoploss_cooldown_minutes
            except AttributeError:
                pass
        return default

    @staticmethod
    def get_enable_symbol_stoploss_cooldown(strategy_name: str, default: bool = True) -> bool:
        """Get whether per-symbol stop loss cooldown is enabled"""
        if load_settings().strategy:
            try:
                if hasattr(load_settings().strategy, 'enable_symbol_stoploss_cooldown'):
                    return load_settings().strategy.enable_symbol_stoploss_cooldown
            except AttributeError:
                pass
        return default


# Convenience functions for specific strategies
def get_trend_following_config() -> dict:
    """Get configuration for TrendFollowingStrategy"""
    return {
        'enabled': True,  # Use static value since we don't have dynamic strategy configs
        'max_position_size': StrategyConfig.get_strategy_max_position_size('TREND_FOLLOWING', 0.05),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('TREND_FOLLOWING', 0.5),
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
        'enabled': True,  # Use static value since we don't have dynamic strategy configs
        'max_position_size': StrategyConfig.get_strategy_max_position_size('MEAN_REVERSION', 0.04),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('MEAN_REVERSION', 0.5),
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
        'enabled': True,  # Use static value since we don't have dynamic strategy configs
        'max_position_size': StrategyConfig.get_strategy_max_position_size('VOLATILITY_BREAKOUT', 0.03),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('VOLATILITY_BREAKOUT', 0.5),
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


def get_breakout_config() -> dict:
    """Get configuration for BreakoutStrategy"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('BREAKOUT'),
        'max_position_size': StrategyConfig.get_strategy_max_position_size('BREAKOUT', 0.05),
        'min_confidence': StrategyConfig.get_strategy_min_confidence('BREAKOUT', 0.5),
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
        'min_confidence': StrategyConfig.get_strategy_min_confidence('LIQUIDITY', 0.5),
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
        'min_confidence': StrategyConfig.get_strategy_min_confidence('MTF_TREND', 0.5),
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
    """Get configuration for OIFootprintStrategy (FROZEN PRODUCTION BASELINE)"""
    return {
        'enabled': StrategyConfig.get_strategy_enabled('OI_FOOTPRINT'),
        'status': 'FROZEN_BASELINE',
        'is_frozen': True,
        'tier': 'Tier 2 (Frozen Production Baseline)',
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
        'min_confidence': StrategyConfig.get_strategy_min_confidence('VWAP_REVERSAL', 0.5),
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