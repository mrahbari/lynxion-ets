from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class StrategyConfig(BaseModel):
    """
    Configuration for trading strategies.
    """
    # Original fields
    strategy_name: str = Field(..., description="Name of the strategy")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    enabled: bool = Field(default=True, description="Whether the strategy is enabled")
    timeframe: str = Field(default="1m", description="Timeframe for the strategy")
    lookback_period: int = Field(default=50, ge=1, description="Number of periods to look back")

    # Additional strategy fields from .env
    default_strategy: str = Field(default="crypto_breakout", description="Default strategy")
    risk_per_trade: float = Field(default=0.02, description="Risk per trade")
    max_position_size: float = Field(default=0.05, description="Maximum position size")
    min_volume_filter: float = Field(default=10000.0, description="Minimum volume filter")
    signal_cooldown_minutes: int = Field(default=30, description="Signal cooldown in minutes")
    min_confidence_threshold: float = Field(default=0.5, description="Minimum confidence threshold")
    high_confidence_threshold: float = Field(default=0.7, description="High confidence threshold")
    neutral_buffer: float = Field(default=0.03, description="Neutral buffer")
    strong_directional_bias_threshold: float = Field(default=0.3, description="Strong directional bias threshold")
    anomaly_ml_contamination: float = Field(default=0.1, description="Anomaly ML contamination")
    atr_default_percentage: float = Field(default=0.02, description="ATR default percentage")
    atr_fixed_dollar_risk: float = Field(default=21.0, description="ATR fixed dollar risk")
    atr_max_portfolio_percent: float = Field(default=0.05, description="ATR max portfolio percent")
    atr_min_multiple: float = Field(default=1.0, description="ATR minimum multiple")
    atr_multiplier: float = Field(default=1.5, description="ATR multiplier")
    atr_to_volatility_multiplier: float = Field(default=1.5, description="ATR to volatility multiplier")
    base_reward_risk_ratio: float = Field(default=0.3, description="Base reward risk ratio")
    confidence_rr_multiplier: float = Field(default=0.3, description="Confidence RR multiplier")
    default_annual_volatility: float = Field(default=0.2, description="Default annual volatility")
    default_asset_volatility: float = Field(default=0.2, description="Default asset volatility")
    edge_estimation_factor: float = Field(default=0.55, description="Edge estimation factor")
    engine_confidence_threshold: float = Field(default=0.3, description="Engine confidence threshold")
    enabled_engines: List[str] = Field(default=["engine1"], description="Enabled engines")
    high_volatility_threshold: float = Field(default=0.3, description="High volatility threshold")
    high_volatility_win_rate_impact: float = Field(default=0.1, description="High volatility win rate impact")
    low_volatility_threshold: float = Field(default=0.3, description="Low volatility threshold")
    low_volatility_win_rate_impact: float = Field(default=0.05, description="Low volatility win rate impact")
    maximum_win_rate_threshold: float = Field(default=0.3, description="Maximum win rate threshold")
    max_reward_risk_ratio: float = Field(default=0.3, description="Maximum reward risk ratio")
    max_trend_impact_on_edge: float = Field(default=0.1, description="Maximum trend impact on edge")
    max_trend_impact_on_win_rate: float = Field(default=0.1, description="Maximum trend impact on win rate")
    max_volatility_impact_on_edge: float = Field(default=0.1, description="Maximum volatility impact on edge")
    min_confidence_rr_factor: float = Field(default=0.3, description="Minimum confidence RR factor")
    min_reward_risk_ratio: float = Field(default=1.5, description="Minimum reward risk ratio")
    ml_weights_enabled: bool = Field(default=True, description="ML weights enabled")
    regime_detection_enabled: bool = Field(default=True, description="Regime detection enabled")
    signal_fusion_enabled: bool = Field(default=True, description="Signal fusion enabled")
    signal_threshold: float = Field(default=0.3, description="Signal threshold")
    target_volatility: float = Field(default=0.2, description="Target volatility")
    trend_impact_on_win_rate_multiplier: float = Field(default=1.5, description="Trend impact on win rate multiplier")
    trend_max_rr_impact: float = Field(default=0.1, description="Trend max RR impact")
    trend_mtf_long_period: int = Field(default=50, description="Trend MTF long period")
    trend_mtf_medium_period: int = Field(default=50, description="Trend MTF medium period")
    trend_mtf_short_period: int = Field(default=50, description="Trend MTF short period")
    trend_rr_multiplier: float = Field(default=1.5, description="Trend RR multiplier")
    var_name: str = Field(default="default_var", description="VAR name")
    volatility_error_default_percentage: float = Field(default=0.1, description="Volatility error default percentage")
    volatility_impact_multiplier: float = Field(default=1.5, description="Volatility impact multiplier")
    volatility_max_portfolio_allocation: float = Field(default=0.05, description="Volatility max portfolio allocation")
    volatility_max_portfolio_percent: float = Field(default=0.05, description="Volatility max portfolio percent")
    volatility_max_rr_impact: float = Field(default=0.1, description="Volatility max RR impact")
    volatility_rr_multiplier: float = Field(default=1.5, description="Volatility RR multiplier")
    volatility_target: float = Field(default=0.2, description="Volatility target")
    volatility_target_percentage: float = Field(default=0.2, description="Volatility target percentage")
    minimum_win_rate_threshold: float = Field(default=0.3, description="Minimum win rate threshold")
    opportunity_score_confidence_weight: float = Field(default=0.4, description="Opportunity score confidence weight")
    opportunity_score_dominance_weight: float = Field(default=0.2, description="Opportunity score dominance weight")
    opportunity_score_position_size_weight: float = Field(default=0.15, description="Opportunity score position size weight")
    opportunity_score_reward_risk_weight: float = Field(default=0.15, description="Opportunity score reward risk weight")
    opportunity_score_regime_bonus: float = Field(default=0.15, description="Opportunity score regime bonus")
    enable_shorting: bool = Field(default=False, description="Enable shorting")

    # Directional Control
    direction_mode: str = Field(default="BOTH", description="Directional mode for signal generation ('BOTH', 'LONG_ONLY', 'SHORT_ONLY')")

    @validator('direction_mode')
    def validate_direction_mode(cls, v):
        allowed = {"BOTH", "LONG_ONLY", "SHORT_ONLY"}
        if v not in allowed:
            raise ValueError(f"direction_mode must be one of {allowed}, got '{v}'")
        return v

    # Volatility-Adapted SL/TP Parameters
    atr_period: int = Field(default=14, description="ATR period for volatility calculations")
    atr_sl_multiplier: float = Field(default=1.5, description="ATR stop loss multiplier")
    min_stop_distance_percent: float = Field(default=0.8, description="Minimum stop distance in percent (e.g. 0.8)")
    enable_dynamic_tp: bool = Field(default=True, description="Enable dynamic take profit expansion")
    reject_low_rr_setup: bool = Field(default=True, description="Reject setup if Reward-to-Risk ratio is below minimum")
    symbol_stoploss_cooldown_minutes: int = Field(default=60, description="Per-symbol stop loss cooldown in minutes")
    enable_symbol_stoploss_cooldown: bool = Field(default=True, description="Enable per-symbol stop loss cooldown")

    class Config:
        extra = "forbid"