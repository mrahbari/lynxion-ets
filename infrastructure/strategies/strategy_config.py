"""
Standardized Configuration for Strategies
Provides consistent access to strategy configuration through the Configs system
"""
import os
from typing import Union
from bootstrap.settings.loaders import load_settings


def _norm_strategy(name) -> str:
    return str(name or "").lower().replace("_", "").replace("-", "").strip()


def is_strategy_allowlisted(strategy_name) -> bool:
    """Operator allowlist (env STRATEGY_ALLOWLIST, comma-separated). Empty/unset = all allowed."""
    allow = {_norm_strategy(x) for x in os.getenv("STRATEGY_ALLOWLIST", "").split(",") if x.strip()}
    return not allow or _norm_strategy(strategy_name) in allow


class StrategyConfig:
    """
    Standardized configuration class for all strategies.
    Provides consistent access to strategy configuration through the Configs system.
    """

    # Common strategy settings
    @staticmethod
    def get_strategy_enabled(strategy_name: str) -> bool:
        """A strategy is enabled unless STRATEGY_ALLOWLIST is set and does not name it.

        Names are compared case-insensitively ignoring '_' and '-', so registry keys
        ('vwap_reversal'), adapter names ('VWAPReversal') and config keys ('VWAP_REVERSAL') match.
        """
        return is_strategy_allowlisted(strategy_name)

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
        'liquidity': '5m', 'vwap_reversal': '15m',   # session-VWAP 2-sigma setup (E21, 2026-11-24)
        'breakout': '15m',
        'trend_following': '1h', 'trend_follow': '1h', 'mean_reversion': '1h',
        'oi_footprint': '1h',
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
        'timeframe': StrategyConfig.get_strategy_timeframe('VWAP_REVERSAL', '15m'),
        'parameters': {
            'vwap_period': 89,
            'std_dev_multiplier': 1.5,
            'reversal_threshold': 0.01
        }
    }