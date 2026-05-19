from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class FusionConfig(BaseModel):
    """
    Configuration for signal fusion.
    """
    method: str = Field(default="weighted_average", description="Fusion method")
    weight_decay_rate: float = Field(default=0.05, description="Weight decay rate")
    min_correlation_score: float = Field(default=0.1, description="Minimum correlation score")
    max_signals_per_asset: int = Field(default=5, description="Maximum signals per asset")
    
    class Config:
        extra = "forbid"