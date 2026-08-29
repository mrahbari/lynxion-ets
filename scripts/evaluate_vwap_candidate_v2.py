#!/usr/bin/env python3
"""Evaluate preregistered C-04 with four chronological cost-adjusted OOS folds."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from domain.value_objects import Symbol
from infrastructure.strategies.adapters.vwap_reversal_strategy_adapter import VWAPReversalStrategyAdapter
from infrastructure.strategies.strategy_config import StrategyConfig


SYMBOLS = ("BTC-USDT", "ETH-USDT", "SOL-USDT")
ROUND_TRIP_COST = 0.003
HORIZON_BARS = 12
FOLDS = 4
MIN_FOLD_SIGNALS = 10


def label_regimes(frame: pd.DataFrame) -> list[str]:
    """Label each closed bar using only that bar and earlier bars."""
    close = frame["close"].astype(float)
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    bar_range = frame["high"].astype(float) - frame["low"].astype(float)
    atr = bar_range.rolling(14).mean()
    atr_median = atr.rolling(100).median()
    labels = []
    for index in range(len(frame)):
        if pd.isna(sma20.iloc[index]) or pd.isna(sma50.iloc[index]):
            labels.append("unknown")
        elif not pd.isna(atr_median.iloc[index]) and atr_median.iloc[index] > 0 and atr.iloc[index] > 1.6 * atr_median.iloc[index]:
            labels.append("breakout")
        elif sma20.iloc[index] > sma50.iloc[index] and close.iloc[index] > sma20.iloc[index]:
            labels.append("trending_up")
        elif sma20.iloc[index] < sma50.iloc[index] and close.iloc[index] < sma20.iloc[index]:
            labels.append("trending_down")
        else:
            labels.append("ranging")
    return labels


def chronological_fold(index: int, bar_count: int) -> int:
    return min(FOLDS - 1, index * FOLDS // bar_count) + 1


def metrics(values: Iterable[float]) -> Dict[str, Any]:
    returns = [float(value) for value in values]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = peak = drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {
        "n": len(returns),
        "expectancy": sum(returns) / len(returns) if returns else None,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "win_rate": len(wins) / len(returns) if returns else None,
        "average_win": gross_profit / len(wins) if wins else None,
        "average_loss": sum(losses) / len(losses) if losses else None,
        "max_drawdown_return_units": drawdown,
    }


def evaluate_symbol(path: Path, symbol: str) -> list[Dict[str, Any]]:
    frame = pd.read_csv(path).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    regimes = label_regimes(frame)
    closes = frame["close"].astype(float).to_numpy()
    adapter = VWAPReversalStrategyAdapter({})
    # BaseStrategyAdapter passes settings getters as eager ``dict.get`` defaults.
    # Cache the immutable research-run values to avoid reloading all settings per bar.
    cooldown_enabled = bool(adapter.config.get("enable_symbol_stoploss_cooldown", True))
    cooldown_minutes = int(adapter.config.get("symbol_stoploss_cooldown_minutes", 60))
    StrategyConfig.get_enable_symbol_stoploss_cooldown = staticmethod(
        lambda _name, _default=True: cooldown_enabled
    )
    StrategyConfig.get_symbol_stoploss_cooldown_minutes = staticmethod(
        lambda _name, _default=60: cooldown_minutes
    )
    domain_symbol = Symbol(symbol.replace("-", ""))
    observations: list[Dict[str, Any]] = []
    for index, row in enumerate(frame.itertuples(index=False)):
        adapter.update_with_market_data({
            "timestamp": row.timestamp,
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
        })
        signal = adapter.generate_signal(domain_symbol)
        if signal is None or regimes[index] != "ranging" or index + HORIZON_BARS >= len(frame):
            continue
        name = (getattr(getattr(signal, "signal_type", None), "name", "") or "").upper()
        side = "BUY" if "BUY" in name or "LONG" in name else "SELL" if "SELL" in name or "SHORT" in name else ""
        if not side:
            continue
        direction = 1.0 if side == "BUY" else -1.0
        gross_return = direction * ((closes[index + HORIZON_BARS] - closes[index]) / closes[index])
        observations.append({
            "symbol": symbol.replace("-", ""),
            "side": side,
            "fold": int(chronological_fold(index, len(frame))),
            "bar_index": int(index),
            "net_return": float(gross_return - ROUND_TRIP_COST),
        })
    return observations


def build_report(data_dir: Path) -> Dict[str, Any]:
    observations: list[Dict[str, Any]] = []
    errors = []
    data_spans: Dict[str, Dict[str, Any]] = {}
    for symbol in SYMBOLS:
        path = data_dir / f"{symbol}.csv"
        if not path.exists():
            errors.append(f"missing:{path}")
            continue
        try:
            span_frame = pd.read_csv(path, usecols=["timestamp"]).sort_values("timestamp")
            data_spans[symbol.replace("-", "")] = {
                "rows": int(len(span_frame)),
                "first_timestamp": str(span_frame.iloc[0]["timestamp"]),
                "last_timestamp": str(span_frame.iloc[-1]["timestamp"]),
            }
            observations.extend(evaluate_symbol(path, symbol))
        except Exception as error:
            errors.append(f"{symbol}:{type(error).__name__}:{error}")

    grouped: Dict[str, Dict[str, Any]] = {}
    definitions = {
        "by_fold": lambda row: f"F{row['fold']}",
        "by_symbol": lambda row: row["symbol"],
        "by_side": lambda row: row["side"],
        "by_symbol_side": lambda row: f"{row['symbol']}:{row['side']}",
    }
    for group_name, key in definitions.items():
        buckets: Dict[str, list[float]] = defaultdict(list)
        for row in observations:
            buckets[key(row)].append(row["net_return"])
        grouped[group_name] = {name: metrics(values) for name, values in sorted(buckets.items())}

    folds = grouped.get("by_fold", {})
    adequate = [result for result in folds.values() if result["n"] >= MIN_FOLD_SIGNALS]
    positive = sum(result["expectancy"] is not None and result["expectancy"] > 0 for result in adequate)
    overall = metrics(row["net_return"] for row in observations)
    symbol_positive = all(
        result["expectancy"] is not None and result["expectancy"] > 0
        for result in grouped.get("by_symbol", {}).values()
    ) and len(grouped.get("by_symbol", {})) == len(SYMBOLS)
    side_positive = all(
        result["expectancy"] is not None and result["expectancy"] > 0
        for result in grouped.get("by_side", {}).values()
    ) and len(grouped.get("by_side", {})) == 2
    passes = (
        not errors
        and len(adequate) == FOLDS
        and positive >= 3
        and overall["profit_factor"] is not None
        and overall["profit_factor"] > 1
        and symbol_positive
        and side_positive
    )
    return {
        "candidate": "C-04",
        "protocol_version": 2,
        "mode": "RESEARCH_FIXED_HORIZON_DIAGNOSTIC",
        "round_trip_cost": ROUND_TRIP_COST,
        "horizon_bars": HORIZON_BARS,
        "fold_count": FOLDS,
        "minimum_signals_per_fold": MIN_FOLD_SIGNALS,
        "errors": errors,
        "data_spans": data_spans,
        "overall": overall,
        **grouped,
        "gate": {
            "adequately_sampled_folds": len(adequate),
            "positive_folds": positive,
            "all_symbols_positive": symbol_positive,
            "both_sides_positive": side_positive,
            "verdict": "KEEP_FOR_PATH_DEPENDENT_CONFIRMATION" if passes else "REJECT",
        },
        "limitations": [
            "Fixed-horizon diagnostic; does not model production SL/TP paths.",
            "No funding observations in the historical candle files.",
            "Path-dependent confirmation is mandatory before any promotion.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/history/processed/5m")
    parser.add_argument("--output")
    args = parser.parse_args()
    previous_disable_level = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        report = build_report(Path(args.data_dir))
    finally:
        logging.disable(previous_disable_level)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
