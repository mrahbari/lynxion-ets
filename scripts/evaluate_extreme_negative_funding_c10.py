#!/usr/bin/env python3
"""Evaluate preregistered C-10 extreme-negative funding rebound."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT")
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)
FOLDS = 4


def causal_funding(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    frame["funding_rate"] = pd.to_numeric(frame["funding_rate"], errors="coerce")
    frame["threshold"] = frame["funding_rate"].shift(1).rolling(365, min_periods=365).quantile(0.10)
    return frame


def load_price(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=["timestamp", "open"]).sort_values("timestamp").drop_duplicates("timestamp")
    return frame.set_index("timestamp")


def symbol_trades(symbol: str, funding: pd.DataFrame, price: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    eligible = funding.loc[funding["threshold"].notna()].reset_index(drop=True)
    timestamps = eligible["timestamp"].astype(int).tolist()
    boundaries = [timestamps[index * len(timestamps) // FOLDS] for index in range(FOLDS)] + [timestamps[-1] + 1]
    price_times = price.index.to_numpy(dtype=int)
    trades = []; last_exit = -1
    census = {"eligible_settlements": len(eligible), "non_signal": 0, "overlap_rejected": 0,
              "unresolved_at_fold_end": 0, "missing_price": 0}
    for row in eligible.itertuples(index=False):
        timestamp, rate, threshold = int(row.timestamp), float(row.funding_rate), float(row.threshold)
        if rate >= 0 or rate > threshold:
            census["non_signal"] += 1
            continue
        entry_position = int(np.searchsorted(price_times, timestamp, side="right"))
        exit_position = entry_position + 96
        if entry_position >= len(price_times) or exit_position >= len(price_times):
            census["missing_price"] += 1
            continue
        entry_timestamp, exit_timestamp = int(price_times[entry_position]), int(price_times[exit_position])
        if entry_timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        fold = max(index for index in range(FOLDS) if timestamp >= boundaries[index])
        if exit_timestamp >= boundaries[fold + 1]:
            census["unresolved_at_fold_end"] += 1
            continue
        entry, exit_price = float(price.iloc[entry_position]["open"]), float(price.iloc[exit_position]["open"])
        subsequent = funding.loc[(funding["timestamp"] > entry_timestamp) & (funding["timestamp"] <= exit_timestamp), "funding_rate"]
        funding_return = -float(subsequent.sum())
        price_return = (exit_price - entry) / entry
        trades.append({"symbol": symbol, "fold": fold + 1, "signal_timestamp": timestamp,
                       "entry_timestamp": entry_timestamp, "exit_timestamp": exit_timestamp,
                       "funding_rate": rate, "threshold": threshold,
                       "severity_ratio": abs(rate) / abs(threshold) if threshold else None,
                       "entry_price": entry, "exit_price": exit_price, "price_return": price_return,
                       "funding_return": funding_return, "gross_return": price_return + funding_return})
        last_exit = exit_timestamp
    return trades, census


def metrics(trades: list[dict[str, Any]], cost: float = PRIMARY_COST, field: str = "gross_return") -> dict[str, Any]:
    values = np.asarray([trade[field] - cost for trade in trades], dtype=float)
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None, "max_drawdown": None}
    wins, losses = values[values > 0], values[values <= 0]
    average_win = float(wins.mean()) if len(wins) else None; average_loss = float(losses.mean()) if len(losses) else None
    equity = values.cumsum(); drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return {"n": int(len(values)), "expectancy": float(values.mean()),
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
            "win_rate": float((values > 0).mean()), "average_win": average_win, "average_loss": average_loss,
            "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
            "max_drawdown": float(drawdown.max(initial=0.0))}


def bootstrap_ci(trades: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not trades:
        return [None, None]
    values = np.asarray([trade["gross_return"] - PRIMARY_COST for trade in trades])
    rng = np.random.default_rng(42); estimates = np.empty(samples)
    for index in range(samples):
        estimates[index] = rng.choice(values, len(values), replace=True).mean()
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def build_report(price_dir: Path, funding_dir: Path) -> dict[str, Any]:
    trades = []; census = {}
    for symbol in SYMBOLS:
        funding = causal_funding(funding_dir / f"{symbol}.csv"); price = load_price(price_dir / f"{symbol}.csv")
        selected, counts = symbol_trades(symbol, funding, price); trades.extend(selected); census[symbol] = counts
    overall = metrics(trades); ci = bootstrap_ci(trades)
    by_fold = {f"F{fold}": metrics([trade for trade in trades if trade["fold"] == fold]) for fold in range(1, 5)}
    by_symbol = {symbol: metrics([trade for trade in trades if trade["symbol"] == symbol]) for symbol in SYMBOLS}
    by_severity = {"1-1.5": metrics([trade for trade in trades if trade["severity_ratio"] < 1.5]),
                   "1.5-2": metrics([trade for trade in trades if 1.5 <= trade["severity_ratio"] < 2]),
                   ">=2": metrics([trade for trade in trades if trade["severity_ratio"] >= 2])}
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in trades if trade["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values()); concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate = [item for item in by_fold.values() if item["n"] >= 20]
    gate = {"adequately_sampled_folds": len(adequate), "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate),
            "both_symbols_positive_and_sampled": all(item["n"] >= 30 and item["expectancy"] > 0 for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0 and overall["profit_factor"] > 1
            and ci[0] > 0 and gate["positive_adequate_folds"] >= 3 and gate["both_symbols_positive_and_sampled"]
            and concentration is not None and concentration <= 0.70)
    gate["verdict"] = "KEEP_FOR_PROSPECTIVE_VST" if keep else "REJECT"
    return {"candidate": "C-10", "protocol": "edge-candidate-register-v9", "census": census,
            "overall_funding_inclusive": overall, "overall_price_only": metrics(trades, field="price_return"),
            "mean_funding_return": float(np.mean([trade["funding_return"] for trade in trades])) if trades else None,
            "bootstrap_95_ci": ci, "by_fold": by_fold, "by_symbol": by_symbol, "by_severity": by_severity,
            "cost_sensitivity": {f"{cost:.3f}": metrics(trades, cost) for cost in COSTS}, "gate": gate,
            "limitations": ["Reverse-time independent holdout; prospective VST remains mandatory.",
                            "Funding cashflow uses the standard unit-notional rate approximation."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-dir", default="data/research/c09/binance_futures_15m")
    parser.add_argument("--funding-dir", default="data/research/c10/funding"); parser.add_argument("--output")
    args = parser.parse_args(); report = build_report(Path(args.price_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
