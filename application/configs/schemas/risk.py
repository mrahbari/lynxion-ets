from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class RiskConfig(BaseModel):
    """
    Configuration for risk management parameters.
    """
    # Original fields
    max_position_size: float = Field(..., gt=0, description="Maximum position size in dollars")
    max_drawdown: float = Field(..., ge=0, le=1, description="Maximum drawdown percentage (0-1)")
    max_risk_per_trade: float = Field(..., ge=0, le=1, description="Maximum risk per trade (0-1)")
    max_correlation: float = Field(..., ge=0, le=1, description="Maximum correlation threshold (0-1)")
    max_leverage: float = Field(..., ge=1, description="Maximum leverage allowed")
    stop_loss_percentage: float = Field(..., ge=0, le=1, description="Stop loss percentage (0-1)")
    take_profit_percentage: float = Field(..., ge=0, description="Take profit percentage (0-1)")

    # Additional risk fields from .env
    max_total_exposure: float = Field(default=0.8, description="Maximum total exposure")
    capital_per_symbol: float = Field(default=0.02, description="Capital per symbol")
    max_exposure: float = Field(default=0.6, description="Maximum exposure")
    per_trade: float = Field(default=0.02, description="Risk per trade")
    max_daily_loss: float = Field(default=0.02, description="Maximum daily loss")
    max_total_positions: int = Field(default=5, description="Maximum total positions")
    max_correlation_between_pos: float = Field(default=0.6, description="Maximum correlation between positions")
    max_sector_exposure: float = Field(default=0.25, description="Maximum sector exposure")
    max_single_asset_exposure: float = Field(default=0.1, description="Maximum single asset exposure")
    emergency_stop_drawdown: float = Field(default=0.15, description="Emergency stop drawdown threshold")
    min_order_size: float = Field(default=0.05, description="Minimum order size")
    max_order_size: float = Field(default=0.05, description="Maximum order size")
    min_position_size: float = Field(default=0.05, description="Minimum position size")
    max_position_concentration: float = Field(default=0.3, description="Maximum position concentration")
    max_portfolio_risk: float = Field(default=0.02, description="Maximum portfolio risk")
    max_position_risk: float = Field(default=0.02, description="Maximum position risk")
    max_drawdown_threshold: float = Field(default=0.3, description="Maximum drawdown threshold")

    # Additional fields that may be passed from config loader
    max_daily_loss_threshold: float = Field(default=0.02, description="Maximum daily loss threshold")
    max_total_positions_limit: int = Field(default=5, description="Maximum total positions limit")
    max_correlation_limit: float = Field(default=0.7, description="Maximum correlation limit")
    max_leverage_limit: float = Field(default=5.0, description="Maximum leverage limit")
    max_order_size_limit: float = Field(default=0.05, description="Maximum order size limit")

    @validator('max_drawdown', 'max_risk_per_trade', 'max_correlation', 'stop_loss_percentage',
               'max_total_exposure', 'capital_per_symbol', 'max_exposure', 'per_trade',
               'max_daily_loss', 'max_correlation_between_pos', 'max_sector_exposure',
               'max_single_asset_exposure', 'emergency_stop_drawdown', 'min_order_size',
               'max_order_size', 'min_position_size', 'max_position_concentration',
               'max_portfolio_risk', 'max_position_risk', 'max_drawdown_threshold')
    def validate_percentages(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Percentage values must be between 0 and 1')
        return v

    class Config:
        extra = "forbid"