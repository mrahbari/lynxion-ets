#!/usr/bin/env python3
"""Evaluate preregistered C-09 on the independent pre-2023 futures holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT")
TRADED = SYMBOLS[1:]
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)
FOLDS = 4


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
    returns = close.pct_change(96, fill_method=None)
    relative = returns[list(TRADED)].sub(returns["BTCUSDT"], axis=0)
    relative["spread"] = relative.max(axis=1) - relative.min(axis=1)
    relative["btc_regime"] = returns["BTCUSDT"]
    daily = relative.index.to_series().mod(86400).eq(0)
    daily_spread = relative.loc[daily, "spread"]
    relative["threshold"] = daily_spread.shift(1).rolling(180, min_periods=180).median().reindex(relative.index)
    return relative


def collect_trades(close: pd.DataFrame, opened: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, int]]:
    features = causal_features(close)
    decisions = [int(timestamp) for timestamp in close.index if int(timestamp) % 86400 == 0
                 and np.isfinite(features.loc[timestamp, "threshold"])]
    boundaries = [decisions[index * len(decisions) // FOLDS] for index in range(FOLDS)] + [decisions[-1] + 86400]
    trades = []
    census = {"eligible_decisions": len(decisions), "no_trade": 0, "unresolved_at_fold_end": 0}
    for timestamp in decisions:
        position = close.index.get_loc(timestamp); row = features.loc[timestamp]
        spread, threshold, regime = float(row["spread"]), float(row["threshold"]), float(row["btc_regime"])
        if regime <= 0 or spread <= threshold:
            census["no_trade"] += 1
            continue
        fold = max(index for index in range(FOLDS) if timestamp >= boundaries[index])
        if position + 97 >= len(close):
            continue
        entry_position, exit_position = position + 1, position + 97
        exit_timestamp = int(close.index[exit_position])
        if exit_timestamp >= boundaries[fold + 1]:
            census["unresolved_at_fold_end"] += 1
            continue
        ranked = sorted(((float(row[symbol]), symbol) for symbol in TRADED), key=lambda item: (item[0], item[1]))
        symbol = ranked[-1][1]
        entry, exit_price = float(opened.iloc[entry_position][symbol]), float(opened.iloc[exit_position][symbol])
        trades.append({"decision_timestamp": timestamp, "entry_timestamp": int(close.index[entry_position]),
                       "exit_timestamp": exit_timestamp, "fold": fold + 1, "symbol": symbol,
                       "spread": spread, "threshold": threshold, "spread_ratio": spread / threshold,
                       "btc_regime": regime, "entry_price": entry, "exit_price": exit_price,
                       "gross_return": (exit_price - entry) / entry})
    return trades, census


def metrics(trades: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    values = np.asarray([trade["gross_return"] - cost for trade in trades], dtype=float)
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


def build_report(data_dir: Path) -> dict[str, Any]:
    close, opened = load_panel(data_dir); trades, census = collect_trades(close, opened)
    overall = metrics(trades); ci = bootstrap_ci(trades)
    by_fold = {f"F{fold}": metrics([trade for trade in trades if trade["fold"] == fold]) for fold in range(1, 5)}
    by_symbol = {symbol: metrics([trade for trade in trades if trade["symbol"] == symbol]) for symbol in TRADED}
    by_spread = {"1-1.5": metrics([trade for trade in trades if trade["spread_ratio"] < 1.5]),
                 "1.5-2": metrics([trade for trade in trades if 1.5 <= trade["spread_ratio"] < 2]),
                 ">=2": metrics([trade for trade in trades if trade["spread_ratio"] >= 2])}
    by_btc = {"0-2%": metrics([trade for trade in trades if trade["btc_regime"] < 0.02]),
              "2-5%": metrics([trade for trade in trades if 0.02 <= trade["btc_regime"] < 0.05]),
              ">=5%": metrics([trade for trade in trades if trade["btc_regime"] >= 0.05])}
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in trades if trade["symbol"] == symbol) for symbol in TRADED}
    total_positive = sum(positive.values()); concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate = [item for item in by_fold.values() if item["n"] >= 50]
    gate = {"adequately_sampled_folds": len(adequate), "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate),
            "non_negative_symbols": sum(item["expectancy"] is not None and item["expectancy"] >= 0 for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0 and overall["profit_factor"] > 1
            and ci[0] > 0 and gate["positive_adequate_folds"] >= 3 and gate["non_negative_symbols"] >= 3
            and concentration is not None and concentration <= 0.30)
    gate["verdict"] = "KEEP_FOR_PROSPECTIVE_VST" if keep else "REJECT"
    return {"candidate": "C-09", "protocol": "edge-candidate-register-v8", "aligned_rows": len(close),
            "aligned_first_timestamp": int(close.index[0]), "aligned_last_timestamp": int(close.index[-1]),
            "census": census, "overall": overall, "bootstrap_95_ci": ci, "by_fold": by_fold,
            "by_symbol": by_symbol, "by_spread_ratio": by_spread, "by_btc_return": by_btc,
            "cost_sensitivity": {f"{cost:.3f}": metrics(trades, cost) for cost in COSTS}, "gate": gate,
            "limitations": ["This independent holdout predates the discovery sample and is reverse-time evidence.",
                            "Funding is unavailable and unmodeled."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/research/c09/binance_futures_15m"); parser.add_argument("--output")
    args = parser.parse_args(); report = build_report(Path(args.data_dir)); rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
