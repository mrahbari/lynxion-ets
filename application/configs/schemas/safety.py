from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class SafetyConfig(BaseModel):
    """
    Configuration for safety mechanisms and circuit breakers.
    """
    # Original fields
    circuit_breaker_enabled: bool = Field(default=True, description="Whether circuit breaker is enabled")
    max_daily_losses: float = Field(default=5000.0, ge=0, description="Maximum daily losses allowed")
    emergency_stop_enabled: bool = Field(default=True, description="Whether emergency stop is enabled")
    position_limit_per_symbol: float = Field(default=10000.0, gt=0, description="Max position per symbol")
    max_open_positions: int = Field(default=10, ge=1, description="Maximum number of open positions")

    # Additional safety fields from .env
    kill_switch_enabled: bool = Field(default=True, description="Master kill switch")
    emergency_stop_enabled: bool = Field(default=True, description="Emergency stop functionality")
    max_order_size_usd: float = Field(default=10000.0, description="Maximum order size in USD")
    max_daily_orders: int = Field(default=50, description="Maximum daily orders")
    api_rate_limit_buffer: float = Field(default=0.15, description="API rate limit buffer")
    enable_kill_switch: bool = Field(default=True, description="Enable kill switch")

    class Config:
        extra = "forbid"