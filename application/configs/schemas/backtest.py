from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class BacktestConfig(BaseModel):
    """
    Configuration for backtesting.
    """
    initial_capital: float = Field(default=10000.0, description="Initial capital for backtests")
    fee_rate: float = Field(default=0.001, description="Trading fee rate")
    slippage_factor: float = Field(default=0.0005, description="Slippage factor")
    risk_per_trade: float = Field(default=0.02, description="Risk per trade")
    end_date: str = Field(default="2026-01-18", description="Backtest end date")
    start_date: str = Field(default="2025-01-01", description="Backtest start date")
    benchmark_symbol: str = Field(default="BTCUSDT", description="Benchmark symbol")
    commission_rate: float = Field(default=0.001, description="Commission rate")
    
    class Config:
        extra = "forbid"