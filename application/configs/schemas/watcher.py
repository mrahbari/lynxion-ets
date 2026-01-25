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

    class Config:
        extra = "forbid"
