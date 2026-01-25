from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class ExecutionConfig(BaseModel):
    """
    Configuration for order execution parameters.
    """
    # Original fields
    order_type: str = Field(default="market", description="Type of order (market, limit, etc.)")
    slippage_tolerance: float = Field(default=0.001, ge=0, description="Tolerance for slippage")
    min_order_size: float = Field(default=0.001, gt=0, description="Minimum order size")
    max_order_size: float = Field(default=10.0, gt=0, description="Maximum order size")
    execution_delay: float = Field(default=0.1, ge=0, description="Delay between executions in seconds")

    # Additional execution fields from .env
    limit_slippage: float = Field(default=0.002, description="Limit order slippage")
    price_band_width: float = Field(default=0.005, description="Price band width")
    max_partial_fill_percent: float = Field(default=0.9, description="Maximum partial fill percentage")
    prevent_same_direction_trade_per_symbol: bool = Field(default=True, description="Prevent same direction trades per symbol")
    enable_twap: bool = Field(default=False, description="Enable TWAP")
    enable_vwap: bool = Field(default=False, description="Enable VWAP")
    smart_order_routing: bool = Field(default=False, description="Smart order routing")
    min_order_quantity: float = Field(default=0.001, description="Minimum order quantity")
    order_timeout: int = Field(default=30, description="Order timeout in seconds")

    # Additional fields that may be passed from config loader
    slippage_factor: float = Field(default=0.001, description="Slippage factor")
    slippage_rate: float = Field(default=0.001, description="Slippage rate")

    @validator('slippage_tolerance', 'execution_delay', 'limit_slippage', 'price_band_width',
               'max_partial_fill_percent', 'min_order_size', 'max_order_size', 'min_order_quantity',
               'slippage_factor', 'slippage_rate')
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v

    class Config:
        extra = "forbid"