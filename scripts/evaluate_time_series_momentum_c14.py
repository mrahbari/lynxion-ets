#!/usr/bin/env python3
"""Evaluate preregistered C-14 long-horizon time-series momentum."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
LOOKBACK_DAYS = 180
HOLD_SECONDS = 28 * 86400
BAR_SECONDS = 900
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)
FOLDS = 4


def load_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=["timestamp", "open", "close"])
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp")
    frame[["open", "close"]] = frame[["open", "close"]].apply(pd.to_numeric, errors="coerce")
    return frame.dropna().set_index("timestamp")


def monthly_decisions(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.reset_index()
    frame["day"] = pd.to_datetime(frame["timestamp"], unit="s", utc=True).dt.floor("D")
    daily = frame.groupby("day", sort=True).agg(
        close=("close", "last"), last_bar_timestamp=("timestamp", "last")
    )
    daily["momentum"] = daily["close"] / daily["close"].shift(LOOKBACK_DAYS) - 1.0
    daily["decision_timestamp"] = daily["last_bar_timestamp"].astype(int) + BAR_SECONDS
    eligible = daily.loc[daily["momentum"].notna()].copy()
    month_key = eligible.index.year * 100 + eligible.index.month
    return eligible.groupby(month_key, sort=True).tail(1)


def collect_trades(symbol: str, bars: pd.DataFrame, fold_boundaries: list[int] | None = None,
                   long_only: bool = False) -> tuple[list[dict[str, Any]], dict[str, int]]:
    decisions = monthly_decisions(bars)
    price_times = bars.index.to_numpy(dtype=int)
    trades: list[dict[str, Any]] = []
    last_exit = -1
    census = {"eligible_decisions": len(decisions), "zero_signal": 0, "direction_filtered": 0,
              "overlap_rejected": 0,
              "missing_price": 0, "unresolved_at_fold_end": 0}
    for row in decisions.itertuples():
        decision_timestamp, momentum = int(row.decision_timestamp), float(row.momentum)
        if momentum == 0:
            census["zero_signal"] += 1
            continue
        if long_only and momentum < 0:
            census["direction_filtered"] += 1
            continue
        entry_position = int(np.searchsorted(price_times, decision_timestamp, side="left"))
        if entry_position >= len(price_times) or int(price_times[entry_position]) != decision_timestamp:
            census["missing_price"] += 1
            continue
        entry_timestamp = int(price_times[entry_position])
        if entry_timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        exit_position = int(np.searchsorted(price_times, entry_timestamp + HOLD_SECONDS, side="left"))
        if exit_position >= len(price_times):
            census["missing_price"] += 1
            continue
        exit_timestamp = int(price_times[exit_position])
        fold = None
        if fold_boundaries is not None:
            fold_index = max(index for index in range(FOLDS) if decision_timestamp >= fold_boundaries[index])
            if exit_timestamp >= fold_boundaries[fold_index + 1]:
                census["unresolved_at_fold_end"] += 1
                continue
            fold = fold_index + 1
        entry_price = float(bars.iloc[entry_position]["open"])
        exit_price = float(bars.iloc[exit_position]["open"])
        direction = 1.0 if momentum > 0 else -1.0
        trades.append({"symbol": symbol, "side": "LONG" if direction > 0 else "SHORT",
                       "decision_timestamp": decision_timestamp, "entry_timestamp": entry_timestamp,
                       "exit_timestamp": exit_timestamp, "cluster_month": decision_timestamp // (31 * 86400),
                       "fold": fold, "momentum": momentum, "entry_price": entry_price,
                       "exit_price": exit_price,
                       "gross_return": direction * (exit_price - entry_price) / entry_price})
        last_exit = exit_timestamp
    return trades, census


def metrics(trades: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    values = np.asarray([trade["gross_return"] - cost for trade in trades], dtype=float)
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None,
                "max_drawdown": None}
    wins, losses = values[values > 0], values[values <= 0]
    average_win = float(wins.mean()) if len(wins) else None
    average_loss = float(losses.mean()) if len(losses) else None
    equity = values.cumsum()
    drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return {"n": len(values), "expectancy": float(values.mean()),
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
            "win_rate": float((values > 0).mean()), "average_win": average_win,
            "average_loss": average_loss,
            "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
            "max_drawdown": float(drawdown.max(initial=0.0))}


def month_cluster_ci(trades: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not trades:
        return [None, None]
    clusters: dict[tuple[int, int], list[float]] = {}
    for trade in trades:
        timestamp = pd.Timestamp(trade["decision_timestamp"], unit="s", tz="UTC")
        clusters.setdefault((timestamp.year, timestamp.month), []).append(trade["gross_return"] - PRIMARY_COST)
    keys = list(clusters)
    rng = np.random.default_rng(42)
    estimates = np.empty(samples)
    for index in range(samples):
        sampled = rng.choice(len(keys), len(keys), replace=True)
        values = [value for cluster_index in sampled for value in clusters[keys[int(cluster_index)]]]
        estimates[index] = np.mean(values)
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def sample(data_dir: Path, primary: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bars = {symbol: load_bars(data_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    all_decisions = sorted({int(row.decision_timestamp) for frame in bars.values()
                            for row in monthly_decisions(frame).itertuples()})
    boundaries = None
    if primary:
        boundaries = [all_decisions[index * len(all_decisions) // FOLDS] for index in range(FOLDS)]
        boundaries.append(all_decisions[-1] + 32 * 86400)
    trades: list[dict[str, Any]] = []
    census = {}
    for symbol, frame in bars.items():
        selected, counts = collect_trades(symbol, frame, boundaries)
        trades.extend(selected)
        census[symbol] = counts
    trades.sort(key=lambda trade: (trade["entry_timestamp"], trade["symbol"]))
    return trades, {"census": census, "fold_boundaries": boundaries}


def build_report(primary_dir: Path, reverse_dir: Path) -> dict[str, Any]:
    primary, primary_info = sample(primary_dir, True)
    reverse, reverse_info = sample(reverse_dir, False)
    overall = metrics(primary)
    ci = month_cluster_ci(primary)
    by_fold = {f"F{fold}": metrics([trade for trade in primary if trade["fold"] == fold])
               for fold in range(1, FOLDS + 1)}
    by_side = {side: metrics([trade for trade in primary if trade["side"] == side])
               for side in ("LONG", "SHORT")}
    by_symbol = {symbol: metrics([trade for trade in primary if trade["symbol"] == symbol])
                 for symbol in SYMBOLS}
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in primary
                            if trade["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate_folds = [item for item in by_fold.values() if item["n"] >= 30]
    reverse_metrics = metrics(reverse)
    cost_sensitivity = {f"{cost:.3f}": metrics(primary, cost) for cost in COSTS}
    gate = {
        "adequately_sampled_folds": len(adequate_folds),
        "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate_folds),
        "both_sides_positive_and_sampled": all(item["n"] >= 30 and item["expectancy"] > 0
                                                for item in by_side.values()),
        "positive_sampled_symbols": sum(item["n"] >= 20 and item["expectancy"] > 0
                                        for item in by_symbol.values()),
        "max_positive_pnl_symbol_concentration": concentration,
    }
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0
            and overall["profit_factor"] is not None and overall["profit_factor"] > 1
            and ci[0] is not None and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["both_sides_positive_and_sampled"] and gate["positive_sampled_symbols"] >= 4
            and concentration is not None and concentration <= 0.40
            and reverse_metrics["n"] >= 120 and reverse_metrics["expectancy"] > 0
            and reverse_metrics["profit_factor"] is not None and reverse_metrics["profit_factor"] > 1
            and cost_sensitivity["0.005"]["expectancy"] > 0)
    gate["verdict"] = "KEEP_FOR_PATH_DEPENDENT_CONFIRMATION" if keep else "REJECT"
    return {"candidate": "C-14", "protocol": "edge-candidate-register-v13",
            "primary": {"overall": overall, "month_cluster_bootstrap_95_ci": ci,
                        "by_fold": by_fold, "by_side": by_side, "by_symbol": by_symbol,
                        "cost_sensitivity": cost_sensitivity, **primary_info},
            "reverse_time": {"overall": reverse_metrics, **reverse_info}, "gate": gate,
            "limitations": ["Funding is unavailable and unmodeled.",
                            "Fixed 28-day exits isolate signal information and are not production exits."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--reverse-dir", default="data/research/c09/binance_futures_15m")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(Path(args.primary_dir), Path(args.reverse_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
