from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class WFOConfig(BaseModel):
    """
    Configuration for Walk-Forward Optimization.
    """
    # Original fields
    wfo_enabled: bool = Field(default=False, description="Whether WFO is enabled")
    window_size: int = Field(default=252, ge=1, description="Size of the walk-forward window")
    walk_forward_ratio: float = Field(default=0.7, ge=0, le=1, description="Ratio for walk-forward period")
    out_of_sample_ratio: float = Field(default=0.3, ge=0, le=1, description="Ratio for out-of-sample period")

    # Additional WFO fields from .env
    train_size: int = Field(default=90, description="Training window size in days")
    test_size: int = Field(default=30, description="Testing window size in days")
    step_size: int = Field(default=30, description="Sliding step size in days")
    max_evals: int = Field(default=50, description="Maximum hyperopt evaluations per asset")
    performance_threshold: float = Field(default=0.1, description="Minimum Sharpe ratio to continue WFO period")
    max_drawdown_threshold: float = Field(default=0.15, description="Maximum acceptable drawdown")
    retrain_frequency_days: int = Field(default=30, description="How often to retrain the model in days")
    min_training_points: int = Field(default=30, description="Minimum data points for training window")
    min_testing_points: int = Field(default=10, description="Minimum data points for testing window")
    overfit_threshold: float = Field(default=1.0, description="Threshold for flagging potential overfitting")
    consistency_threshold: float = Field(default=0.6, description="Minimum consistency score to accept optimization")
    pass_rate_threshold: float = Field(default=0.6, description="Minimum pass rate across WFO windows")
    coins: List[str] = Field(default=["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "SOLUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "SHIBUSDT",
                                     "TRXUSDT", "LTCUSDT", "UNIUSDT", "LINKUSDT", "LUNAUSDT", "TONUSDT", "ALGOUSDT", "XLMUSDT", "ETCUSDT", "BCHUSDT",
                                     "NEARUSDT", "FLOWUSDT", "MANAUSDT", "SANDUSDT", "AAVEUSDT"], description="WFO coins")
    sync_days: int = Field(default=180, description="Full refresh every days")
    incremental_days: int = Field(default=2, description="Incremental sync looks back days")
    refresh_interval_hours: int = Field(default=24, description="Schedule incremental sync every hours")
    default_timeframes: List[str] = Field(default=["5m", "15m", "30m", "1h"], description="Timeframes to generate from 1m base")

    # Additional fields that may be passed from config loader
    data_dir: str = Field(default="./data", description="Data directory")
    raw_dir: str = Field(default="./data/history/raw/1m", description="Raw data directory")
    processed_dir: str = Field(default="./data/history/processed", description="Processed data directory")

    @validator('walk_forward_ratio', 'out_of_sample_ratio', 'performance_threshold', 'max_drawdown_threshold',
               'consistency_threshold', 'pass_rate_threshold')
    def validate_ratios(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Ratio values must be between 0 and 1')
        return v

    @validator('out_of_sample_ratio', always=True)
    def validate_ratios_sum(cls, v, values):
        wfr = values.get('walk_forward_ratio')
        if wfr is not None:
            if abs((wfr + v) - 1.0) > 1e-6:  # Account for floating point precision
                raise ValueError('walk_forward_ratio and out_of_sample_ratio must sum to 1.0')
        return v

    class Config:
        extra = "forbid"
