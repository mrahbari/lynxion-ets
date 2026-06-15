"""Golden/characterization test for the canonical backtest path.

Pins the scalar performance metrics produced by ``RealisticBacktester`` on a
tiny committed OHLCV dataset with a fixed, deterministic strategy. Protects
the E3/E5 backtest-engine consolidations from silent behavior drift (F3).

Determinism: the backtester seeds ``np.random`` from a fixed seed; the dataset
carries an explicit ``timestamp`` column so order-cooldown timing is stable;
no network or live data is used.
"""

from datetime import datetime
from pathlib import Path

import pytest

# Heavy / production dependencies: skip the whole module cleanly if they are
# unavailable (e.g. a minimal CI image) so collection stays error-free.
pd = pytest.importorskip("pandas")
pytest.importorskip("numpy")
try:
    from infrastructure.backtest.realistic_backtester import RealisticBacktester
    from infrastructure.backtest.execution_intent import create_execution_intent, OrderSide
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"backtest dependencies unavailable: {exc}", allow_module_level=True)

from golden_utils import assert_golden

DATASET = Path(__file__).resolve().parent.parent / "fixtures" / "golden" / "ohlcv_sample.csv"

# Scalar metrics that characterize the canonical backtest output.
_GOLDEN_KEYS = [
    "total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown",
    "win_rate", "profit_factor", "total_trades", "winning_trades",
    "losing_trades", "total_volume", "total_fees", "final_equity",
    "initial_capital", "max_drawdown_reached",
]


def _load_dataset() -> pd.DataFrame:
    # Mirror the canonical runner: a DatetimeIndex with no `timestamp` column
    # (so the backtester's freshness check uses the index branch).
    df = pd.read_csv(DATASET)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df = df.set_index("timestamp")
    return df


def _golden_strategy(row, params):
    """Deterministic close-vs-SMA strategy emitting infrastructure intents."""
    close = row.get("close")
    sma = row.get("sma_20")
    if close is None or pd.isna(close) or sma is None or pd.isna(sma):
        return None

    atr = row.get("atr")
    if atr is None or pd.isna(atr) or atr <= 0:
        atr = close * 0.01

    if close > sma:
        side, sl, tp = OrderSide.BUY, close - 2 * atr, close + 3 * atr
    elif close < sma:
        side, sl, tp = OrderSide.SELL, close + 2 * atr, close - 3 * atr
    else:
        return None

    ts = row.name  # index label (Timestamp) for this candle
    if not isinstance(ts, datetime):
        ts = pd.Timestamp(ts).to_pydatetime()

    return create_execution_intent(
        side=side, size=0.01, price=float(close), timestamp=ts,
        stop_loss=float(sl), take_profit=float(tp),
        strategy_name="golden", symbol="BTCUSDT",
    )


def _run_backtest():
    bt = RealisticBacktester(initial_capital=10000.0, fee_rate=0.001, slippage_factor=0.0005)
    metrics = bt.run_backtest(
        data=_load_dataset(),
        strategy_function=_golden_strategy,
        strategy_params={"symbol": "BTCUSDT"},
    )
    assert "error" not in metrics, f"Backtest produced no trades: {metrics}"
    return {k: metrics[k] for k in _GOLDEN_KEYS}


@pytest.mark.e2e
def test_backtest_output_matches_golden():
    assert_golden("backtest_metrics.json", _run_backtest())


@pytest.mark.e2e
def test_backtest_is_deterministic_across_runs():
    assert _run_backtest() == _run_backtest()
