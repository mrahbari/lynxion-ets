"""E2.T2 pilot: the container-wired backtest path is byte-identical to legacy.

Proves the strangler migration of the backtest runner: running through the new
``RunBacktestUseCase`` (constructed from the composition root, with the
``file_repository`` port resolved from the container) produces the same
deterministic per-symbol backtest metrics as calling the legacy
``run_backtest_process`` directly. Uses a committed OHLCV fixture; no network.
"""

from datetime import datetime
from pathlib import Path
import shutil

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("numpy")

try:
    from runner_backtest import run_backtest_process
    from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
    from bootstrap.lifecycle import lifespan
    from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"backtest pilot dependencies unavailable: {exc}", allow_module_level=True)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "ohlcv_sample.csv"

_SYMBOL = "BTCUSDT"
_STRATEGY = "rsi_strategy"
_START = datetime(2023, 1, 1)
_END = datetime(2024, 1, 1)

# Deterministic scalar metrics produced by the backtester (timestamps and
# wall-clock durations in the top-level result are intentionally excluded).
_METRIC_KEYS = [
    "total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown",
    "win_rate", "profit_factor", "total_trades", "winning_trades",
    "losing_trades", "total_volume", "total_fees", "final_equity",
    "initial_capital", "max_drawdown_reached",
]


def _seed_data_dir(base_dir: Path) -> None:
    """Place the fixture where ``FileRepositoryAdapter`` expects the raw file."""
    raw_dir = base_dir / "raw" / "1m"
    raw_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURE, raw_dir / "BTC-USDT.csv")


def _metric_subset(results: dict) -> dict:
    symbol_result = results["backtest_results"][_SYMBOL]
    assert "error" not in symbol_result, f"backtest errored: {symbol_result}"
    return {k: symbol_result[k] for k in _METRIC_KEYS if k in symbol_result}


@pytest.mark.e2e
def test_pilot_path_matches_legacy(tmp_path):
    _seed_data_dir(tmp_path)

    legacy = run_backtest_process(
        symbols=[_SYMBOL],
        strategy_name=_STRATEGY,
        start_date=_START,
        end_date=_END,
        file_repository=FileRepositoryAdapter(base_data_dir=str(tmp_path)),
    )

    with lifespan(base_data_dir=str(tmp_path)) as container:
        use_case = RunBacktestUseCase(
            file_repository=container.resolve("file_repository"),
            backtester_factory=container.resolve("backtester_factory"),
            strategy_provider=container.resolve("backtest_strategy_provider"),
            csv_history_loader=container.resolve("csv_history_loader"),
        )
        new = use_case.execute(BacktestRequest(
            symbols=[_SYMBOL],
            strategy_names=[_STRATEGY],
            start_date=_START,
            end_date=_END,
        ))

    assert legacy["summary"]["successful_backtests"] == 1
    assert new["summary"]["successful_backtests"] == 1
    assert _metric_subset(new) == _metric_subset(legacy)


@pytest.mark.e2e
def test_pilot_path_is_deterministic(tmp_path):
    _seed_data_dir(tmp_path)

    def _run_via_use_case() -> dict:
        with lifespan(base_data_dir=str(tmp_path)) as container:
            uc = RunBacktestUseCase(
                file_repository=container.resolve("file_repository"),
                backtester_factory=container.resolve("backtester_factory"),
                strategy_provider=container.resolve("backtest_strategy_provider"),
                csv_history_loader=container.resolve("csv_history_loader"),
            )
            return uc.execute(BacktestRequest(
                symbols=[_SYMBOL], strategy_names=[_STRATEGY],
                start_date=_START, end_date=_END,
            ))

    assert _metric_subset(_run_via_use_case()) == _metric_subset(_run_via_use_case())
