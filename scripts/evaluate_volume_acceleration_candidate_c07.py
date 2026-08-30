#!/usr/bin/env python3
"""Evaluate preregistered C-07 on the aligned TASK-0094 futures panel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT")
TRADED = SYMBOLS[1:]
FOLDS = 4
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)


def load_panel(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    closes, opens, volumes = {}, {}, {}
    for symbol in SYMBOLS:
        frame = pd.read_csv(data_dir / f"{symbol}.csv", usecols=["timestamp", "open", "close", "volume"])
        frame = frame.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
        closes[symbol] = pd.to_numeric(frame["close"], errors="coerce")
        opens[symbol] = pd.to_numeric(frame["open"], errors="coerce")
        volumes[symbol] = pd.to_numeric(frame["volume"], errors="coerce")
    close = pd.DataFrame(closes).dropna()
    return close, pd.DataFrame(opens).reindex(close.index), pd.DataFrame(volumes).reindex(close.index)


def causal_features(close: pd.DataFrame, volume: pd.DataFrame) -> dict[str, pd.DataFrame | pd.Series]:
    momentum = close.pct_change(16, fill_method=None)
    prior_momentum = close.shift(16).div(close.shift(32)).sub(1)
    acceleration = momentum - prior_momentum
    prior_volume_median = volume.shift(1).rolling(96, min_periods=96).median()
    relative_volume = volume / prior_volume_median
    btc_regime = close["BTCUSDT"].pct_change(96, fill_method=None)
    return {"momentum": momentum, "acceleration": acceleration,
            "relative_volume": relative_volume, "btc_regime": btc_regime}


def fold_boundaries(index: pd.Index) -> list[int]:
    decisions = [int(timestamp) for timestamp in index if int(timestamp) % 3600 == 0]
    return [decisions[item * len(decisions) // FOLDS] for item in range(FOLDS)] + [decisions[-1] + 3600]


def collect_trades(close: pd.DataFrame, opened: pd.DataFrame, volume: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    features = causal_features(close, volume)
    boundaries = fold_boundaries(close.index[96:])
    trades: list[dict[str, Any]] = []
    active: dict[str, int] = {}
    census = {"decision_timestamps": 0, "no_trade": 0, "capacity_rejected": 0,
              "duplicate_rejected": 0, "unresolved_at_fold_end": 0}
    for position in range(96, len(close) - 17):
        timestamp = int(close.index[position])
        if timestamp % 3600 != 0:
            continue
        census["decision_timestamps"] += 1
        fold = max(item for item in range(FOLDS) if timestamp >= boundaries[item])
        entry_position, exit_position = position + 1, position + 17
        entry_timestamp, exit_timestamp = int(close.index[entry_position]), int(close.index[exit_position])
        active = {symbol: end for symbol, end in active.items() if end > entry_position}
        regime = float(features["btc_regime"].iloc[position])
        if not np.isfinite(regime) or regime == 0:
            census["no_trade"] += 1
            continue
        side, direction = ("LONG", 1.0) if regime > 0 else ("SHORT", -1.0)
        eligible = []
        for symbol in TRADED:
            momentum = float(features["momentum"].iloc[position][symbol])
            acceleration = float(features["acceleration"].iloc[position][symbol])
            relative_volume = float(features["relative_volume"].iloc[position][symbol])
            if not all(np.isfinite(value) for value in (momentum, acceleration, relative_volume)):
                continue
            if relative_volume < 2.0 or direction * momentum <= 0 or direction * acceleration <= 0:
                continue
            eligible.append((abs(acceleration), symbol, momentum, acceleration, relative_volume))
        eligible.sort(key=lambda item: (-item[0], item[1]))
        if not eligible:
            census["no_trade"] += 1
            continue
        if exit_timestamp >= boundaries[fold + 1]:
            census["unresolved_at_fold_end"] += min(3, len(eligible))
            continue
        admitted = 0
        for _, symbol, momentum, acceleration, relative_volume in eligible:
            if symbol in active:
                census["duplicate_rejected"] += 1
                continue
            if len(active) >= 3:
                census["capacity_rejected"] += 1
                break
            entry, exit_price = float(opened.iloc[entry_position][symbol]), float(opened.iloc[exit_position][symbol])
            gross = direction * (exit_price - entry) / entry
            trades.append({
                "decision_timestamp": timestamp, "entry_timestamp": entry_timestamp,
                "exit_timestamp": exit_timestamp, "fold": fold + 1, "symbol": symbol,
                "side": side, "btc_regime": regime, "momentum": momentum,
                "acceleration": acceleration, "relative_volume": relative_volume,
                "entry_price": entry, "exit_price": exit_price, "gross_return": gross,
            })
            active[symbol] = exit_position
            admitted += 1
        if admitted == 0:
            census["no_trade"] += 1
    return trades, census


def metrics(trades: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    values = np.asarray([trade["gross_return"] - cost for trade in trades], dtype=float)
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None, "max_drawdown": None}
    wins, losses = values[values > 0], values[values <= 0]
    average_win = float(wins.mean()) if len(wins) else None
    average_loss = float(losses.mean()) if len(losses) else None
    equity = values.cumsum(); drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return {"n": int(len(values)), "expectancy": float(values.mean()),
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
            "win_rate": float((values > 0).mean()), "average_win": average_win, "average_loss": average_loss,
            "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
            "max_drawdown": float(drawdown.max(initial=0.0))}


def bootstrap_ci(trades: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not trades:
        return [None, None]
    frame = pd.DataFrame(trades)
    clusters = [group["gross_return"].to_numpy() - PRIMARY_COST for _, group in frame.groupby("decision_timestamp")]
    rng = np.random.default_rng(42); estimates = np.empty(samples)
    for index in range(samples):
        selected = rng.integers(0, len(clusters), len(clusters))
        estimates[index] = np.concatenate([clusters[item] for item in selected]).mean()
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def build_report(data_dir: Path) -> dict[str, Any]:
    close, opened, volume = load_panel(data_dir)
    trades, census = collect_trades(close, opened, volume)
    overall = metrics(trades); ci = bootstrap_ci(trades)
    by_fold = {f"F{fold}": metrics([trade for trade in trades if trade["fold"] == fold]) for fold in range(1, 5)}
    by_side = {side: metrics([trade for trade in trades if trade["side"] == side]) for side in ("LONG", "SHORT")}
    by_symbol = {symbol: metrics([trade for trade in trades if trade["symbol"] == symbol]) for symbol in TRADED}
    by_context = {"BTC_POSITIVE": by_side["LONG"], "BTC_NEGATIVE": by_side["SHORT"]}
    by_volume = {
        "2-3": metrics([trade for trade in trades if trade["relative_volume"] < 3]),
        "3-5": metrics([trade for trade in trades if 3 <= trade["relative_volume"] < 5]),
        ">=5": metrics([trade for trade in trades if trade["relative_volume"] >= 5]),
    }
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in trades if trade["symbol"] == symbol) for symbol in TRADED}
    total_positive = sum(positive.values()); concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate = [item for item in by_fold.values() if item["n"] >= 100]
    gate = {"adequately_sampled_folds": len(adequate),
            "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate),
            "both_sides_non_negative_and_sampled": all(item["n"] >= 100 and item["expectancy"] >= 0 for item in by_side.values()),
            "non_negative_symbols": sum(item["expectancy"] is not None and item["expectancy"] >= 0 for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0 and overall["profit_factor"] > 1
            and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["both_sides_non_negative_and_sampled"] and gate["non_negative_symbols"] >= 3
            and concentration is not None and concentration <= 0.30)
    gate["verdict"] = "KEEP_FOR_FURTHER_VALIDATION" if keep else "REJECT"
    return {"candidate": "C-07", "protocol": "edge-candidate-register-v6", "aligned_rows": len(close),
            "census": census, "overall": overall, "bootstrap_95_ci": ci, "by_fold": by_fold,
            "by_side": by_side, "by_symbol": by_symbol, "by_btc_context": by_context,
            "by_relative_volume": by_volume,
            "cost_sensitivity": {f"{cost:.3f}": metrics(trades, cost) for cost in COSTS},
            "gate": gate, "limitations": ["Funding is unavailable and unmodeled.",
            "Fixed four-hour exits isolate entry information and do not reproduce production exits."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--output")
    args = parser.parse_args(); report = build_report(Path(args.data_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
