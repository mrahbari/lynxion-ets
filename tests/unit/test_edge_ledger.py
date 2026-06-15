"""Unit tests for the E-P5.2 T1 per-strategy edge ledger."""
import math

import pytest

from infrastructure.results_tracking.edge_ledger import (
    EdgeLedger,
    EdgeRecord,
    compute_attribution,
    compute_edge_records,
)


def _trade(pnl, regime=None):
    t = {"pnl": pnl}
    if regime is not None:
        t["regime"] = regime
    return t


def test_basic_metrics_and_reconciliation():
    # 3 wins (+10,+20,+30), 2 losses (-5,-15); no break-evens.
    trades = [_trade(10), _trade(20), _trade(30), _trade(-5), _trade(-15)]
    [rec] = compute_edge_records(trades, strategy="rsi")

    assert rec.strategy == "rsi" and rec.regime == "unknown"
    assert rec.trade_count == 5
    assert rec.win_count == 3 and rec.loss_count == 2
    assert rec.win_rate == pytest.approx(3 / 5)
    assert rec.avg_win == pytest.approx(60 / 3)        # 20
    assert rec.avg_loss == pytest.approx(20 / 2)       # 10 (positive magnitude)
    assert rec.avg_rr == pytest.approx(20 / 10)        # 2.0
    assert rec.gross_profit == pytest.approx(60)
    assert rec.gross_loss == pytest.approx(20)
    assert rec.profit_factor == pytest.approx(60 / 20)  # 3.0
    # expectancy = total_pnl / n = (60-20)/5 = 8
    assert rec.expectancy == pytest.approx(8.0)
    assert rec.reconciled is True
    # normalized = expectancy / max(avg_win, avg_loss) = 8 / 20 = 0.4
    assert rec.expectancy_normalized == pytest.approx(0.4)


def test_expectancy_decomposition_holds_with_breakevens():
    # Include a break-even; with include_zero_pnl the decomposition must still
    # reconcile because loss_rate uses #losses/n (not 1 - win_rate).
    trades = [_trade(10), _trade(-4), _trade(0)]
    [rec] = compute_edge_records(trades, strategy="s", include_zero_pnl=True)
    assert rec.trade_count == 3
    # total_pnl = 6 -> expectancy 2.0
    assert rec.expectancy == pytest.approx(6 / 3)
    win_rate = 1 / 3
    loss_rate = 1 / 3
    decomposed = win_rate * rec.avg_win - loss_rate * rec.avg_loss
    assert decomposed == pytest.approx(rec.expectancy)
    assert rec.reconciled is True


def test_zero_pnl_excluded_by_default():
    trades = [_trade(10), _trade(0), _trade(0), _trade(-2)]
    [rec] = compute_edge_records(trades, strategy="s")
    assert rec.trade_count == 2  # break-evens dropped


def test_regime_segmentation():
    trades = [
        _trade(10, "trending_up"), _trade(-5, "trending_up"),
        _trade(8, "ranging"), _trade(-9, "ranging"), _trade(-3, "ranging"),
    ]
    recs = compute_edge_records(trades, strategy="brk")
    by_regime = {r.regime: r for r in recs}
    assert set(by_regime) == {"trending_up", "ranging"}
    assert by_regime["trending_up"].trade_count == 2
    assert by_regime["ranging"].trade_count == 3
    # records sorted by regime
    assert [r.regime for r in recs] == ["ranging", "trending_up"]


def test_profit_factor_infinite_when_no_losses():
    trades = [_trade(5), _trade(7)]
    [rec] = compute_edge_records(trades, strategy="s")
    assert rec.profit_factor == float("inf")
    assert rec.avg_rr == 0.0  # no losses -> undefined R:R reported as 0


