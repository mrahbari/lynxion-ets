"""Unit tests for the E-P5.2 edge gate (go/no-go)."""
import pytest

from infrastructure.results_tracking.edge_gate import (
    GO,
    NO_GO,
    INSUFFICIENT_DATA,
    DIRECTIONAL_NO_GO,
    EdgeGateThresholds,
    evaluate_edge_gate,
)
from infrastructure.results_tracking.edge_ledger import EdgeLedger


def _ledger_from(strategy, trades_by_regime):
    ledger = EdgeLedger()
    for regime, trades in trades_by_regime.items():
        ledger.update_from_trades(
            [{"pnl": p, "regime": regime} for p in trades], strategy=strategy
        )
    return ledger


def _winning_trades(n):
    # n trades, ~60% wins of +2, rest losses of -1 -> positive expectancy, PF=3
    wins = [2.0] * int(n * 0.6)
    losses = [-1.0] * (n - len(wins))
    return wins + losses


def test_go_when_a_cell_has_edge():
    ledger = _ledger_from("rsi", {"trending_up": _winning_trades(40)})
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == GO
    assert len(v.passing) == 1
    assert v.passing[0].strategy == "rsi" and v.passing[0].regime == "trending_up"


def test_insufficient_data_when_too_few_trades():
    ledger = _ledger_from("rsi", {"ranging": _winning_trades(10)})
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == INSUFFICIENT_DATA
    assert not v.passing


def test_no_go_when_sample_ok_but_no_edge():
    # 40 trades, net-negative (losers dominate) -> adequate sample, no edge
    losers = [1.0] * 10 + [-2.0] * 30
    ledger = _ledger_from("rsi", {"ranging": losers})
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == NO_GO
    assert not v.passing and v.failing
    assert any("expectancy" in r for r in v.failing[0].reasons)


def test_profit_factor_threshold_enforced():
    # positive but marginal: PF just above 1, expectancy tiny positive.
    # 40 trades: 20 wins +1.0, 20 losses -0.9 -> PF = 20/18 ~1.11, exp = +0.05
    trades = [1.0] * 20 + [-0.9] * 20
    ledger = _ledger_from("rsi", {"trending_up": trades})
    # Demand PF > 1.5 -> should fail on profit_factor
    v = evaluate_edge_gate(
        ledger.records(),
        EdgeGateThresholds(min_trades=30, min_profit_factor=1.5),
    )
    assert v.verdict == NO_GO
    assert any("profit_factor" in r for r in v.failing[0].reasons)


def test_mixed_cells_go_if_any_passes():
    ledger = EdgeLedger()
    ledger.update_from_trades(
        [{"pnl": p, "regime": "trending_up"} for p in _winning_trades(40)], strategy="A")
    ledger.update_from_trades(
        [{"pnl": p, "regime": "ranging"} for p in ([1.0] * 5 + [-2.0] * 35)], strategy="A")
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == GO
    assert {c.regime for c in v.passing} == {"trending_up"}
    assert {c.regime for c in v.failing} == {"ranging"}


def test_directional_no_go_when_throttled_and_decisively_negative():
    # No cell reaches min_trades (30), but aggregate is decisively negative with
    # an adequate aggregate floor and no positive cell -> DIRECTIONAL_NO_GO.
    losers = [-2.0] * 8 + [1.0] * 2  # 10 trades/cell, net negative, <30
    ledger = _ledger_from("rsi", {"trending_down": losers, "ranging": losers})
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == DIRECTIONAL_NO_GO
    assert not v.passing


def test_insufficient_when_throttled_but_too_few_aggregate_trades():
    # Below the aggregate directional floor (default 12) -> stays INSUFFICIENT.
    ledger = _ledger_from("rsi", {"ranging": [-2.0] * 3 + [1.0]})  # 4 trades total
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == INSUFFICIENT_DATA


def test_directional_no_go_not_triggered_when_a_cell_is_positive():
    # Aggregate negative but one cell is net-positive -> not a clean directional
    # reject; stays INSUFFICIENT (no cell has the sample to confirm GO either).
    ledger = EdgeLedger()
    ledger.update_from_trades([{"pnl": p, "regime": "up"} for p in ([3.0] * 6 + [-1.0] * 2)], strategy="rsi")
    ledger.update_from_trades([{"pnl": p, "regime": "down"} for p in ([-5.0] * 9)], strategy="rsi")
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    assert v.verdict == INSUFFICIENT_DATA  # a positive cell blocks directional reject


def test_verdict_serializes_with_inf_pf():
    ledger = _ledger_from("rsi", {"trending_up": [1.0] * 35})  # no losses -> PF inf
    v = evaluate_edge_gate(ledger.records(), EdgeGateThresholds(min_trades=30))
    d = v.to_dict()
    assert d["verdict"] == GO
    assert d["passing"][0]["profit_factor"] == "inf"
