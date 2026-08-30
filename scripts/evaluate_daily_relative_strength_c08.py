#!/usr/bin/env python3
"""Evaluate preregistered C-08 daily relative-strength continuation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT")
TRADED = SYMBOLS[1:]
LOOKBACK = 96
EXIT_OFFSET = 97
WARMUP_DAYS = 180
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
    return close, pd.DataFrame(opens).reindex(close.index)


def causal_features(close: pd.DataFrame) -> pd.DataFrame:
    returns = close.pct_change(LOOKBACK, fill_method=None)
    relative = returns[list(TRADED)].sub(returns["BTCUSDT"], axis=0)
    relative["spread"] = relative.max(axis=1) - relative.min(axis=1)
    relative["btc_regime"] = returns["BTCUSDT"]
    daily = relative.index.to_series().mod(86400).eq(0)
    daily_spread = relative.loc[daily, "spread"]
    relative["threshold"] = daily_spread.shift(1).rolling(WARMUP_DAYS, min_periods=WARMUP_DAYS).median().reindex(relative.index)
    return relative


def collect_pairs(close: pd.DataFrame, opened: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    features = causal_features(close)
    eligible_decisions = [int(timestamp) for timestamp in close.index
                          if int(timestamp) % 86400 == 0 and np.isfinite(features.loc[timestamp, "threshold"])]
    boundaries = [eligible_decisions[index * len(eligible_decisions) // FOLDS] for index in range(FOLDS)]
    boundaries.append(eligible_decisions[-1] + 86400)
    pairs = []
    census = {"eligible_decisions": len(eligible_decisions), "no_trade": 0, "unresolved_at_fold_end": 0}
    for timestamp in eligible_decisions:
        position = close.index.get_loc(timestamp)
        if position + EXIT_OFFSET >= len(close):
            continue
        row = features.loc[timestamp]
        spread, threshold = float(row["spread"]), float(row["threshold"])
        if spread <= threshold:
            census["no_trade"] += 1
            continue
        fold = max(index for index in range(FOLDS) if timestamp >= boundaries[index])
        entry_position, exit_position = position + 1, position + EXIT_OFFSET
        entry_timestamp, exit_timestamp = int(close.index[entry_position]), int(close.index[exit_position])
        if exit_timestamp >= boundaries[fold + 1]:
            census["unresolved_at_fold_end"] += 1
            continue
        ranked = sorted(((float(row[symbol]), symbol) for symbol in TRADED), key=lambda item: (item[0], item[1]))
        short_symbol, long_symbol = ranked[0][1], ranked[-1][1]
        legs = []
        for side, symbol, direction in (("LONG", long_symbol, 1.0), ("SHORT", short_symbol, -1.0)):
            entry, exit_price = float(opened.iloc[entry_position][symbol]), float(opened.iloc[exit_position][symbol])
            legs.append({"side": side, "symbol": symbol, "entry_price": entry, "exit_price": exit_price,
                         "gross_return": direction * (exit_price - entry) / entry})
        pairs.append({"decision_timestamp": timestamp, "entry_timestamp": entry_timestamp,
                      "exit_timestamp": exit_timestamp, "fold": fold + 1, "spread": spread,
                      "threshold": threshold, "spread_ratio": spread / threshold,
                      "btc_regime": float(row["btc_regime"]), "legs": legs,
                      "pair_gross_return": float(np.mean([leg["gross_return"] for leg in legs]))})
    return pairs, census


def values_metrics(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if not len(array):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None, "max_drawdown": None}
    wins, losses = array[array > 0], array[array <= 0]
    average_win = float(wins.mean()) if len(wins) else None; average_loss = float(losses.mean()) if len(losses) else None
    equity = array.cumsum(); drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return {"n": int(len(array)), "expectancy": float(array.mean()),
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
            "win_rate": float((array > 0).mean()), "average_win": average_win, "average_loss": average_loss,
            "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
            "max_drawdown": float(drawdown.max(initial=0.0))}


def pair_metrics(pairs: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    return values_metrics([pair["pair_gross_return"] - cost for pair in pairs])


def legs(pairs: list[dict[str, Any]], cost: float = PRIMARY_COST) -> list[dict[str, Any]]:
    return [{**leg, "net_return": leg["gross_return"] - cost, "fold": pair["fold"]}
            for pair in pairs for leg in pair["legs"]]


def bootstrap_ci(pairs: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not pairs:
        return [None, None]
    values = np.asarray([pair["pair_gross_return"] - PRIMARY_COST for pair in pairs])
    rng = np.random.default_rng(42); estimates = np.empty(samples)
    for index in range(samples):
        estimates[index] = rng.choice(values, len(values), replace=True).mean()
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def build_report(data_dir: Path) -> dict[str, Any]:
    close, opened = load_panel(data_dir); pairs, census = collect_pairs(close, opened); leg_rows = legs(pairs)
    overall = pair_metrics(pairs); ci = bootstrap_ci(pairs)
    by_fold = {f"F{fold}": pair_metrics([pair for pair in pairs if pair["fold"] == fold]) for fold in range(1, 5)}
    by_side = {side: values_metrics([leg["net_return"] for leg in leg_rows if leg["side"] == side]) for side in ("LONG", "SHORT")}
    by_symbol = {symbol: values_metrics([leg["net_return"] for leg in leg_rows if leg["symbol"] == symbol]) for symbol in TRADED}
    by_spread = {"1-1.5": pair_metrics([pair for pair in pairs if pair["spread_ratio"] < 1.5]),
                 "1.5-2": pair_metrics([pair for pair in pairs if 1.5 <= pair["spread_ratio"] < 2]),
                 ">=2": pair_metrics([pair for pair in pairs if pair["spread_ratio"] >= 2])}
    by_btc = {"BTC_POSITIVE": pair_metrics([pair for pair in pairs if pair["btc_regime"] > 0]),
              "BTC_NEGATIVE": pair_metrics([pair for pair in pairs if pair["btc_regime"] < 0])}
    positive = {symbol: sum(max(0.0, leg["net_return"]) for leg in leg_rows if leg["symbol"] == symbol) for symbol in TRADED}
    total_positive = sum(positive.values()); concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate = [item for item in by_fold.values() if item["n"] >= 100]
    gate = {"adequately_sampled_folds": len(adequate), "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate),
            "both_sides_non_negative_and_sampled": all(item["n"] >= 100 and item["expectancy"] >= 0 for item in by_side.values()),
            "non_negative_symbols": sum(item["expectancy"] is not None and item["expectancy"] >= 0 for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0 and overall["profit_factor"] > 1
            and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["both_sides_non_negative_and_sampled"] and gate["non_negative_symbols"] >= 3
            and concentration is not None and concentration <= 0.30)
    gate["verdict"] = "KEEP_FOR_FURTHER_VALIDATION" if keep else "REJECT"
    return {"candidate": "C-08", "protocol": "edge-candidate-register-v7", "aligned_rows": len(close),
            "census": census, "overall_pair": overall, "bootstrap_95_ci": ci, "by_fold": by_fold,
            "by_side": by_side, "by_symbol": by_symbol, "by_spread_ratio": by_spread,
            "by_btc_regime": by_btc, "cost_sensitivity": {f"{cost:.3f}": pair_metrics(pairs, cost) for cost in COSTS},
            "gate": gate, "limitations": ["Funding is unavailable and unmodeled.",
            "Fixed 24-hour exits isolate signal information and do not reproduce production exits."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/research/c06/binance_futures_15m"); parser.add_argument("--output")
    args = parser.parse_args(); report = build_report(Path(args.data_dir)); rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
