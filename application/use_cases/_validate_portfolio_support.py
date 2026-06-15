"""E5.T5 split: validate_portfolio request DTOs + mock-data helper (shared support)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import numpy as np

from shared.logger import EnhancedLogger
from shared.mock_data_guard import assert_mock_data_allowed


@dataclass
class PortfolioBacktestRequest:
    symbols: List[str]
    strategy_functions: Dict[str, Callable]
    start_date: datetime
    end_date: datetime
    strategy_params: Optional[Dict[str, Dict]] = None
    initial_capital: float = 100000.0
    fee_rate: float = 0.001
    slippage_factor: float = 0.0005
    min_success_rate: float = 0.7


@dataclass
class ComprehensiveValidationRequest:
    symbols: List[str]
    strategy_functions: Dict[str, Callable]
    start_date: datetime
    end_date: datetime
    strategy_params: Optional[Dict[str, Dict]] = None
    initial_capital: float = 100000.0
    fee_rate: float = 0.001
    slippage_factor: float = 0.0005
    min_success_rate: float = 0.7


@dataclass
class ExtendedHorizonRequest:
    horizons: List[int]
    symbols: List[str]
    strategy_functions: Dict[str, Callable]
    strategy_params: Optional[Dict[str, Dict]] = None
    initial_capital: float = 100000.0
    fee_rate: float = 0.001
    slippage_factor: float = 0.0005
    min_success_rate: float = 0.7


def generate_mock_data(symbol: str, days: int = 180) -> pd.DataFrame:
    """Generate mock price data — UNIT-TEST USE ONLY.

    E-P5.2 T3: validation/production must never run on fabricated data. Raises
    unless mock data was explicitly enabled in-code via a
    ``shared.mock_data_guard.allow_mock_data()`` context.
    """
    assert_mock_data_allowed(context="_validate_portfolio_support.generate_mock_data")
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Generate mock OHLCV data
    np.random.seed(hash(symbol) % 2**32)  # Different seed for each symbol
    returns = np.random.normal(0.0005, 0.02, days)  # Daily returns ~0.05% mean, 2% std
    closes = 40000 * np.exp(np.cumsum(returns))  # Starting at ~$40,000

    opens = closes * np.exp(np.random.normal(0, 0.001, days))
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.01, days)))

    volumes = np.random.lognormal(15, 1, days)  # Mock volume data

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df
