from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class PositionSizingConfig(BaseModel):
    """
    Configuration for position sizing methods.
    """
    fixed_position_size_enabled: bool = Field(default=True, description="Fixed position size enabled")
    fixed_position_amount: float = Field(default=4.0, description="Fixed position amount")
    default_account_balance: float = Field(default=10000.0, description="Default account balance")
    fixed_fractional_default_percentage: float = Field(default=0.02, description="Fixed fractional default percentage")
    fixed_fractional_percentage: float = Field(default=0.02, description="Fixed fractional percentage")
    fixed_fractional_risk_per_unit: float = Field(default=0.02, description="Fixed fractional risk per unit")
    kelly_default_percentage: float = Field(default=0.02, description="Kelly default percentage")
    kelly_fraction: float = Field(default=0.25, description="Kelly fraction")
    kelly_max_position_size: float = Field(default=0.05, description="Kelly max position size")
    kelly_minimum_edge: float = Field(default=0.1, description="Kelly minimum edge")
    kelly_var_confidence_level: float = Field(default=0.3, description="Kelly VAR confidence level")
    kelly_var_margin_of_safety_percentage: float = Field(default=0.05, description="Kelly VAR margin of safety percentage")
    kelly_var_max_position_with_var: float = Field(default=0.1, description="Kelly VAR max position with VAR")
    kelly_var_stress_test_multiplier: float = Field(default=1.5, description="Kelly VAR stress test multiplier")
    martingale_base_risk_percentage: float = Field(default=0.02, description="Martingale base risk percentage")
    martingale_max_progression_levels: int = Field(default=5, description="Martingale max progression levels")
    martingale_max_total_exposure_multiplier: float = Field(default=1.5, description="Martingale max total exposure multiplier")
    martingale_progression_multiplier: float = Field(default=1.5, description="Martingale progression multiplier")
    optimal_f_calculation_error_default: float = Field(default=0.1, description="Optimal F calculation error default")
    optimal_f_default_percentage: float = Field(default=0.02, description="Optimal F default percentage")
    optimal_f_error_fallback_percentage: float = Field(default=0.02, description="Optimal F error fallback percentage")
    optimal_f_max_per_trade: float = Field(default=0.05, description="Optimal F max per trade")
    method: str = Field(default="risk_percentagerisk_percentage", description="Position sizing method")

    # Additional fields needed for position sizing service
    atr_multiplier: float = Field(default=2.0, description="ATR multiplier for stop distance")
    atr_fixed_dollar_risk: float = Field(default=1000.0, description="ATR fixed dollar risk")
    atr_min_multiple: float = Field(default=1.5, description="ATR minimum multiple")
    atr_max_portfolio_percent: float = Field(default=0.10, description="ATR max portfolio percent")
    atr_default_percentage: float = Field(default=0.015, description="ATR default percentage")
    volatility_target: float = Field(default=0.15, description="Volatility target")
    volatility_max_portfolio_percent: float = Field(default=0.15, description="Volatility max portfolio percent")
    volatility_error_default_percentage: float = Field(default=0.01, description="Volatility error default percentage")
    volatility_target_percentage: float = Field(default=0.15, description="Volatility target percentage")
    volatility_max_portfolio_allocation: float = Field(default=0.15, description="Volatility max portfolio allocation")
    volatility_max_rr_impact: float = Field(default=0.5, description="Volatility max RR impact")
    volatility_rr_multiplier: float = Field(default=10.0, description="Volatility RR multiplier")
    atr_to_volatility_multiplier: float = Field(default=1.0, description="ATR to volatility multiplier")

    class Config:
        extra = "forbid"