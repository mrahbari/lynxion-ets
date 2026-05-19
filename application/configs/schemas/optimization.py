from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class OptimizationConfig(BaseModel):
    """
    Configuration for hyperparameter optimization.
    """
    # Original fields
    optimization_enabled: bool = Field(default=False, description="Whether optimization is enabled")
    population_size: int = Field(default=50, ge=1, description="Size of the population for GA")
    generations: int = Field(default=100, ge=1, description="Number of generations for GA")
    mutation_rate: float = Field(default=0.1, ge=0, le=1, description="Mutation rate for GA")
    crossover_rate: float = Field(default=0.8, ge=0, le=1, description="Crossover rate for GA")

    # Additional optimization fields from .env
    algorithm: str = Field(default="tpe", description="Hyperopt algorithm")
    max_evals: int = Field(default=50, description="Maximum hyperopt evaluations")
    early_stopping_rounds: int = Field(default=5, description="Early stopping rounds")
    validation_split: float = Field(default=0.15, description="Validation split")
    objective_metric: str = Field(default="sharpe_ratio", description="Objective metric")
    min_returns: float = Field(default=0.02, description="Minimum returns")
    min_sharpe_ratio: float = Field(default=0.05, description="Minimum Sharpe ratio")
    max_drawdown: float = Field(default=0.15, description="Maximum drawdown")
    min_win_rate: float = Field(default=0.3, description="Minimum win rate")
    retune_enabled: bool = Field(default=True, description="Retune enabled")
    retune_interval_hours: int = Field(default=3, description="Retune interval in hours")
    retune_performance_threshold: float = Field(default=0.1, description="Retune performance threshold")
    retune_evals_per_retune: int = Field(default=15, description="Retune evals per retune")
    retune_retention_period_days: int = Field(default=5, description="Retune retention period in days")

    @validator('mutation_rate', 'crossover_rate', 'validation_split', 'min_returns', 'min_sharpe_ratio',
               'max_drawdown', 'min_win_rate')
    def validate_rates(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Rate values must be between 0 and 1')
        return v

    class Config:
        extra = "forbid"