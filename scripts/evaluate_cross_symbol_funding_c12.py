#!/usr/bin/env python3
"""Evaluate preregistered C-12 cross-symbol funding generalization."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


SYMBOLS = ("BNBUSDT", "XRPUSDT", "ADAUSDT")
COSTS = (0.002, 0.003, 0.005)
PRIMARY_COST = 0.003
FOLDS = 4


def _load_c10():
    path = Path(__file__).with_name("evaluate_extreme_negative_funding_c10.py")
    spec = importlib.util.spec_from_file_location("funding_c10_mechanics", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_report(price_dir: Path, funding_dir: Path, candidate: str = "C-12",
                 protocol: str = "edge-candidate-register-v11") -> dict[str, Any]:
    mechanics = _load_c10()
    trades: list[dict[str, Any]] = []
    census: dict[str, dict[str, int]] = {}
    for symbol in SYMBOLS:
        funding = mechanics.causal_funding(funding_dir / f"{symbol}.csv")
        price = mechanics.load_price(price_dir / f"{symbol}.csv")
        selected, counts = mechanics.symbol_trades(symbol, funding, price)
        trades.extend(selected)
        census[symbol] = counts

    overall = mechanics.metrics(trades)
    ci = mechanics.bootstrap_ci(trades)
    by_fold = {
        f"F{fold}": mechanics.metrics([trade for trade in trades if trade["fold"] == fold])
        for fold in range(1, FOLDS + 1)
    }
    by_symbol = {
        symbol: mechanics.metrics([trade for trade in trades if trade["symbol"] == symbol])
        for symbol in SYMBOLS
    }
    by_severity = {
        "1-1.5": mechanics.metrics(
            [trade for trade in trades if trade["severity_ratio"] is not None and trade["severity_ratio"] < 1.5]
        ),
        "1.5-2": mechanics.metrics(
            [
                trade
                for trade in trades
                if trade["severity_ratio"] is not None and 1.5 <= trade["severity_ratio"] < 2
            ]
        ),
        ">=2": mechanics.metrics(
            [trade for trade in trades if trade["severity_ratio"] is not None and trade["severity_ratio"] >= 2]
        ),
        "undefined-zero-threshold": mechanics.metrics(
            [trade for trade in trades if trade["severity_ratio"] is None]
        ),
    }
    positive_pnl = {
        symbol: sum(
            max(0.0, trade["gross_return"] - PRIMARY_COST)
            for trade in trades
            if trade["symbol"] == symbol
        )
        for symbol in SYMBOLS
    }
    total_positive = sum(positive_pnl.values())
    concentration = max(positive_pnl.values(), default=0.0) / total_positive if total_positive else None
    adequate_folds = [item for item in by_fold.values() if item["n"] >= 30]
    positive_adequate_folds = sum(item["expectancy"] > 0 for item in adequate_folds)
    all_symbols_positive_and_sampled = all(
        item["n"] >= 30 and item["expectancy"] > 0 for item in by_symbol.values()
    )
    keep = (
        overall["expectancy"] is not None
        and overall["expectancy"] > 0
        and overall["profit_factor"] is not None
        and overall["profit_factor"] > 1
        and ci[0] is not None
        and ci[0] > 0
        and positive_adequate_folds >= 3
        and all_symbols_positive_and_sampled
        and concentration is not None
        and concentration <= 0.50
    )
    gate = {
        "adequately_sampled_folds": len(adequate_folds),
        "positive_adequate_folds": positive_adequate_folds,
        "all_symbols_positive_and_sampled": all_symbols_positive_and_sampled,
        "max_positive_pnl_symbol_concentration": concentration,
        "verdict": "KEEP_FOR_FURTHER_VALIDATION" if keep else "REJECT",
    }
    return {
        "candidate": candidate,
        "protocol": protocol,
        "symbols": list(SYMBOLS),
        "census": census,
        "overall_funding_inclusive": overall,
        "overall_price_only": mechanics.metrics(trades, field="price_return"),
        "mean_funding_return": float(np.mean([trade["funding_return"] for trade in trades])) if trades else None,
        "bootstrap_95_ci": ci,
        "by_fold": by_fold,
        "by_symbol": by_symbol,
        "by_severity": by_severity,
        "cost_sensitivity": {f"{cost:.3f}": mechanics.metrics(trades, cost) for cost in COSTS},
        "gate": gate,
        "limitations": [
            "Price paths may have been used by other hypotheses; conditional funding membership was frozen separately.",
            "Funding cashflow uses the standard unit-notional rate approximation.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-dir", default="data/research/c09/binance_futures_15m")
    parser.add_argument("--funding-dir", default="data/research/c12/funding")
    parser.add_argument("--candidate", default="C-12")
    parser.add_argument("--protocol", default="edge-candidate-register-v11")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(
        Path(args.price_dir), Path(args.funding_dir), args.candidate, args.protocol
    )
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