def test_persistence_round_trip_handles_inf(tmp_path):
    trades = [_trade(5), _trade(7), _trade(3, "ranging"), _trade(-1, "ranging")]
    ledger = EdgeLedger()
    ledger.update_from_trades(trades, strategy="s")
    path = ledger.save(str(tmp_path / "edge.json"))

    loaded = EdgeLedger.load(path)
    assert {r.regime for r in loaded.records()} == {"unknown", "ranging"}
    # inf profit_factor survives the JSON round-trip via the sentinel
    assert loaded.get("s", "unknown").profit_factor == float("inf")
    assert loaded.get("s", "ranging").profit_factor == pytest.approx(3 / 1)


def test_get_expectancy_lookup_forms():
    trades = [_trade(10), _trade(20), _trade(30), _trade(-5), _trade(-15)]
    ledger = EdgeLedger()
    ledger.update_from_trades(trades, strategy="rsi")

    assert ledger.get_expectancy("rsi") == pytest.approx(0.4)            # normalized
    assert ledger.get_expectancy("rsi", normalized=False) == pytest.approx(8.0)
    assert ledger.get_expectancy("missing") is None
    assert -1.0 <= ledger.get_expectancy("rsi") <= 1.0


def test_update_from_metrics_uses_trades_key():
    metrics = {"trades": [_trade(4), _trade(-2)], "total_trades": 2}
    ledger = EdgeLedger()
    recs = ledger.update_from_metrics(metrics, strategy="golden", regime="ranging")
    assert len(recs) == 1
    assert ledger.get("golden", "ranging").expectancy == pytest.approx(1.0)


def test_attribution_decomposes_and_reconciles():
    # Two strategies across two regimes.
    ledger = EdgeLedger()
    ledger.update_from_trades(
        [_trade(10, "trending_up"), _trade(-4, "ranging")], strategy="A")
    ledger.update_from_trades(
        [_trade(6, "trending_up"), _trade(6, "ranging"), _trade(-2, "ranging")],
        strategy="B")

    report = ledger.attribution_report()
    # total = (10-4) + (6+6-2) = 6 + 10 = 16
    assert report["total_pnl"] == pytest.approx(16.0)
    assert report["total_trades"] == 5
    # by strategy: A=6, B=10
    assert report["by_strategy"]["A"] == pytest.approx(6.0)
    assert report["by_strategy"]["B"] == pytest.approx(10.0)
    # by regime: trending_up=10+6=16... wait: A up=10, B up=6 -> 16; ranging: A=-4,B=4 ->0
    assert report["by_regime"]["trending_up"] == pytest.approx(16.0)
    assert report["by_regime"]["ranging"] == pytest.approx(0.0)
    # both decompositions reconcile to the same total
    assert report["reconciled"] is True
    assert sum(report["by_strategy"].values()) == pytest.approx(report["total_pnl"])
    assert sum(report["by_regime"].values()) == pytest.approx(report["total_pnl"])
    assert report["unattributed_trades"] == 0


def test_attribution_counts_unknown_regime():
    recs = compute_edge_records([_trade(5), _trade(-1)], strategy="A")  # no regime -> unknown
    report = compute_attribution(recs)
    assert report["unknown_regime_trades"] == 2
    assert report["unattributed_trades"] == 0  # has strategy + (unknown) regime


def test_normalized_expectancy_matches_sizer_form_without_breakevens():
    # Demonstrates the ledger value is a drop-in for the probabilistic sizer's
    # own calculate_expectancy normalisation (which uses 1 - win_rate, so this
    # holds when there are no break-even trades).
    sizer = pytest.importorskip(
        "infrastructure.position_sizing.probabilistic_position_sizer"
    ).ProbabilisticPositionSizer()
    trades = [_trade(10), _trade(20), _trade(30), _trade(-5), _trade(-15)]
    [rec] = compute_edge_records(trades, strategy="rsi")
    sizer_norm = sizer.calculate_expectancy(rec.win_rate, rec.avg_win, rec.avg_loss)
    assert rec.expectancy_normalized == pytest.approx(sizer_norm)
