#!/usr/bin/env python3
"""
ValidatePortfolioUseCase - application-layer orchestration for portfolio-level
validation pipelines: comprehensive portfolio backtest, comprehensive hedge-fund
validation, and extended-horizon validation.

Orchestration moved here from runner_comprehensive_portfolio_backtest.py,
runner_comprehensive_validation.py and runner_extended_horizon_validation.py
(E2.T4). The portfolio backtester is constructed via an injected factory and the
CSV history loader / data-integrity checker are injected ports, so this use case
never instantiates infrastructure classes directly.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import numpy as np

from shared.logger import EnhancedLogger
from application.use_cases._validate_portfolio_support import (
    PortfolioBacktestRequest, ComprehensiveValidationRequest, ExtendedHorizonRequest, generate_mock_data,
)
from application.use_cases._validate_portfolio_flows import _ValidatePortfolioFlowsMixin


class ValidatePortfolioUseCase(_ValidatePortfolioFlowsMixin):
    """Run portfolio validation pipelines using container-injected ports."""

    def __init__(self,
                 settings,
                 portfolio_backtester_factory: Optional[Callable[[float, float, float], Any]] = None,
                 csv_history_loader: Optional[Any] = None,
                 data_integrity_checker: Optional[Any] = None,
                 capital_allocator_factory: Optional[Callable[..., Any]] = None,
                 monte_carlo_analyzer: Optional[Callable[..., Any]] = None,
                 kill_switch_factory: Optional[Callable[..., Any]] = None,
                 portfolio_walk_forward_validator: Optional[Callable[..., Any]] = None) -> None:
        # Settings injected by the composition root (E1.T5); the inherited
        # _ValidatePortfolioFlowsMixin reads off self._settings instead of importing
        # bootstrap.settings.loaders.
        self._settings = settings
        self._portfolio_backtester_factory = portfolio_backtester_factory
        self._csv_history_loader = csv_history_loader
        self._data_integrity_checker = data_integrity_checker
        self._capital_allocator_factory = capital_allocator_factory
        self._monte_carlo_analyzer = monte_carlo_analyzer
        self._kill_switch_factory = kill_switch_factory
        self._portfolio_walk_forward_validator = portfolio_walk_forward_validator

    def _build_backtester(self, initial_capital: float, fee_rate: float, slippage_factor: float):
        return self._portfolio_backtester_factory(initial_capital, fee_rate, slippage_factor)

    def _get_csv_loader(self):
        return self._csv_history_loader

    def _get_integrity_checker(self):
        return self._data_integrity_checker
