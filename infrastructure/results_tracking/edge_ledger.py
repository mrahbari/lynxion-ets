"""Per-strategy edge ledger — E-P5.2 T1 (Edge Measurement).

Computes and persists, from real backtest trade ledgers, each strategy's
measured edge segmented by market regime:

    expectancy, profit factor, win rate, average realised reward:risk, trade count

You cannot allocate capital to (or retire) a strategy without knowing its
expectancy net of costs, so this ledger is the gate input for any live-capital
decision. It consumes the trade list produced by ``RealisticBacktester`` (the
canonical engine after E-P5.2 T3) whose fills are now realistic (T4: spread,
partial fills, rejections, latency), so the measured edge is net of those costs.

Design notes
------------
* **Reconciliation.** Expectancy is computed directly as ``total_pnl / n`` and
  cross-checked against the textbook decomposition
  ``win_rate*avg_win - loss_rate*avg_loss``. We use ``loss_rate = #losses / n``
  (NOT ``1 - win_rate``) so break-even trades are handled exactly and the two
  expressions are identical by construction. We also assert the profit-factor
  identity ``gross_profit - gross_loss == expectancy * n``.
* **Regime segmentation.** Records are keyed by ``(strategy, regime)``. A trade
  may carry a per-trade ``regime`` field; otherwise the run-level ``regime``
  passed to the builder is used (default ``"unknown"``). The ``RegimeType``
  enum is intentionally treated as an opaque string here — there are competing
  enum definitions (consolidation is deferred, see the deferred backlog DB-4),
  so the ledger stays decoupled from any specific enum.
* **Normalised expectancy** mirrors the form the probabilistic sizer expects
  (``-1..1``) so a ledger value is a drop-in for the sizer's
  ``strategy_expectancy`` input.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_REGIME = "unknown"
DEFAULT_LEDGER_PATH = os.path.join("data", "results_storage", "edge_ledger.json")


@dataclass
class EdgeRecord:
    """Measured edge for one (strategy, regime) cell."""
    strategy: str
    regime: str
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float            # win_count / trade_count
    avg_win: float             # mean of positive pnls (0 if none)
    avg_loss: float            # mean of |negative pnls| (positive magnitude, 0 if none)
    avg_rr: float              # realised reward:risk = avg_win / avg_loss (0 if no losses)
    gross_profit: float
    gross_loss: float          # positive magnitude
    profit_factor: float       # gross_profit / gross_loss (inf if no loss and profit > 0)
    expectancy: float          # per-trade pnl units = total_pnl / trade_count
    expectancy_normalized: float  # -1..1, sizer form
    reconciled: bool           # expectancy decomposition + PF identity hold

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # JSON cannot represent inf; persist profit_factor as a string sentinel.
        if d["profit_factor"] == float("inf"):
            d["profit_factor"] = "inf"
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EdgeRecord":
        d = dict(d)
        if d.get("profit_factor") == "inf":
            d["profit_factor"] = float("inf")
        return cls(**d)


def _normalize_expectancy(expectancy: float, avg_win: float, avg_loss: float) -> float:
    """Map per-trade expectancy to the sizer's -1..1 scale.

    Mirrors ``ProbabilisticPositionSizer.calculate_expectancy`` normalisation
    without coupling to that (deprecated) module.
    """
    scale = max(avg_win, avg_loss)
    if scale <= 0:
        return 0.0
    return max(-1.0, min(1.0, expectancy / scale))


def _trade_pnl(trade: Dict[str, Any]) -> Optional[float]:
    pnl = trade.get("pnl")
    if pnl is None:
        return None
    try:
        return float(pnl)
    except (TypeError, ValueError):
        return None


def compute_edge_records(
    trades: Iterable[Dict[str, Any]],
    *,
    strategy: str,
    default_regime: str = DEFAULT_REGIME,
    regime_key: str = "regime",
    include_zero_pnl: bool = False,
) -> List[EdgeRecord]:
    """Compute per-(strategy, regime) edge records from a trade list.

    Args:
        trades: trade dicts (e.g. ``RealisticBacktester`` metrics["trades"]),
            each with a numeric ``pnl`` and optionally a ``regime`` field.
        strategy: the strategy these trades belong to (a backtest run is one
            strategy).
        default_regime: regime label for trades lacking ``regime_key``.
        regime_key: per-trade field carrying the regime label.
        include_zero_pnl: if True, break-even (pnl == 0) trades count toward
            ``trade_count`` (and dilute win/loss rates). Defaults to False so
            only realised closes are measured (entry records with pnl==0 are
            excluded).

    Returns:
        One EdgeRecord per observed (strategy, regime), sorted by regime.
    """
    buckets: Dict[str, List[float]] = {}
    for trade in trades:
        pnl = _trade_pnl(trade)
        if pnl is None:
            continue
        if pnl == 0.0 and not include_zero_pnl:
            continue
        regime = str(trade.get(regime_key) or default_regime)
        buckets.setdefault(regime, []).append(pnl)

    records: List[EdgeRecord] = []
    for regime in sorted(buckets):
        pnls = buckets[regime]
        n = len(pnls)
        wins = [p for p in pnls if p > 0]
        losses = [-p for p in pnls if p < 0]  # positive magnitudes
        win_count, loss_count = len(wins), len(losses)
        gross_profit = float(sum(wins))
        gross_loss = float(sum(losses))
        total_pnl = gross_profit - gross_loss

        win_rate = win_count / n if n else 0.0
        loss_rate = loss_count / n if n else 0.0
        avg_win = gross_profit / win_count if win_count else 0.0
        avg_loss = gross_loss / loss_count if loss_count else 0.0
        avg_rr = avg_win / avg_loss if avg_loss > 0 else 0.0

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float("inf") if gross_profit > 0 else 0.0

        expectancy = total_pnl / n if n else 0.0
        expectancy_normalized = _normalize_expectancy(expectancy, avg_win, avg_loss)

        # Reconciliation: the textbook decomposition must equal the direct mean,
        # and the profit-factor identity must hold (within float tolerance).
        decomposed = win_rate * avg_win - loss_rate * avg_loss
        pf_identity = (gross_profit - gross_loss) - (expectancy * n)
        reconciled = abs(decomposed - expectancy) < 1e-9 and abs(pf_identity) < 1e-6

        records.append(EdgeRecord(
            strategy=strategy,
            regime=regime,
            trade_count=n,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_rr=avg_rr,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            expectancy_normalized=expectancy_normalized,
            reconciled=reconciled,
        ))
    return records


def compute_attribution(records: Iterable["EdgeRecord"]) -> Dict[str, Any]:
    """P&L attribution by strategy and regime — E-P5.2 T2.

    Decomposes realised P&L (gross_profit - gross_loss per cell) by strategy and
    by regime. Both decompositions must independently sum to the same total
    (``reconciled``). ``unattributed_trades`` counts trades with no strategy or
    no regime label; trades in the "unknown" regime bucket are reported
    separately (they are attributed — just to an undetermined regime).
    """
    by_strategy: Dict[str, float] = {}
    by_regime: Dict[str, float] = {}
    cells = []
    total_pnl = 0.0
    total_trades = 0
    unknown_regime_trades = 0
    unattributed_trades = 0

    for r in records:
        pnl = r.gross_profit - r.gross_loss
        total_pnl += pnl
        total_trades += r.trade_count
        by_strategy[r.strategy] = by_strategy.get(r.strategy, 0.0) + pnl
        by_regime[r.regime] = by_regime.get(r.regime, 0.0) + pnl
        cells.append({
            "strategy": r.strategy,
            "regime": r.regime,
            "pnl": pnl,
            "trade_count": r.trade_count,
        })
        if r.regime == DEFAULT_REGIME:
            unknown_regime_trades += r.trade_count
        if not r.strategy or not r.regime:
            unattributed_trades += r.trade_count

    reconciled = (
        abs(sum(by_strategy.values()) - total_pnl) < 1e-6
        and abs(sum(by_regime.values()) - total_pnl) < 1e-6
    )
    return {
        "total_pnl": total_pnl,
        "total_trades": total_trades,
        "by_strategy": by_strategy,
        "by_regime": by_regime,
        "cells": cells,
        "reconciled": reconciled,
        "unattributed_trades": unattributed_trades,
        "unknown_regime_trades": unknown_regime_trades,
    }


class EdgeLedger:
    """A collection of EdgeRecords keyed by (strategy, regime), with persistence."""

    def __init__(self, records: Optional[Iterable[EdgeRecord]] = None):
        self._records: Dict[tuple, EdgeRecord] = {}
        if records:
            for r in records:
                self.upsert(r)

    @staticmethod
    def _key(strategy: str, regime: str) -> tuple:
        return (strategy, regime)

    def upsert(self, record: EdgeRecord) -> None:
        self._records[self._key(record.strategy, record.regime)] = record

    def update_from_trades(
        self,
        trades: Iterable[Dict[str, Any]],
        *,
        strategy: str,
        default_regime: str = DEFAULT_REGIME,
        regime_key: str = "regime",
        include_zero_pnl: bool = False,
    ) -> List[EdgeRecord]:
        """Compute records for a backtest run and merge them into the ledger."""
        recs = compute_edge_records(
            trades,
            strategy=strategy,
            default_regime=default_regime,
            regime_key=regime_key,
            include_zero_pnl=include_zero_pnl,
        )
        for r in recs:
            self.upsert(r)
        return recs

    def update_from_metrics(self, metrics: Dict[str, Any], *, strategy: str,
                            regime: str = DEFAULT_REGIME, **kwargs) -> List[EdgeRecord]:
        """Merge records computed from a RealisticBacktester metrics dict.

        Trades carrying their own ``regime`` field segment accordingly; the
        rest fall under ``regime``.
        """
        return self.update_from_trades(
            metrics.get("trades", []), strategy=strategy, default_regime=regime, **kwargs
        )

    def get(self, strategy: str, regime: str = DEFAULT_REGIME) -> Optional[EdgeRecord]:
        return self._records.get(self._key(strategy, regime))

    def get_expectancy(self, strategy: str, regime: str = DEFAULT_REGIME,
                       *, normalized: bool = True) -> Optional[float]:
        """Computed expectancy for (strategy, regime), or None if unmeasured.

        Returned in the sizer's normalised ``-1..1`` form by default so it is a
        drop-in for ``strategy_expectancy``. NOTE: as of E-P5.2 T1 the
        probabilistic sizer's expectancy input has no live caller (the canonical
        sizing engine does not consume it); wiring this value into live sizing
        is deferred — see the edge-gate / deferred backlog.
        """
        rec = self.get(strategy, regime)
        if rec is None:
            return None
        return rec.expectancy_normalized if normalized else rec.expectancy

    def records(self) -> List[EdgeRecord]:
        return list(self._records.values())

    def attribution_report(self) -> Dict[str, Any]:
        """P&L attribution by strategy and regime across all ledger records."""
        return compute_attribution(self._records.values())

    def strategies(self) -> List[str]:
        return sorted({k[0] for k in self._records})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "records": [r.to_dict() for r in self._records.values()],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EdgeLedger":
        return cls(EdgeRecord.from_dict(rd) for rd in d.get("records", []))

    def save(self, path: str = DEFAULT_LEDGER_PATH) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, sort_keys=True)
        return path

    @classmethod
    def load(cls, path: str = DEFAULT_LEDGER_PATH) -> "EdgeLedger":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
