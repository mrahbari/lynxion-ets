from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class InfrastructureConfig(BaseModel):
    """
    Configuration for infrastructure settings.
    """
    use_multiprocessing: bool = Field(default=True, description="Use multiprocessing")
    num_workers: int = Field(default=2, description="Number of workers")
    batch_size: int = Field(default=500, description="Batch size")
    memory_profiling: bool = Field(default=False, description="Memory profiling")
    api_timeout: int = Field(default=30, description="API timeout")
    max_workers: int = Field(default=4, description="Maximum workers")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment")
    use_mock_data: bool = Field(default=False, description="Use mock data")

    # Additional fields needed for position sizing service
    edge_estimation_factor: float = Field(default=0.1, description="Edge estimation factor")
    default_asset_volatility: float = Field(default=0.02, description="Default asset volatility")
    max_volatility_impact_on_edge: float = Field(default=0.2, description="Max volatility impact on edge")
    volatility_impact_multiplier: float = Field(default=2.0, description="Volatility impact multiplier")
    max_trend_impact_on_edge: float = Field(default=0.5, description="Max trend impact on edge")
    high_volatility_threshold: float = Field(default=0.05, description="High volatility threshold")
    low_volatility_threshold: float = Field(default=0.01, description="Low volatility threshold")
    high_volatility_win_rate_impact: float = Field(default=0.8, description="High volatility win rate impact")
    low_volatility_win_rate_impact: float = Field(default=0.9, description="Low volatility win rate impact")
    trend_impact_on_win_rate_multiplier: float = Field(default=0.5, description="Trend impact on win rate multiplier")
    max_trend_impact_on_win_rate: float = Field(default=0.2, description="Max trend impact on win rate")
    minimum_win_rate_threshold: float = Field(default=0.4, description="Minimum win rate threshold")
    maximum_win_rate_threshold: float = Field(default=0.9, description="Maximum win rate threshold")
    base_reward_risk_ratio: float = Field(default=1.5, description="Base reward risk ratio")
    min_confidence_rr_factor: float = Field(default=0.7, description="Min confidence RR factor")
    confidence_rr_multiplier: float = Field(default=0.6, description="Confidence RR multiplier")
    min_reward_risk_ratio: float = Field(default=0.5, description="Min reward risk ratio")
    max_reward_risk_ratio: float = Field(default=5.0, description="Max reward risk ratio")
    default_annual_volatility: float = Field(default=0.20, description="Default annual volatility")

    class Config:
        extra = "forbid"