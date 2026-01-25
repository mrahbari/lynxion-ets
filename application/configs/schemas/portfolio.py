from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class PortfolioConfig(BaseModel):
    """
    Configuration for portfolio management.
    """
    rebalance_frequency: str = Field(default="daily", description="Rebalance frequency")
    correlation_consensus_weight: float = Field(default=0.5, description="Correlation consensus weight")
    correlation_confidence_weight: float = Field(default=0.3, description="Correlation confidence weight")
    correlation_base_percentage: float = Field(default=0.5, description="Correlation base percentage")
    correlation_default_percentage: float = Field(default=0.5, description="Correlation default percentage")
    correlation_diversification_factor: float = Field(default=0.7, description="Correlation diversification factor")
    correlation_max_correlation: float = Field(default=0.7, description="Correlation max correlation")
    correlation_portfolio_impact_threshold: float = Field(default=0.3, description="Correlation portfolio impact threshold")
    
    class Config:
        extra = "forbid"