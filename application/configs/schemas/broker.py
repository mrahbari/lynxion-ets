from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from decimal import Decimal


class BrokerConfig(BaseModel):
    """
    Configuration for broker connectivity and settings.
    """
    # Original fields
    api_key: str = Field(..., description="Broker API key")
    secret_key: str = Field(..., description="Broker secret key")
    testnet: bool = Field(default=True, description="Whether to use testnet")
    broker_name: str = Field(..., description="Name of the broker")
    paper_trading: bool = Field(default=True, description="Whether to use paper trading")

    # Additional broker fields from .env
    bingx_api_key: str = Field(default="", description="BingX API key")
    bingx_secret_key: str = Field(default="", description="BingX secret key")
    bingx_order_placement_enabled: bool = Field(default=False, description="Enable BingX order placement")
    bingx_testnet: bool = Field(default=True, description="BingX testnet mode")
    default_broker: str = Field(default="bingx", description="Default broker")
    binance_api_key: str = Field(default="", description="Binance API key")
    binance_secret_key: str = Field(default="", description="Binance secret key")
    binance_order_placement_enabled: bool = Field(default=False, description="Enable Binance order placement")
    binance_testnet: bool = Field(default=True, description="Binance testnet mode")
    mexc_api_key: str = Field(default="", description="MEXC API key")
    mexc_secret_key: str = Field(default="", description="MEXC secret key")
    mexc_order_placement_enabled: bool = Field(default=False, description="Enable MEXC order placement")
    mexc_testnet: bool = Field(default=True, description="MEXC testnet mode")
    phemex_api_key: str = Field(default="", description="Phemex API key")
    phemex_secret_key: str = Field(default="", description="Phemex secret key")
    phemex_order_placement_enabled: bool = Field(default=False, description="Enable Phemex order placement")
    phemex_testnet: bool = Field(default=True, description="Phemex testnet mode")
    binance_api_url: str = Field(default="https://api.binance.com", description="Binance API URL")
    binance_retry_attempts: int = Field(default=3, description="Binance retry attempts")
    binance_rate_limit_delay: float = Field(default=0.1, description="Binance rate limit delay")
    bingx_passphrase: str = Field(default="", description="BingX passphrase")
    enabled_brokers: List[str] = Field(default=["bingx"], description="Enabled brokers")

    class Config:
        extra = "forbid"  # Forbid extra fields not defined in the model