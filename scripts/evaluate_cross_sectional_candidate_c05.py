#!/usr/bin/env python3
"""Evaluate preregistered C-05 cross-sectional momentum without production mutation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BAR_SECONDS = 900
MOMENTUM_BARS = 16
LIQUIDITY_BARS = 96
LIQUID_UNIVERSE = 50
MIN_UNIVERSE = 30
POSITIONS = 3
FOLDS = 4
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)
RESTRICTED = {"XMR-USDT"}


def prepare_symbol(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, usecols=["timestamp", "open", "close", "volume"])
    raw = raw.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    for column in ("timestamp", "open", "close", "volume"):
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    contiguous_lookback = raw["timestamp"].diff(MOMENTUM_BARS).eq(MOMENTUM_BARS * BAR_SECONDS)
    contiguous_liquidity = raw["timestamp"].diff(LIQUIDITY_BARS - 1).eq((LIQUIDITY_BARS - 1) * BAR_SECONDS)
    entry_time = raw["timestamp"].shift(-1)
    exit_time = raw["timestamp"].shift(-(MOMENTUM_BARS + 1))
    result = pd.DataFrame({
        "timestamp": raw["timestamp"].astype("Int64"),
        "symbol": path.stem,
        "momentum": raw["close"].div(raw["close"].shift(MOMENTUM_BARS)).sub(1),
        "liquidity": (raw["close"] * raw["volume"]).rolling(LIQUIDITY_BARS, min_periods=LIQUIDITY_BARS).median(),
        "entry_open": raw["open"].shift(-1),
        "exit_open": raw["open"].shift(-(MOMENTUM_BARS + 1)),
        "entry_timestamp": entry_time,
        "exit_timestamp": exit_time,
    })
    valid = (
        contiguous_lookback & contiguous_liquidity
        & entry_time.sub(raw["timestamp"]).eq(BAR_SECONDS)
        & exit_time.sub(raw["timestamp"]).eq((MOMENTUM_BARS + 1) * BAR_SECONDS)
        & result[["momentum", "liquidity", "entry_open", "exit_open"]].apply(np.isfinite).all(axis=1)
        & result["entry_open"].gt(0) & result["exit_open"].gt(0) & result["liquidity"].gt(0)
    )
    return result.loc[valid].reset_index(drop=True)


def load_universe(data_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(data_dir.glob("*-USDT.csv")):
        base = path.stem.removesuffix("-USDT")
        if path.stem in RESTRICTED or "USD" in base:
            continue
        try:
            frame = prepare_symbol(path)
            if not frame.empty:
                frames.append(frame)
        except (OSError, ValueError, pd.errors.ParserError):
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def select_batches(universe: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    selections: list[dict[str, Any]] = []
    counts = {"decision_timestamps": 0, "no_trade": 0, "insufficient_universe": 0}
    for timestamp, cross_section in universe.groupby("timestamp", sort=True):
        if int(timestamp) % (MOMENTUM_BARS * BAR_SECONDS) != 0:
            continue
        counts["decision_timestamps"] += 1
        liquid = cross_section.nlargest(LIQUID_UNIVERSE, "liquidity")
        if len(liquid) < MIN_UNIVERSE:
            counts["insufficient_universe"] += 1
            continue
        market_momentum = float(liquid["momentum"].median())
        if market_momentum > 0:
            chosen, side = liquid.nlargest(POSITIONS, "momentum"), "LONG"
        elif market_momentum < 0:
            chosen, side = liquid.nsmallest(POSITIONS, "momentum"), "SHORT"
        else:
            counts["no_trade"] += 1
            continue
        for row in chosen.itertuples(index=False):
            direction = 1.0 if side == "LONG" else -1.0
            gross_return = direction * (float(row.exit_open) - float(row.entry_open)) / float(row.entry_open)
            selections.append({
                "decision_timestamp": int(timestamp), "entry_timestamp": int(row.entry_timestamp),
                "exit_timestamp": int(row.exit_timestamp), "symbol": row.symbol, "side": side,
                "market_momentum": market_momentum, "symbol_momentum": float(row.momentum),
                "entry_price": float(row.entry_open), "exit_price": float(row.exit_open),
                "gross_return": gross_return,
            })
    return selections, counts


def split_folds(selections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    if not selections:
        return [], 0
    decisions = sorted({item["decision_timestamp"] for item in selections})
    boundaries = [decisions[index * len(decisions) // FOLDS] for index in range(FOLDS)]
    boundaries.append(max(item["exit_timestamp"] for item in selections) + 1)
    accepted, unresolved = [], 0
    for item in selections:
        fold = max(index for index in range(FOLDS) if item["decision_timestamp"] >= boundaries[index])
        if item["exit_timestamp"] >= boundaries[fold + 1]:
            unresolved += 1
            continue
        accepted.append({**item, "fold": fold + 1})
    return accepted, unresolved


def metrics(items: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    returns = np.array([item["gross_return"] - cost for item in items], dtype=float)
    if not len(returns):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None, "max_drawdown": None}
    wins, losses = returns[returns > 0], returns[returns <= 0]
    gross_profit, gross_loss = float(wins.sum()), float(-losses.sum())
    equity = returns.cumsum()
    drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    average_win = float(wins.mean()) if len(wins) else None
    average_loss = float(losses.mean()) if len(losses) else None
    return {
        "n": int(len(returns)), "expectancy": float(returns.mean()),
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "win_rate": float((returns > 0).mean()), "average_win": average_win,
        "average_loss": average_loss,
        "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
        "max_drawdown": float(drawdown.max(initial=0.0)),
    }


def cluster_bootstrap_ci(items: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not items:
        return [None, None]
    frame = pd.DataFrame(items)
    clusters = [group["gross_return"].to_numpy() - PRIMARY_COST for _, group in frame.groupby("decision_timestamp")]
    rng = np.random.default_rng(42)
    estimates = np.empty(samples)
    for index in range(samples):
        picked = rng.integers(0, len(clusters), len(clusters))
        estimates[index] = np.concatenate([clusters[item] for item in picked]).mean()
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def build_report(data_dir: Path) -> dict[str, Any]:
    universe = load_universe(data_dir)
    selections, census = select_batches(universe)
    trades, unresolved = split_folds(selections)
    overall = metrics(trades)
    by_fold = {f"F{fold}": metrics([item for item in trades if item["fold"] == fold]) for fold in range(1, FOLDS + 1)}
    by_side = {side: metrics([item for item in trades if item["side"] == side]) for side in ("LONG", "SHORT")}
    by_symbol = {symbol: metrics([item for item in trades if item["symbol"] == symbol]) for symbol in sorted({t["symbol"] for t in trades})}
    positive_by_symbol = {
        symbol: sum(max(0.0, item["gross_return"] - PRIMARY_COST) for item in trades if item["symbol"] == symbol)
        for symbol in by_symbol
    }
    total_positive = sum(positive_by_symbol.values())
    max_concentration = max(positive_by_symbol.values(), default=0.0) / total_positive if total_positive else None
    ci = cluster_bootstrap_ci(trades)
    adequate_folds = [value for value in by_fold.values() if value["n"] >= 30]
    gate = {
        "positive_adequate_folds": sum(value["expectancy"] > 0 for value in adequate_folds),
        "adequately_sampled_folds": len(adequate_folds),
        "both_sides_non_negative_and_sampled": all(by_side[side]["n"] >= 30 and by_side[side]["expectancy"] >= 0 for side in by_side),
        "max_positive_pnl_symbol_concentration": max_concentration,
    }
    keep = (
        overall["expectancy"] is not None and overall["expectancy"] > 0
        and overall["profit_factor"] is not None and overall["profit_factor"] > 1
        and ci[0] is not None and ci[0] > 0
        and gate["positive_adequate_folds"] >= 3
        and gate["both_sides_non_negative_and_sampled"]
        and max_concentration is not None and max_concentration <= 0.20
    )
    gate["verdict"] = "KEEP_FOR_FURTHER_VALIDATION" if keep else "REJECT"
    return {
        "candidate": "C-05", "protocol": "edge-candidate-register-v4",
        "data_dir": str(data_dir), "source_symbols_loaded": int(universe["symbol"].nunique()) if not universe.empty else 0,
        "census": census, "unresolved_at_fold_end": unresolved,
        "overall": overall, "bootstrap_95_ci": ci, "by_fold": by_fold, "by_side": by_side,
        "by_symbol": by_symbol, "cost_sensitivity": {f"{cost:.3f}": metrics(trades, cost) for cost in COSTS},
        "gate": gate,
        "limitations": [
            "Historical store does not preserve complete point-in-time exchange listing membership.",
            "Historical bid/ask and funding observations are unavailable; fixed costs represent spread/slippage/fees and funding is unmodeled.",
            "Fixed four-hour exits isolate selection quality and do not reproduce a production strategy exit policy.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/history/processed/15m")
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
