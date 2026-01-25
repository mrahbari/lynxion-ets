from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class AnalyticsConfig(BaseModel):
    """
    Configuration for analytics and reporting.
    """
    analytics_enabled: bool = Field(default=True, description="Whether analytics are enabled")
    report_frequency: str = Field(default="daily", description="How often to generate reports")
    performance_metrics: bool = Field(default=True, description="Whether to collect performance metrics")
    risk_metrics: bool = Field(default=True, description="Whether to collect risk metrics")
    
    @validator('report_frequency')
    def validate_report_frequency(cls, v):
        valid_frequencies = {'realtime', 'minute', 'hourly', 'daily', 'weekly', 'monthly'}
        if v not in valid_frequencies:
            raise ValueError(f'report_frequency must be one of {valid_frequencies}')
        return v
    
    class Config:
        extra = "forbid"