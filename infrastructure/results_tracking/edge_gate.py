"""Edge gate — E-P5.2 go/no-go decision over the per-strategy edge ledger.

The cheap kill switch: before paying for execution-safety hardening (E-P5.1),
prove that at least one strategy has a *demonstrable* edge net of realistic
costs (the backtester now models spread / partial fills / rejections — T4) on an
adequate sample, segmented by regime (T1/T2).

A (strategy, regime) cell PASSES when it has enough trades and a positive
expectancy with profit factor above threshold. The overall verdict is:

* ``GO``                — at least one cell passes (a real, measured edge exists)
* ``NO_GO``             — cells have adequate data but none clears the bar
* ``INSUFFICIENT_DATA`` — no cell reaches the minimum trade count

This module is pure decision logic (no I/O beyond an optional ledger load), so
it is fully unit-testable offline; the *gate run* that feeds it real backtest
results belongs on the canonical environment with real data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List

from infrastructure.results_tracking.edge_ledger import (
    DEFAULT_LEDGER_PATH,
    EdgeLedger,
    EdgeRecord,
)

GO = "GO"
NO_GO = "NO_GO"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
DIRECTIONAL_NO_GO = "DIRECTIONAL_NO_GO"


@dataclass
class EdgeGateThresholds:
    """Bar a (strategy, regime) cell must clear to count as a measured edge."""
    min_trades: int = 30           # statistical minimum per cell
    min_expectancy: float = 0.0    # per-trade expectancy must EXCEED this (net of costs)
    min_profit_factor: float = 1.0  # PF must EXCEED this
    # DIRECTIONAL_NO_GO: when no cell reaches min_trades (would be
    # INSUFFICIENT_DATA) but the AGGREGATE evidence is decisively negative —
    # which happens when risk-discipline throttles a losing strategy so per-cell
    # counts stay low. Requires an aggregate trade floor so we don't judge on a
    # handful of trades, a clearly-negative aggregate expectancy, and no
    # positive cell.
    directional_min_trades: int = 12       # aggregate (across cells) floor
    directional_max_expectancy: float = 0.0  # aggregate expectancy must be BELOW this


@dataclass
class CellVerdict:
    strategy: str
    regime: str
    trade_count: int
    expectancy: float
    profit_factor: float
    passed: bool
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["profit_factor"] == float("inf"):
            d["profit_factor"] = "inf"
        return d


@dataclass
class EdgeGateVerdict:
    verdict: str
    passing: List[CellVerdict]
    failing: List[CellVerdict]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "summary": self.summary,
            "passing": [c.to_dict() for c in self.passing],
            "failing": [c.to_dict() for c in self.failing],
        }


def _evaluate_cell(rec: EdgeRecord, t: EdgeGateThresholds) -> CellVerdict:
    reasons: List[str] = []
    has_sample = rec.trade_count >= t.min_trades
    if not has_sample:
        reasons.append(f"trades {rec.trade_count} < min {t.min_trades}")
    if not (rec.expectancy > t.min_expectancy):
        reasons.append(f"expectancy {rec.expectancy:.6g} <= min {t.min_expectancy}")
    if not (rec.profit_factor > t.min_profit_factor):
        reasons.append(f"profit_factor {rec.profit_factor:.6g} <= min {t.min_profit_factor}")
    passed = not reasons
    return CellVerdict(
        strategy=rec.strategy,
        regime=rec.regime,
        trade_count=rec.trade_count,
        expectancy=rec.expectancy,
        profit_factor=rec.profit_factor,
        passed=passed,
        reasons=reasons,
    )


def evaluate_edge_gate(
    records: Iterable[EdgeRecord],
    thresholds: EdgeGateThresholds = None,
) -> EdgeGateVerdict:
    """Apply the gate to edge records and return an overall verdict."""
    t = thresholds or EdgeGateThresholds()
    cells = [_evaluate_cell(r, t) for r in records]
    passing = [c for c in cells if c.passed]
    failing = [c for c in cells if not c.passed]

    any_adequate_sample = any(c.trade_count >= t.min_trades for c in cells)

    # Aggregate evidence across all cells (for the directional check).
    total_trades = sum(c.trade_count for c in cells)
    # expectancy is per-trade; weight by trade_count to get aggregate per-trade PnL.
    weighted_pnl = sum(c.expectancy * c.trade_count for c in cells)
    agg_expectancy = weighted_pnl / total_trades if total_trades else 0.0
    no_positive_cell = all(c.expectancy <= t.min_expectancy for c in cells)

    if passing:
        verdict = GO
        summary = (
            f"GO — {len(passing)} of {len(cells)} (strategy,regime) cells show a "
            f"measured edge (expectancy>{t.min_expectancy}, PF>{t.min_profit_factor}, "
            f">={t.min_trades} trades)."
        )
    elif any_adequate_sample:
        verdict = NO_GO
        summary = (
            f"NO_GO — {len(cells)} cells evaluated, adequate sample present, but none "
            f"clears expectancy>{t.min_expectancy} and PF>{t.min_profit_factor} net of "
            f"realistic costs. Do not invest in execution hardening yet."
        )
    elif (total_trades >= t.directional_min_trades
          and agg_expectancy < t.directional_max_expectancy
          and no_positive_cell):
        # No cell reached min_trades (discipline throttled a losing strategy),
        # but the aggregate is decisively negative -> reject directionally.
        verdict = DIRECTIONAL_NO_GO
        summary = (
            f"DIRECTIONAL_NO_GO — no cell reached {t.min_trades} trades (risk "
            f"discipline throttled a losing strategy), but {total_trades} aggregate "
            f"trades show decisively negative expectancy ({agg_expectancy:.4g} < "
            f"{t.directional_max_expectancy}) with no positive cell. Reject: no edge."
        )
    else:
        verdict = INSUFFICIENT_DATA
        summary = (
            f"INSUFFICIENT_DATA — no (strategy,regime) cell reaches {t.min_trades} "
            f"trades and aggregate evidence ({total_trades} trades) is not decisive. "
            f"Gather more data before deciding."
        )
    return EdgeGateVerdict(verdict=verdict, passing=passing, failing=failing, summary=summary)


def evaluate_ledger_file(
    path: str = DEFAULT_LEDGER_PATH,
    thresholds: EdgeGateThresholds = None,
) -> EdgeGateVerdict:
    """Load a persisted edge ledger and evaluate the gate (for the gate run)."""
    ledger = EdgeLedger.load(path)
    return evaluate_edge_gate(ledger.records(), thresholds)
