#!/usr/bin/env python3
"""Evaluate frozen C-01/C-02/C-03 with causal filters and path-dependent exits."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from domain.value_objects import Symbol
from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
from infrastructure.strategies.strategy_adapters import VolatilityBreakoutStrategy

SYMBOLS = ("BTC-USDT", "ETH-USDT", "SOL-USDT")
COST = 0.003
FOLDS = 4
MIN_FOLD_TRADES = 10


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.astype(float).ewm(span=span, adjust=False, min_periods=span).mean()


def true_range(frame: pd.DataFrame) -> pd.Series:
    close = frame["close"].astype(float)
    previous = close.shift(1)
    return pd.concat([
        frame["high"].astype(float) - frame["low"].astype(float),
        (frame["high"].astype(float) - previous).abs(),
        (frame["low"].astype(float) - previous).abs(),
    ], axis=1).max(axis=1)


def wilder_adx(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)
    atr = true_range(frame).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def causal_features(frame15: pd.DataFrame, frame1h: pd.DataFrame) -> pd.DataFrame:
    result = frame15.copy().sort_values("timestamp").reset_index(drop=True)
    result["ema20_15m"] = ema(result["close"], 20)
    result["ema50_15m"] = ema(result["close"], 50)
    result["adx14"] = wilder_adx(result)
    atr = true_range(result).rolling(14).mean()
    result["atr14"] = atr
    result["atr_median_prior100"] = atr.shift(1).rolling(100).median()

    hourly = frame1h.copy().sort_values("timestamp").reset_index(drop=True)
    hourly["ema20_1h"] = ema(hourly["close"], 20).shift(1)
    hourly["ema50_1h"] = ema(hourly["close"], 50).shift(1)
    return pd.merge_asof(
        result.sort_values("timestamp"),
        hourly[["timestamp", "ema20_1h", "ema50_1h"]].sort_values("timestamp"),
        on="timestamp",
        direction="backward",
    )


def metrics(values: Iterable[float]) -> dict[str, Any]:
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
    average_win = gross_profit / len(wins) if wins else None
    average_loss = sum(losses) / len(losses) if losses else None
    return {
        "n": len(returns),
        "expectancy": sum(returns) / len(returns) if returns else None,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "win_rate": len(wins) / len(returns) if returns else None,
        "average_win": average_win,
        "average_loss": average_loss,
        "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
        "max_drawdown_return_units": drawdown,
    }


def signal_side(signal: Any) -> str:
    name = (getattr(getattr(signal, "signal_type", None), "name", "") or "").upper()
    return "BUY" if "BUY" in name or "LONG" in name else "SELL" if "SELL" in name or "SHORT" in name else ""


def collect_signals(frame: pd.DataFrame, symbol: str, adapter: Any, candidate: str) -> list[dict[str, Any]]:
    domain_symbol = Symbol(symbol.replace("-", ""))
    signals = []
    for index, row in enumerate(frame.itertuples(index=False)):
        adapter.update_with_market_data({
            "timestamp": row.timestamp, "open": float(row.open), "high": float(row.high),
            "low": float(row.low), "close": float(row.close), "volume": float(row.volume),
        })
        signal = adapter.generate_signal(domain_symbol)
        if signal is None or index + 1 >= len(frame):
            continue
        side = signal_side(signal)
        setup = (getattr(signal, "metadata", None) or {}).get("setup")
        if not side or setup is None:
            continue
        if candidate == "C-01" and not (
            side == "BUY" and row.ema20_15m > row.ema50_15m
            and row.ema20_1h > row.ema50_1h and row.adx14 >= 25
        ):
            continue
        if candidate == "C-02" and not (
            side == "SELL" and row.ema20_15m < row.ema50_15m
            and row.ema20_1h < row.ema50_1h and row.adx14 >= 25
        ):
            continue
        if candidate == "C-03" and not (
            row.atr_median_prior100 > 0 and row.atr14 > 1.10 * row.atr_median_prior100
        ):
            continue
        signals.append({
            "signal_index": index, "entry_index": index + 1, "side": side,
            "stop": float(setup.stop_loss_level), "take_profit": float(setup.take_profit_level),
        })
    return signals


def simulate_fold(frame: pd.DataFrame, signals: list[dict[str, Any]], lo: int, hi: int) -> tuple[list[dict[str, Any]], int]:
    trades = []
    unresolved = 0
    next_free_index = lo
    for signal in signals:
        entry_index = signal["entry_index"]
        if entry_index < lo or entry_index >= hi or entry_index < next_free_index:
            continue
        entry = float(frame.iloc[entry_index]["open"])
        side = signal["side"]
        stop = signal["stop"]
        take_profit = signal["take_profit"]
        exit_price = None
        exit_index = None
        exit_reason = None
        for index in range(entry_index, hi):
            bar = frame.iloc[index]
            opened, high, low = float(bar.open), float(bar.high), float(bar.low)
            if side == "BUY":
                if low <= stop:  # SL priority, including dual-touch candles
                    exit_price, exit_reason = min(opened, stop), "SL"
                elif high >= take_profit:
                    exit_price, exit_reason = take_profit, "TP"
            else:
                if high >= stop:
                    exit_price, exit_reason = max(opened, stop), "SL"
                elif low <= take_profit:
                    exit_price, exit_reason = take_profit, "TP"
            if exit_price is not None:
                exit_index = index
                break
        if exit_price is None:
            unresolved += 1
            # The position remains open through the fold boundary, so no later
            # signal in this fold can be admitted for the same symbol.
            break
        direction = 1.0 if side == "BUY" else -1.0
        trades.append({
            **signal, "entry_price": entry, "exit_price": exit_price, "exit_index": exit_index,
            "exit_reason": exit_reason, "net_return": direction * (exit_price - entry) / entry - COST,
        })
        next_free_index = exit_index + 1
    return trades, unresolved


def evaluate_candidate(candidate: str, data_dir: Path) -> dict[str, Any]:
    universe = SYMBOLS if candidate != "C-02" else SYMBOLS[:2]
    all_trades = []
    unresolved = 0
    errors = []
    for symbol in universe:
        try:
            frame15 = pd.read_csv(data_dir / "15m" / f"{symbol}.csv")
            frame1h = pd.read_csv(data_dir / "1h" / f"{symbol}.csv")
            frame = causal_features(frame15, frame1h)
            adapter = TrendFollowStrategyAdapter({}) if candidate in ("C-01", "C-02") else VolatilityBreakoutStrategy({})
            signals = collect_signals(frame, symbol, adapter, candidate)
            for fold in range(1, FOLDS + 1):
                lo, hi = (fold - 1) * len(frame) // FOLDS, fold * len(frame) // FOLDS
                trades, missed = simulate_fold(frame, signals, lo, hi)
                unresolved += missed
                for trade in trades:
                    trade.update({"candidate": candidate, "symbol": symbol.replace("-", ""), "fold": fold})
                all_trades.extend(trades)
        except Exception as error:
            errors.append(f"{symbol}:{type(error).__name__}:{error}")

    groups = {}
    for group_name, key_fn in {
        "by_fold": lambda trade: f"F{trade['fold']}",
        "by_symbol": lambda trade: trade["symbol"],
        "by_side": lambda trade: trade["side"],
        "by_exit": lambda trade: trade["exit_reason"],
    }.items():
        buckets = defaultdict(list)
        for trade in all_trades:
            buckets[key_fn(trade)].append(trade["net_return"])
        groups[group_name] = {key: metrics(values) for key, values in sorted(buckets.items())}
    overall = metrics(trade["net_return"] for trade in all_trades)
    folds = groups.get("by_fold", {})
    adequate = [value for value in folds.values() if value["n"] >= MIN_FOLD_TRADES]
    positive_folds = sum(value["expectancy"] is not None and value["expectancy"] > 0 for value in adequate)
    symbols_positive = len(groups.get("by_symbol", {})) == len(universe) and all(
        value["expectancy"] is not None and value["expectancy"] > 0 for value in groups["by_symbol"].values()
    )
    sides_positive = candidate != "C-03" or (
        len(groups.get("by_side", {})) == 2 and all(
            value["expectancy"] is not None and value["expectancy"] > 0 for value in groups["by_side"].values()
        )
    )
    passes = (
        not errors and len(adequate) == FOLDS and positive_folds >= 3
        and overall["profit_factor"] is not None and overall["profit_factor"] > 1
        and symbols_positive and sides_positive
    )
    return {
        "candidate": candidate, "round_trip_cost": COST, "fold_count": FOLDS,
        "errors": errors, "unresolved_at_fold_end": unresolved, "overall": overall, **groups,
        "gate": {
            "adequately_sampled_folds": len(adequate), "positive_folds": positive_folds,
            "all_symbols_positive": symbols_positive, "required_sides_positive": sides_positive,
            "verdict": "KEEP_FOR_FURTHER_VALIDATION" if passes else "REJECT",
        },
    }


def build_report(data_dir: Path) -> dict[str, Any]:
    return {
        "protocol": "edge-candidate-register-v3",
        "mode": "RESEARCH_PATH_DEPENDENT_OOS",
        "candidates": {candidate: evaluate_candidate(candidate, data_dir) for candidate in ("C-01", "C-02", "C-03")},
        "limitations": [
            "Historical candle files contain no funding observations.",
            "Spread quality is represented by the preregistered round-trip cost because historical bid/ask is unavailable.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/history/processed")
    parser.add_argument("--output")
    args = parser.parse_args()
    previous = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        report = build_report(Path(args.data_dir))
    finally:
        logging.disable(previous)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
