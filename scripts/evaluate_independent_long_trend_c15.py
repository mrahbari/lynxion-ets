#!/usr/bin/env python3
"""Evaluate preregistered C-15 independent long-only trend holdout."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


SYMBOLS = ("DOGEUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT", "AVAXUSDT")
FOLDS = 4
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)


def _mechanics():
    path = Path(__file__).with_name("evaluate_time_series_momentum_c14.py")
    spec = importlib.util.spec_from_file_location("c14_mechanics", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_report(data_dir: Path) -> dict[str, Any]:
    mechanics = _mechanics()
    bars = {symbol: mechanics.load_bars(data_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    decisions = sorted({int(row.decision_timestamp) for frame in bars.values()
                        for row in mechanics.monthly_decisions(frame).itertuples()})
    boundaries = [decisions[index * len(decisions) // FOLDS] for index in range(FOLDS)]
    boundaries.append(decisions[-1] + 32 * 86400)
    trades: list[dict[str, Any]] = []
    census = {}
    for symbol, frame in bars.items():
        selected, counts = mechanics.collect_trades(symbol, frame, boundaries, long_only=True)
        trades.extend(selected)
        census[symbol] = counts
    trades.sort(key=lambda trade: (trade["entry_timestamp"], trade["symbol"]))
    overall = mechanics.metrics(trades)
    ci = mechanics.month_cluster_ci(trades)
    by_fold = {f"F{fold}": mechanics.metrics([trade for trade in trades if trade["fold"] == fold])
               for fold in range(1, FOLDS + 1)}
    by_symbol = {symbol: mechanics.metrics([trade for trade in trades if trade["symbol"] == symbol])
                 for symbol in SYMBOLS}
    cost_sensitivity = {f"{cost:.3f}": mechanics.metrics(trades, cost) for cost in COSTS}
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in trades
                            if trade["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate_folds = [item for item in by_fold.values() if item["n"] >= 20]
    gate = {"adequately_sampled_folds": len(adequate_folds),
            "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate_folds),
            "positive_sampled_symbols": sum(item["n"] >= 15 and item["expectancy"] > 0
                                            for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0
            and overall["profit_factor"] is not None and overall["profit_factor"] > 1
            and ci[0] is not None and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["positive_sampled_symbols"] >= 4 and concentration is not None
            and concentration <= 0.35 and cost_sensitivity["0.005"]["expectancy"] > 0)
    gate["verdict"] = "KEEP_FOR_PATH_DEPENDENT_CONFIRMATION" if keep else "REJECT"
    return {"candidate": "C-15", "protocol": "edge-candidate-register-v14",
            "overall": overall, "month_cluster_bootstrap_95_ci": ci, "by_fold": by_fold,
            "by_symbol": by_symbol, "cost_sensitivity": cost_sensitivity,
            "census": census, "fold_boundaries": boundaries, "gate": gate,
            "limitations": ["Funding is unavailable and unmodeled.",
                            "Fixed 28-day exits isolate signal information and are not production exits."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/research/c15/binance_futures_15m")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(Path(args.data_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
