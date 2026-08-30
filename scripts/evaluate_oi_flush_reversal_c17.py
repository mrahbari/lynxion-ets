#!/usr/bin/env python3
"""Evaluate preregistered C-17 OI-flush exhaustion reversal."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("DOGEUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT", "AVAXUSDT")
FOLDS = 4
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)


def _mechanics():
    path = Path(__file__).with_name("evaluate_oi_confirmed_impulse_c16.py")
    spec = importlib.util.spec_from_file_location("c16_mechanics", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def causal_features(price: pd.DataFrame, oi: pd.Series) -> pd.DataFrame:
    mechanics = _mechanics()
    frame = mechanics.causal_features(price, oi)[["price_return", "oi_return"]].copy()
    frame["oi_contraction"] = -frame["oi_return"]
    frame["price_threshold"] = frame["price_return"].abs().shift(1).rolling(
        mechanics.WARMUP, min_periods=mechanics.WARMUP
    ).quantile(0.75)
    frame["contraction_threshold"] = frame["oi_contraction"].shift(1).rolling(
        mechanics.WARMUP, min_periods=mechanics.WARMUP
    ).quantile(0.75)
    return frame


def collect_trades(symbol: str, price: pd.DataFrame, oi: pd.Series, funding: pd.Series,
                   fold_boundaries: list[int] | None = None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    mechanics = _mechanics()
    features = causal_features(price, oi)
    eligible = features.dropna()
    trades: list[dict[str, Any]] = []
    last_exit = -1
    census = {"valid_feature_decisions": len(features), "eligible_after_warmup": len(eligible),
              "non_signal": 0, "overlap_rejected": 0, "missing_exit": 0,
              "unresolved_at_fold_end": 0}
    for timestamp, row in eligible.iterrows():
        timestamp = int(timestamp)
        price_return = float(row["price_return"])
        contraction = float(row["oi_contraction"])
        if (abs(price_return) < float(row["price_threshold"]) or contraction <= 0
                or contraction < float(row["contraction_threshold"]) or price_return == 0):
            census["non_signal"] += 1
            continue
        exit_timestamp = timestamp + mechanics.EXIT_SECONDS
        if timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        if exit_timestamp not in price.index:
            census["missing_exit"] += 1
            continue
        fold = None
        if fold_boundaries is not None:
            fold_index = max(index for index in range(FOLDS) if timestamp >= fold_boundaries[index])
            if exit_timestamp >= fold_boundaries[fold_index + 1]:
                census["unresolved_at_fold_end"] += 1
                continue
            fold = fold_index + 1
        direction = -1.0 if price_return > 0 else 1.0
        entry = float(price.loc[timestamp, "open"])
        exit_price = float(price.loc[exit_timestamp, "open"])
        rates = funding.loc[(funding.index > timestamp) & (funding.index <= exit_timestamp)]
        funding_return = -direction * float(rates.sum())
        trade = {"symbol": symbol, "side": "LONG" if direction > 0 else "SHORT", "fold": fold,
                 "decision_timestamp": timestamp, "entry_timestamp": timestamp,
                 "exit_timestamp": exit_timestamp, "price_return_feature": price_return,
                 "oi_contraction_feature": contraction,
                 "price_impulse_ratio": abs(price_return) / float(row["price_threshold"]),
                 "oi_contraction_ratio": contraction / float(row["contraction_threshold"])
                 if row["contraction_threshold"] else None,
                 "entry_price": entry, "exit_price": exit_price,
                 "price_pnl_return": direction * (exit_price - entry) / entry,
                 "funding_return": funding_return}
        trade["gross_return"] = trade["price_pnl_return"] + funding_return
        trades.append(trade); last_exit = exit_timestamp
    return trades, census


def evaluate_sample(price_dir: Path, oi_dir: Path, funding_dir: Path,
                    primary: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mechanics = _mechanics()
    prices = {symbol: mechanics.load_price(price_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    oi = {symbol: mechanics.load_oi(oi_dir / f"{symbol}.csv.gz") for symbol in SYMBOLS}
    funding = {symbol: mechanics.load_funding(funding_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    union = sorted({int(timestamp) for symbol in SYMBOLS
                    for timestamp in causal_features(prices[symbol], oi[symbol]).dropna().index})
    boundaries = None
    if primary:
        boundaries = [union[index * len(union) // FOLDS] for index in range(FOLDS)]
        boundaries.append(union[-1] + 2 * mechanics.DECISION_SECONDS)
    trades: list[dict[str, Any]] = []
    census = {}
    for symbol in SYMBOLS:
        selected, counts = collect_trades(symbol, prices[symbol], oi[symbol], funding[symbol], boundaries)
        trades.extend(selected); census[symbol] = counts
    trades.sort(key=lambda trade: (trade["entry_timestamp"], trade["symbol"]))
    return trades, {"census": census, "fold_boundaries": boundaries}


def build_report(primary_price_dir: Path, reverse_price_dir: Path, oi_dir: Path,
                 funding_dir: Path) -> dict[str, Any]:
    mechanics = _mechanics()
    primary, primary_info = evaluate_sample(primary_price_dir, oi_dir, funding_dir, True)
    reverse, reverse_info = evaluate_sample(reverse_price_dir, oi_dir, funding_dir, False)
    overall = mechanics.metrics(primary); ci = mechanics.day_cluster_ci(primary)
    by_fold = {f"F{fold}": mechanics.metrics([trade for trade in primary if trade["fold"] == fold])
               for fold in range(1, FOLDS + 1)}
    by_side = {side: mechanics.metrics([trade for trade in primary if trade["side"] == side])
               for side in ("LONG", "SHORT")}
    by_symbol = {symbol: mechanics.metrics([trade for trade in primary if trade["symbol"] == symbol])
                 for symbol in SYMBOLS}
    costs = {f"{cost:.3f}": mechanics.metrics(primary, cost) for cost in COSTS}
    reverse_metrics = mechanics.metrics(reverse)
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in primary
                            if trade["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate = [item for item in by_fold.values() if item["n"] >= 80]
    gate = {"adequately_sampled_folds": len(adequate),
            "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate),
            "both_sides_positive_and_sampled": all(item["n"] >= 80 and item["expectancy"] > 0
                                                    for item in by_side.values()),
            "positive_sampled_symbols": sum(item["n"] >= 60 and item["expectancy"] > 0
                                            for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0
            and overall["profit_factor"] is not None and overall["profit_factor"] > 1
            and ci[0] is not None and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["both_sides_positive_and_sampled"] and gate["positive_sampled_symbols"] >= 4
            and concentration is not None and concentration <= 0.35
            and reverse_metrics["n"] >= 200 and reverse_metrics["expectancy"] > 0
            and reverse_metrics["profit_factor"] is not None and reverse_metrics["profit_factor"] > 1
            and costs["0.005"]["expectancy"] > 0)
    gate["verdict"] = "KEEP_FOR_PATH_DEPENDENT_CONFIRMATION" if keep else "REJECT"
    return {"candidate": "C-17", "protocol": "edge-candidate-register-v16",
            "primary": {"overall_funding_inclusive": overall,
                        "overall_price_only": mechanics.metrics(primary, field="price_pnl_return"),
                        "mean_funding_return": float(np.mean([trade["funding_return"] for trade in primary])) if primary else None,
                        "day_cluster_bootstrap_95_ci": ci, "by_fold": by_fold,
                        "by_side": by_side, "by_symbol": by_symbol,
                        "cost_sensitivity": costs, **primary_info},
            "reverse_time": {"overall_funding_inclusive": reverse_metrics, **reverse_info},
            "gate": gate, "limitations": ["Fixed 24-hour exits isolate signal information and are not production exits."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-price-dir", default="data/research/c15/binance_futures_15m")
    parser.add_argument("--reverse-price-dir", default="data/research/c17/reverse_price")
    parser.add_argument("--oi-dir", default="data/research/c17/oi_metrics/normalized")
    parser.add_argument("--funding-dir", default="data/research/c17/funding")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(Path(args.primary_price_dir), Path(args.reverse_price_dir),
                          Path(args.oi_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
