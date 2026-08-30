#!/usr/bin/env python3
"""Evaluate preregistered C-06 on the aligned TASK-0094 futures panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT")
SIGNAL_BARS = 5
EXIT_BARS = 5
THRESHOLD_BARS = 2880
FOLDS = 4
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)


def load_panel(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    closes, opens = {}, {}
    for symbol in SYMBOLS:
        frame = pd.read_csv(data_dir / f"{symbol}.csv", usecols=["timestamp", "open", "close"])
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
        closes[symbol] = pd.to_numeric(frame["close"], errors="coerce")
        opens[symbol] = pd.to_numeric(frame["open"], errors="coerce")
    close = pd.DataFrame(closes).dropna()
    opened = pd.DataFrame(opens).reindex(close.index)
    return close, opened


def causal_features(close: pd.DataFrame) -> pd.DataFrame:
    signal = close.pct_change(SIGNAL_BARS, fill_method=None)
    median = signal.median(axis=1)
    dispersion = signal.sub(median, axis=0).abs().median(axis=1)
    threshold = dispersion.shift(1).rolling(THRESHOLD_BARS, min_periods=THRESHOLD_BARS).median()
    features = signal.copy()
    features["dispersion"] = dispersion
    features["threshold"] = threshold
    return features


def collect_pairs(close: pd.DataFrame, opened: pd.DataFrame) -> tuple[list[dict[str, Any]], int]:
    features = causal_features(close)
    pairs = []
    no_trade = 0
    for position, timestamp in enumerate(close.index):
        if int(timestamp) % 3600 != 0 or position + EXIT_BARS >= len(close):
            continue
        row = features.loc[timestamp]
        dispersion, threshold = float(row["dispersion"]), float(row["threshold"])
        if not np.isfinite(dispersion) or not np.isfinite(threshold) or dispersion <= threshold:
            no_trade += 1
            continue
        ranked = sorted(((float(row[symbol]), symbol) for symbol in SYMBOLS), key=lambda item: (item[0], item[1]))
        long_symbol, short_symbol = ranked[0][1], ranked[-1][1]
        entry_position, exit_position = position + 1, position + EXIT_BARS
        entry_timestamp, exit_timestamp = int(close.index[entry_position]), int(close.index[exit_position])
        legs = []
        for side, symbol, direction in (("LONG", long_symbol, 1.0), ("SHORT", short_symbol, -1.0)):
            entry, exit_price = float(opened.iloc[entry_position][symbol]), float(opened.iloc[exit_position][symbol])
            gross = direction * (exit_price - entry) / entry
            legs.append({"side": side, "symbol": symbol, "entry_price": entry,
                         "exit_price": exit_price, "gross_return": gross})
        pairs.append({
            "decision_timestamp": int(timestamp), "entry_timestamp": entry_timestamp,
            "exit_timestamp": exit_timestamp, "dispersion": dispersion,
            "threshold": threshold, "dispersion_ratio": dispersion / threshold,
            "pair_gross_return": float(np.mean([leg["gross_return"] for leg in legs])),
            "legs": legs,
        })
    return pairs, no_trade


def split_folds(pairs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    decisions = sorted(item["decision_timestamp"] for item in pairs)
    if not decisions:
        return [], 0
    boundaries = [decisions[index * len(decisions) // FOLDS] for index in range(FOLDS)]
    boundaries.append(max(item["exit_timestamp"] for item in pairs) + 1)
    accepted, unresolved = [], 0
    for item in pairs:
        fold = max(index for index in range(FOLDS) if item["decision_timestamp"] >= boundaries[index])
        if item["exit_timestamp"] >= boundaries[fold + 1]:
            unresolved += 1
            continue
        accepted.append({**item, "fold": fold + 1})
    return accepted, unresolved


def values_metrics(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if not len(array):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None, "max_drawdown": None}
    wins, losses = array[array > 0], array[array <= 0]
    average_win = float(wins.mean()) if len(wins) else None
    average_loss = float(losses.mean()) if len(losses) else None
    equity = array.cumsum()
    drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return {
        "n": int(len(array)), "expectancy": float(array.mean()),
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
        "win_rate": float((array > 0).mean()), "average_win": average_win,
        "average_loss": average_loss,
        "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
        "max_drawdown": float(drawdown.max(initial=0.0)),
    }


def pair_metrics(pairs: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    return values_metrics([item["pair_gross_return"] - cost for item in pairs])


def flatten_legs(pairs: list[dict[str, Any]], cost: float = PRIMARY_COST) -> list[dict[str, Any]]:
    return [{**leg, "net_return": leg["gross_return"] - cost, "fold": item["fold"],
             "decision_timestamp": item["decision_timestamp"]} for item in pairs for leg in item["legs"]]


def bootstrap_ci(pairs: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not pairs:
        return [None, None]
    values = np.asarray([item["pair_gross_return"] - PRIMARY_COST for item in pairs])
    rng = np.random.default_rng(42)
    estimates = np.empty(samples)
    for index in range(samples):
        estimates[index] = rng.choice(values, size=len(values), replace=True).mean()
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def build_report(data_dir: Path) -> dict[str, Any]:
    close, opened = load_panel(data_dir)
    candidates, no_trade = collect_pairs(close, opened)
    pairs, unresolved = split_folds(candidates)
    legs = flatten_legs(pairs)
    overall = pair_metrics(pairs)
    by_fold = {f"F{fold}": pair_metrics([item for item in pairs if item["fold"] == fold]) for fold in range(1, 5)}
    by_side = {side: values_metrics([leg["net_return"] for leg in legs if leg["side"] == side]) for side in ("LONG", "SHORT")}
    by_symbol = {symbol: values_metrics([leg["net_return"] for leg in legs if leg["symbol"] == symbol]) for symbol in SYMBOLS}
    by_dispersion = {
        "1.00-1.25": pair_metrics([item for item in pairs if item["dispersion_ratio"] <= 1.25]),
        "1.25-1.50": pair_metrics([item for item in pairs if 1.25 < item["dispersion_ratio"] <= 1.50]),
        ">1.50": pair_metrics([item for item in pairs if item["dispersion_ratio"] > 1.50]),
    }
    positive = {symbol: sum(max(0.0, leg["net_return"]) for leg in legs if leg["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values()) / total_positive if total_positive else None
    ci = bootstrap_ci(pairs)
    adequate_folds = [value for value in by_fold.values() if value["n"] >= 100]
    gate = {
        "adequately_sampled_folds": len(adequate_folds),
        "positive_adequate_folds": sum(value["expectancy"] > 0 for value in adequate_folds),
        "both_sides_non_negative_and_sampled": all(value["n"] >= 100 and value["expectancy"] >= 0 for value in by_side.values()),
        "non_negative_symbols": sum(value["expectancy"] is not None and value["expectancy"] >= 0 for value in by_symbol.values()),
        "max_positive_pnl_symbol_concentration": concentration,
    }
    keep = (
        overall["expectancy"] > 0 and overall["profit_factor"] is not None and overall["profit_factor"] > 1
        and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
        and gate["both_sides_non_negative_and_sampled"] and gate["non_negative_symbols"] >= 4
        and concentration is not None and concentration <= 0.30
    )
    gate["verdict"] = "KEEP_FOR_FURTHER_VALIDATION" if keep else "REJECT"
    return {
        "candidate": "C-06", "protocol": "edge-candidate-register-v5",
        "aligned_rows": len(close), "candidate_pairs": len(candidates), "no_trade_decisions": no_trade,
        "unresolved_at_fold_end": unresolved, "overall_pair": overall, "bootstrap_95_ci": ci,
        "by_fold": by_fold, "by_side": by_side, "by_symbol": by_symbol,
        "by_dispersion_ratio": by_dispersion,
        "cost_sensitivity": {f"{cost:.3f}": pair_metrics(pairs, cost) for cost in COSTS},
        "gate": gate,
        "limitations": ["Funding is unavailable and unmodeled.",
                        "Fixed one-hour exits isolate selection quality and do not reproduce production exits."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(Path(args.data_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
