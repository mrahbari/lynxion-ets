"""Edge-gate runner (composition layer) — E-P5.2.

Bridges backtest results to the infrastructure edge ledger + gate so the
interface CLI stays free of direct infrastructure imports (R1). The composition
root legitimately imports infrastructure; the interface only deals in plain
dicts returned here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from infrastructure.results_tracking.edge_gate import (
    EdgeGateThresholds,
    evaluate_edge_gate,
)
from infrastructure.results_tracking.edge_ledger import DEFAULT_LEDGER_PATH, EdgeLedger


def set_forensic_logging(enabled: bool) -> None:
    """Toggle the forensic decision logger. Offline edge measurement does not
    need the live audit trail, and the per-decision validation/serialisation it
    performs dominates backtest runtime — disabling it makes long-window gate
    runs tractable. Lives here (composition layer) so the interface CLI need not
    import infrastructure (R1)."""
    from infrastructure.logging.forensic_logger import forensic_logger
    forensic_logger.enabled = enabled


def _thresholds(min_trades: int, min_expectancy: float,
                min_profit_factor: float) -> EdgeGateThresholds:
    return EdgeGateThresholds(
        min_trades=min_trades,
        min_expectancy=min_expectancy,
        min_profit_factor=min_profit_factor,
    )


def build_ledger_from_results(results_by_strategy: Dict[str, Dict[str, Any]]) -> EdgeLedger:
    """Aggregate per-strategy backtest results (across symbols) into an EdgeLedger.

    ``results_by_strategy`` maps strategy name -> a RunBacktestUseCase result
    dict (``{"backtest_results": {symbol: metrics}, ...}``). All trades for a
    strategy are pooled before computing its per-regime edge records.
    """
    ledger = EdgeLedger()
    for strategy, result in results_by_strategy.items():
        pooled = []
        for _symbol, metrics in (result.get("backtest_results") or {}).items():
            if isinstance(metrics, dict) and metrics.get("trades"):
                pooled.extend(metrics["trades"])
        if pooled:
            ledger.update_from_trades(pooled, strategy=strategy)
    return ledger


def build_and_evaluate(
    results_by_strategy: Dict[str, Dict[str, Any]],
    *,
    save_path: Optional[str] = DEFAULT_LEDGER_PATH,
    min_trades: int = 30,
    min_expectancy: float = 0.0,
    min_profit_factor: float = 1.0,
) -> Dict[str, Any]:
    """Build the edge ledger from results, optionally persist it, and evaluate
    the gate. Returns ``{"verdict": ..., "ledger_path": ..., "attribution": ...}``
    as plain data (no infrastructure types leak to the caller)."""
    ledger = build_ledger_from_results(results_by_strategy)
    ledger_path = ledger.save(save_path) if save_path else None
    verdict = evaluate_edge_gate(
        ledger.records(), _thresholds(min_trades, min_expectancy, min_profit_factor)
    )
    return {
        "verdict": verdict.to_dict(),
        "attribution": ledger.attribution_report(),
        "ledger_path": ledger_path,
    }


def evaluate_saved_ledger(
    path: str = DEFAULT_LEDGER_PATH,
    *,
    min_trades: int = 30,
    min_expectancy: float = 0.0,
    min_profit_factor: float = 1.0,
) -> Dict[str, Any]:
    """Load a persisted edge ledger and evaluate the gate. Returns plain data."""
    ledger = EdgeLedger.load(path)
    verdict = evaluate_edge_gate(
        ledger.records(), _thresholds(min_trades, min_expectancy, min_profit_factor)
    )
    return {
        "verdict": verdict.to_dict(),
        "attribution": ledger.attribution_report(),
        "ledger_path": path,
    }
