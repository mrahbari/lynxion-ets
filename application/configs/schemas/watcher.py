from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class WatcherConfig(BaseModel):
    """
    Configuration for watcher systems.
    """
    polling_interval_seconds: int = Field(default=15, description="Polling interval in seconds")
    max_symbols_to_monitor: int = Field(default=10, description="Maximum symbols to monitor")
    data_refresh_interval_minutes: int = Field(default=5, description="Data refresh interval in minutes")
    risk_threshold: float = Field(default=0.02, description="Risk threshold")
    min_confidence_threshold: float = Field(default=0.15, description="Minimum confidence threshold")
    max_confidence_with_patterns: float = Field(default=0.2, description="Maximum confidence with patterns")
    min_price_change_threshold: float = Field(default=0.0001, description="Minimum price change threshold")
    max_confidence_with_movement: float = Field(default=0.25, description="Maximum confidence with movement")
    neutral_confidence: float = Field(default=0.05, description="Neutral confidence")
    pattern_weight: float = Field(default=0.3, description="Pattern weight")
    momentum_weight: float = Field(default=0.2, description="Momentum weight")
    high_volatility_boost: float = Field(default=0.1, description="High volatility boost")
    low_volatility_boost: float = Field(default=0.02, description="Low volatility boost")
    normal_volatility_boost: float = Field(default=0.05, description="Normal volatility boost")
    min_confidence_when_signals_detected: float = Field(default=0.08,
                                                        description="Minimum confidence when signals detected")
    max_confidence_cap: float = Field(default=0.85, description="Maximum confidence cap")
    momentum_lookback_period: int = Field(default=7, description="Momentum lookback period")
    momentum_sensitivity_factor: float = Field(default=7.0, description="Momentum sensitivity factor")
    market_pulse_watcher_enabled: bool = Field(default=True, description="Market pulse watcher enabled")
    volatility_watcher_enabled: bool = Field(default=True, description="Volatility watcher enabled")
    trend_mtf_watcher_enabled: bool = Field(default=True, description="Trend MTF watcher enabled")
    anomaly_ml_watcher_enabled: bool = Field(default=True, description="Anomaly ML watcher enabled")
    orderflow_ws_watcher_enabled: bool = Field(default=True, description="Orderflow WS watcher enabled")
    cmc_screener_enabled: bool = Field(default=True, description="CMC screener enabled")
    funding_rate_watcher_enabled: bool = Field(default=True, description="Funding rate watcher enabled")
    liquidity_watcher_enabled: bool = Field(default=True, description="Liquidity watcher enabled")
    historical_candle_watcher_enabled: bool = Field(default=True, description="Historical candle watcher enabled")
    tick_watcher_enabled: bool = Field(default=False, description="Tick watcher enabled")
    broker_config: str = Field(
        default="MarketPulse:bingx,Volatility:bingx,TrendMTF:bingx,AnomalyML:bingx,OrderFlow:bingx",
        description="Watcher broker configuration")
    target_broker_market_pulse: str = Field(default="bingx", description="Target broker for market pulse")
    target_broker_volatility: str = Field(default="bingx", description="Target broker for volatility")
    target_broker_trend_mtf: str = Field(default="bingx", description="Target broker for trend MTF")
    target_broker_anomaly_ml: str = Field(default="bingx", description="Target broker for anomaly ML")
    target_broker_orderflow_ws: str = Field(default="bingx", description="Target broker for orderflow WS")
    target_broker_funding_rate: str = Field(default="bingx", description="Target broker for funding rate")
    target_broker_liquidity: str = Field(default="bingx", description="Target broker for liquidity")
    target_broker_historical_candle: str = Field(default="bingx", description="Target broker for historical candle")
    target_broker_tick_watcher: str = Field(default="bingx", description="Target broker for tick watcher")
    use_improved_watchers: bool = Field(default=True, description="Use improved watchers")
    auto_enable_watchers: bool = Field(default=True, description="Auto enable watchers")
    enabled_watchers: List[str] = Field(default=["watcher1"], description="Enabled watchers")
    update_freq: int = Field(default=3030, description="Update frequency")
    lookback: int = Field(default=2020, description="Lookback period")
    early_exit_momentum_threshold: float = Field(default=0.0001, description="Early exit momentum threshold")
    early_exit_trend_confidence_threshold: float = Field(default=0.0001,
                                                         description="Early exit trend confidence threshold")
    early_exit_volatility_threshold: float = Field(default=0.0001, description="Early exit volatility threshold")

    # Specific watcher configuration fields
    market_pulse_lookback_period: int = Field(default=20, description="Market pulse lookback period")
    volatility_lookback_period: int = Field(default=20, description="Volatility lookback period")
    trend_mtf_lookback_period: int = Field(default=20, description="Trend MTF lookback period")
    anomaly_ml_lookback_period: int = Field(default=50, description="Anomaly ML lookback period")
    orderflow_ws_lookback_period: int = Field(default=100, description="Orderflow WS lookback period")
    cmc_screener_lookback_period: int = Field(default=20, description="CMC screener lookback period")
    funding_rate_lookback_period: int = Field(default=24, description="Funding rate lookback period")
    liquidity_lookback_period: int = Field(default=20, description="Liquidity lookback period")
    historical_candle_lookback_period: int = Field(default=50, description="Historical candle lookback period")
    tick_lookback_period: int = Field(default=1000, description="Tick lookback period")

    # Specific watcher min confidence thresholds
    market_pulse_min_confidence_threshold: float = Field(default=0.05, description="Market pulse min confidence threshold")
    volatility_min_confidence_threshold: float = Field(default=0.05, description="Volatility min confidence threshold")
    trend_mtf_min_confidence_threshold: float = Field(default=0.05, description="Trend MTF min confidence threshold")
    anomaly_ml_min_confidence_threshold: float = Field(default=0.05, description="Anomaly ML min confidence threshold")
    orderflow_ws_min_confidence_threshold: float = Field(default=0.05, description="Orderflow WS min confidence threshold")
    cmc_screener_min_confidence_threshold: float = Field(default=0.05, description="CMC screener min confidence threshold")
    funding_rate_min_confidence_threshold: float = Field(default=0.05, description="Funding rate min confidence threshold")
    liquidity_min_confidence_threshold: float = Field(default=0.05, description="Liquidity min confidence threshold")
    historical_candle_min_confidence_threshold: float = Field(default=0.05, description="Historical candle min confidence threshold")
    tick_min_confidence_threshold: float = Field(default=0.05, description="Tick min confidence threshold")

    # Specific watcher max confidence thresholds
    market_pulse_max_confidence_threshold: float = Field(default=0.95, description="Market pulse max confidence threshold")
    volatility_max_confidence_threshold: float = Field(default=0.95, description="Volatility max confidence threshold")
    trend_mtf_max_confidence_threshold: float = Field(default=0.95, description="Trend MTF max confidence threshold")
    anomaly_ml_max_confidence_threshold: float = Field(default=0.95, description="Anomaly ML max confidence threshold")
    orderflow_ws_max_confidence_threshold: float = Field(default=0.95, description="Orderflow WS max confidence threshold")
    cmc_screener_max_confidence_threshold: float = Field(default=0.95, description="CMC screener max confidence threshold")
    funding_rate_max_confidence_threshold: float = Field(default=0.95, description="Funding rate max confidence threshold")
    liquidity_max_confidence_threshold: float = Field(default=0.95, description="Liquidity max confidence threshold")
    historical_candle_max_confidence_threshold: float = Field(default=0.95, description="Historical candle max confidence threshold")
    tick_max_confidence_threshold: float = Field(default=0.95, description="Tick max confidence threshold")

    # Adaptive sensitivity settings
    market_pulse_adaptive_sensitivity: bool = Field(default=False, description="Market pulse adaptive sensitivity")
    volatility_adaptive_sensitivity: bool = Field(default=False, description="Volatility adaptive sensitivity")
    trend_mtf_adaptive_sensitivity: bool = Field(default=False, description="Trend MTF adaptive sensitivity")
    anomaly_ml_adaptive_sensitivity: bool = Field(default=False, description="Anomaly ML adaptive sensitivity")
    orderflow_ws_adaptive_sensitivity: bool = Field(default=False, description="Orderflow WS adaptive sensitivity")
    cmc_screener_adaptive_sensitivity: bool = Field(default=False, description="CMC screener adaptive sensitivity")
    funding_rate_adaptive_sensitivity: bool = Field(default=False, description="Funding rate adaptive sensitivity")
    liquidity_adaptive_sensitivity: bool = Field(default=False, description="Liquidity adaptive sensitivity")
    historical_candle_adaptive_sensitivity: bool = Field(default=False, description="Historical candle adaptive sensitivity")
    tick_adaptive_sensitivity: bool = Field(default=False, description="Tick adaptive sensitivity")

    # Specific watcher pattern weights
    market_pulse_pattern_weight: float = Field(default=0.4, description="Market pulse pattern weight")
    volatility_pattern_weight: float = Field(default=0.4, description="Volatility pattern weight")
    trend_mtf_pattern_weight: float = Field(default=0.4, description="Trend MTF pattern weight")
    anomaly_ml_pattern_weight: float = Field(default=0.4, description="Anomaly ML pattern weight")
    orderflow_ws_pattern_weight: float = Field(default=0.4, description="Orderflow WS pattern weight")
    cmc_screener_pattern_weight: float = Field(default=0.4, description="CMC screener pattern weight")
    funding_rate_pattern_weight: float = Field(default=0.4, description="Funding rate pattern weight")
    liquidity_pattern_weight: float = Field(default=0.4, description="Liquidity pattern weight")
    historical_candle_pattern_weight: float = Field(default=0.4, description="Historical candle pattern weight")
    tick_pattern_weight: float = Field(default=0.4, description="Tick pattern weight")

    # Specific watcher momentum weights
    market_pulse_momentum_weight: float = Field(default=0.3, description="Market pulse momentum weight")
    volatility_momentum_weight: float = Field(default=0.3, description="Volatility momentum weight")
    trend_mtf_momentum_weight: float = Field(default=0.3, description="Trend MTF momentum weight")
    anomaly_ml_momentum_weight: float = Field(default=0.3, description="Anomaly ML momentum weight")
    orderflow_ws_momentum_weight: float = Field(default=0.3, description="Orderflow WS momentum weight")
    cmc_screener_momentum_weight: float = Field(default=0.3, description="CMC screener momentum weight")
    funding_rate_momentum_weight: float = Field(default=0.3, description="Funding rate momentum weight")
    liquidity_momentum_weight: float = Field(default=0.3, description="Liquidity momentum weight")
    historical_candle_momentum_weight: float = Field(default=0.3, description="Historical candle momentum weight")
    tick_momentum_weight: float = Field(default=0.3, description="Tick momentum weight")

    # Specific watcher high volatility boosts
    market_pulse_high_volatility_boost: float = Field(default=0.2, description="Market pulse high volatility boost")
    volatility_high_volatility_boost: float = Field(default=0.2, description="Volatility high volatility boost")
    trend_mtf_high_volatility_boost: float = Field(default=0.2, description="Trend MTF high volatility boost")
    anomaly_ml_high_volatility_boost: float = Field(default=0.2, description="Anomaly ML high volatility boost")
    orderflow_ws_high_volatility_boost: float = Field(default=0.2, description="Orderflow WS high volatility boost")
    cmc_screener_high_volatility_boost: float = Field(default=0.2, description="CMC screener high volatility boost")
    funding_rate_high_volatility_boost: float = Field(default=0.2, description="Funding rate high volatility boost")
    liquidity_high_volatility_boost: float = Field(default=0.2, description="Liquidity high volatility boost")
    historical_candle_high_volatility_boost: float = Field(default=0.2, description="Historical candle high volatility boost")
    tick_high_volatility_boost: float = Field(default=0.2, description="Tick high volatility boost")

    # Specific watcher low volatility boosts
    market_pulse_low_volatility_boost: float = Field(default=0.05, description="Market pulse low volatility boost")
    volatility_low_volatility_boost: float = Field(default=0.05, description="Volatility low volatility boost")
    trend_mtf_low_volatility_boost: float = Field(default=0.05, description="Trend MTF low volatility boost")
    anomaly_ml_low_volatility_boost: float = Field(default=0.05, description="Anomaly ML low volatility boost")
    orderflow_ws_low_volatility_boost: float = Field(default=0.05, description="Orderflow WS low volatility boost")
    cmc_screener_low_volatility_boost: float = Field(default=0.05, description="CMC screener low volatility boost")
    funding_rate_low_volatility_boost: float = Field(default=0.05, description="Funding rate low volatility boost")
    liquidity_low_volatility_boost: float = Field(default=0.05, description="Liquidity low volatility boost")
    historical_candle_low_volatility_boost: float = Field(default=0.05, description="Historical candle low volatility boost")
    tick_low_volatility_boost: float = Field(default=0.05, description="Tick low volatility boost")

    # Specific watcher normal volatility boosts
    market_pulse_normal_volatility_boost: float = Field(default=0.1, description="Market pulse normal volatility boost")
    volatility_normal_volatility_boost: float = Field(default=0.1, description="Volatility normal volatility boost")
    trend_mtf_normal_volatility_boost: float = Field(default=0.1, description="Trend MTF normal volatility boost")
    anomaly_ml_normal_volatility_boost: float = Field(default=0.1, description="Anomaly ML normal volatility boost")
    orderflow_ws_normal_volatility_boost: float = Field(default=0.1, description="Orderflow WS normal volatility boost")
    cmc_screener_normal_volatility_boost: float = Field(default=0.1, description="CMC screener normal volatility boost")
    funding_rate_normal_volatility_boost: float = Field(default=0.1, description="Funding rate normal volatility boost")
    liquidity_normal_volatility_boost: float = Field(default=0.1, description="Liquidity normal volatility boost")
    historical_candle_normal_volatility_boost: float = Field(default=0.1, description="Historical candle normal volatility boost")
    tick_normal_volatility_boost: float = Field(default=0.1, description="Tick normal volatility boost")

    # Specific watcher momentum lookback periods
    market_pulse_momentum_lookback_period: int = Field(default=10, description="Market pulse momentum lookback period")
    volatility_momentum_lookback_period: int = Field(default=10, description="Volatility momentum lookback period")
    trend_mtf_momentum_lookback_period: int = Field(default=10, description="Trend MTF momentum lookback period")
    anomaly_ml_momentum_lookback_period: int = Field(default=10, description="Anomaly ML momentum lookback period")
    orderflow_ws_momentum_lookback_period: int = Field(default=10, description="Orderflow WS momentum lookback period")
    cmc_screener_momentum_lookback_period: int = Field(default=10, description="CMC screener momentum lookback period")
    funding_rate_momentum_lookback_period: int = Field(default=10, description="Funding rate momentum lookback period")
    liquidity_momentum_lookback_period: int = Field(default=10, description="Liquidity momentum lookback period")
    historical_candle_momentum_lookback_period: int = Field(default=10, description="Historical candle momentum lookback period")
    tick_momentum_lookback_period: int = Field(default=10, description="Tick momentum lookback period")

    # Specific watcher momentum sensitivity factors
    market_pulse_momentum_sensitivity_factor: float = Field(default=10.0, description="Market pulse momentum sensitivity factor")
    volatility_momentum_sensitivity_factor: float = Field(default=10.0, description="Volatility momentum sensitivity factor")
    trend_mtf_momentum_sensitivity_factor: float = Field(default=10.0, description="Trend MTF momentum sensitivity factor")
    anomaly_ml_momentum_sensitivity_factor: float = Field(default=10.0, description="Anomaly ML momentum sensitivity factor")
    orderflow_ws_momentum_sensitivity_factor: float = Field(default=10.0, description="Orderflow WS momentum sensitivity factor")
    cmc_screener_momentum_sensitivity_factor: float = Field(default=10.0, description="CMC screener momentum sensitivity factor")
    funding_rate_momentum_sensitivity_factor: float = Field(default=10.0, description="Funding rate momentum sensitivity factor")
    liquidity_momentum_sensitivity_factor: float = Field(default=10.0, description="Liquidity momentum sensitivity factor")
    historical_candle_momentum_sensitivity_factor: float = Field(default=10.0, description="Historical candle momentum sensitivity factor")
    tick_momentum_sensitivity_factor: float = Field(default=10.0, description="Tick momentum sensitivity factor")

    # Trend MTF specific fields
    trend_mtf_short_period: int = Field(default=5, description="Trend MTF short period")
    trend_mtf_medium_period: int = Field(default=15, description="Trend MTF medium period")
    trend_mtf_long_period: int = Field(default=30, description="Trend MTF long period")

    # Anomaly ML specific fields
    anomaly_ml_contamination: float = Field(default=0.1, description="Anomaly ML contamination")

    class Config:
        extra = "forbid"
