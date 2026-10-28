"""Inner CV failures must not become plausible zero-performance evidence."""

import pandas as pd
import pytest
from unittest.mock import patch

from application.walk_forward.cross_validation_engine import CrossValidationEngine
from application.walk_forward.wfo_orchestrator import WFOOrchestrator


def test_inner_cv_backtest_error_is_not_neutral_metrics():
    class FailingBacktester:
        def run_backtest(self, **_kwargs):
            raise RuntimeError('synthetic CV replay failure')

    engine = CrossValidationEngine(backtester_class=FailingBacktester)
    bars = pd.DataFrame({'close': [100.0]}, index=pd.date_range(
        '2026-01-01', periods=1, freq='h', tz='UTC'))
    with pytest.raises(RuntimeError, match='synthetic CV replay failure'):
        engine._run_single_backtest(bars, lambda row, params: 0, {})


def test_orchestrator_does_not_swallow_inner_cv_error(tmp_path):
    with patch('application.walk_forward.wfo_orchestrator.CSVHistoryLoader'):
        orchestrator = WFOOrchestrator({'results_dir': str(tmp_path)})
    bars = pd.DataFrame({'close': [100.0] * 101}, index=pd.date_range(
        '2026-01-01', periods=101, freq='h', tz='UTC'))

    class FailingCV:
        def run_cross_validation(self, **_kwargs):
            raise RuntimeError('synthetic inner CV failure')

    orchestrator.cv_engine = FailingCV()
    with pytest.raises(RuntimeError, match='synthetic inner CV failure'):
        orchestrator._run_cross_validation(
            {'BTCUSDT': bars}, lambda row, params: 0, {})


def test_orchestrator_rejects_cv_error_result(tmp_path):
    with patch('application.walk_forward.wfo_orchestrator.CSVHistoryLoader'):
        orchestrator = WFOOrchestrator({'results_dir': str(tmp_path)})
    bars = pd.DataFrame({'close': [100.0] * 101}, index=pd.date_range(
        '2026-01-01', periods=101, freq='h', tz='UTC'))

    class InvalidCV:
        def run_cross_validation(self, **_kwargs):
            return {'error': 'no valid folds'}

    orchestrator.cv_engine = InvalidCV()
    with pytest.raises(ValueError, match='no valid folds'):
        orchestrator._run_cross_validation(
            {'BTCUSDT': bars}, lambda row, params: 0, {})
