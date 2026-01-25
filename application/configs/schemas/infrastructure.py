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
    
    class Config:
        extra = "forbid"