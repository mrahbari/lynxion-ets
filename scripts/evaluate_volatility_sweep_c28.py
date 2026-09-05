#!/usr/bin/env python3
"""Evaluate preregistered C-28 volatility-sweep rejection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
EXTREME_LOOKBACK = 96
RANGE_LOOKBACK = 2880
RANGE_QUANTILE = 0.95
WICK_SHARE = 0.60
HOLD_BARS = 16
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)
PRIMARY_START, PRIMARY_END = 1704067200, 1788134400
REVERSE_START, REVERSE_END = 1672531200, 1704067200


def load_price(path: Path) -> pd.DataFrame:
    return (pd.read_csv(path, usecols=["timestamp", "open", "high", "low", "close"])
            .sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True))


def load_funding(path: Path) -> pd.DataFrame:
    return pd.read_csv(path).sort_values("timestamp").drop_duplicates("timestamp")


def causal_features(price: pd.DataFrame) -> pd.DataFrame:
    frame = price.copy().sort_values("timestamp").reset_index(drop=True)
    previous_close = frame.close.shift(1)
    frame["true_range"] = np.maximum.reduce([
        (frame.high - frame.low).to_numpy(),
        (frame.high - previous_close).abs().to_numpy(),
        (frame.low - previous_close).abs().to_numpy(),
    ])
    frame["prior_high"] = frame.high.shift(1).rolling(
        EXTREME_LOOKBACK, min_periods=EXTREME_LOOKBACK).max()
    frame["prior_low"] = frame.low.shift(1).rolling(
        EXTREME_LOOKBACK, min_periods=EXTREME_LOOKBACK).min()
    frame["range_threshold"] = frame.true_range.shift(1).rolling(
        RANGE_LOOKBACK, min_periods=RANGE_LOOKBACK).quantile(RANGE_QUANTILE)
    candle_range = frame.high - frame.low
    frame["upper_wick_share"] = (frame.high - frame[["open", "close"]].max(axis=1)) / candle_range
    frame["lower_wick_share"] = (frame[["open", "close"]].min(axis=1) - frame.low) / candle_range
    return frame


def signal_side(row: object) -> str | None:
    if (pd.isna(row.prior_high) or pd.isna(row.prior_low) or
            pd.isna(row.range_threshold) or row.high <= row.low or
            not row.true_range > row.range_threshold):
        return None
    bearish = (row.high > row.prior_high and row.close <= row.prior_high and
               row.upper_wick_share >= WICK_SHARE)
    bullish = (row.low < row.prior_low and row.close >= row.prior_low and
               row.lower_wick_share >= WICK_SHARE)
    if bearish == bullish:
        return None
    return "SHORT" if bearish else "LONG"


def collect_events(symbol: str, features: pd.DataFrame, funding: pd.DataFrame,
                   start: int, end: int) -> tuple[list[dict], dict]:
    indexed = features.set_index("timestamp")
    events: list[dict] = []
    last_exit = -1
    census = {key: 0 for key in (
        "period_rows", "warmup_rejected", "range_rejected", "sweep_rejected",
        "ambiguous_rejected", "missing_path", "overlap_rejected", "signals")}
    for row in features.itertuples(index=False):
        signal_ts = int(row.timestamp)
        entry_ts = signal_ts + 900
        if not start <= entry_ts < end:
            continue
        census["period_rows"] += 1
        if pd.isna(row.prior_high) or pd.isna(row.prior_low) or pd.isna(row.range_threshold):
            census["warmup_rejected"] += 1
            continue
        if row.high <= row.low or not row.true_range > row.range_threshold:
            census["range_rejected"] += 1
            continue
        bearish = (row.high > row.prior_high and row.close <= row.prior_high and
                   row.upper_wick_share >= WICK_SHARE)
        bullish = (row.low < row.prior_low and row.close >= row.prior_low and
                   row.lower_wick_share >= WICK_SHARE)
        if bearish and bullish:
            census["ambiguous_rejected"] += 1
            continue
        if not (bearish or bullish):
            census["sweep_rejected"] += 1
            continue
        census["signals"] += 1
        exit_ts = entry_ts + HOLD_BARS * 900
        expected = [entry_ts + offset * 900 for offset in range(HOLD_BARS + 1)]
        if any(timestamp not in indexed.index for timestamp in expected):
            census["missing_path"] += 1
            continue
        if entry_ts < last_exit:
            census["overlap_rejected"] += 1
            continue
        side = "SHORT" if bearish else "LONG"
        entry = float(indexed.loc[entry_ts, "open"])
        exit_price = float(indexed.loc[exit_ts, "open"])
        price_return = (exit_price / entry - 1) * (1 if side == "LONG" else -1)
        rates = funding.loc[(funding.timestamp > entry_ts) &
                            (funding.timestamp <= exit_ts), "funding_rate"].sum()
        funding_return = float(rates) * (-1 if side == "LONG" else 1)
        events.append({
            "symbol": symbol, "side": side, "signal_timestamp": signal_ts,
            "entry_timestamp": entry_ts, "exit_timestamp": exit_ts,
            "true_range": float(row.true_range),
            "range_threshold": float(row.range_threshold),
            "wick_share": float(row.upper_wick_share if bearish else row.lower_wick_share),
            "entry_price": entry, "exit_price": exit_price,
            "price_return": price_return, "funding_return": funding_return,
            "gross_return": price_return + funding_return,
        })
        last_exit = exit_ts
    return events, census


def assign_folds(events: list[dict]) -> None:
    timestamps = sorted(event["entry_timestamp"] for event in events)
    if not timestamps:
        return
    bounds = [timestamps[index * len(timestamps) // 4] for index in range(4)]
    for event in events:
        event["fold"] = max(index for index, bound in enumerate(bounds)
                            if event["entry_timestamp"] >= bound) + 1


def metrics(events: list[dict], cost: float = PRIMARY_COST) -> dict:
    values = np.asarray([event["gross_return"] - cost for event in events])
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None,
                "win_rate": None, "max_drawdown": None}
    wins, losses = values[values > 0], values[values <= 0]
    equity = values.cumsum()
    peak = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    return {
        "n": int(len(values)), "expectancy": float(values.mean()),
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
        "win_rate": float((values > 0).mean()),
        "max_drawdown": float((peak - equity).max(initial=0)),
    }


def bootstrap(events: list[dict], samples: int = 10_000) -> list[float | None]:
    if not events:
        return [None, None]
    clusters: dict[int, list[float]] = {}
    for event in events:
        clusters.setdefault(event["entry_timestamp"] // 86400, []).append(
            event["gross_return"] - PRIMARY_COST)
    keys = sorted(clusters)
    rng = np.random.default_rng(280028)
    estimates = np.empty(samples)
    for index in range(samples):
        selected = rng.choice(keys, len(keys), replace=True)
        estimates[index] = np.mean([value for key in selected for value in clusters[int(key)]])
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def summarize(events: list[dict]) -> dict:
    years = sorted({pd.to_datetime(event["entry_timestamp"], unit="s", utc=True).year
                    for event in events})
    return {
        "overall": metrics(events), "clustered_bootstrap_95_ci": bootstrap(events),
        "by_fold": {f"F{fold}": metrics([e for e in events if e.get("fold") == fold])
                    for fold in range(1, 5)},
        "by_side": {side: metrics([e for e in events if e["side"] == side])
                    for side in ("LONG", "SHORT")},
        "by_symbol": {symbol: metrics([e for e in events if e["symbol"] == symbol])
                      for symbol in SYMBOLS},
        "by_year": {str(year): metrics([e for e in events if pd.to_datetime(
            e["entry_timestamp"], unit="s", utc=True).year == year]) for year in years},
        "cost_sensitivity": {f"{cost:.3f}": metrics(events, cost) for cost in COSTS},
        "mean_funding_return": float(np.mean([e["funding_return"] for e in events]))
        if events else None,
    }


def positive_symbol_concentration(events: list[dict]) -> float | None:
    values = {symbol: sum(max(0, event["gross_return"] - PRIMARY_COST)
                          for event in events if event["symbol"] == symbol)
              for symbol in SYMBOLS}
    total = sum(values.values())
    return max(values.values(), default=0) / total if total else None


def build_report(price_dir: Path, funding_dir: Path) -> dict:
    primary, reverse, primary_census, reverse_census = [], [], {}, {}
    for symbol in SYMBOLS:
        features = causal_features(load_price(price_dir / f"{symbol}.csv"))
        funding = load_funding(funding_dir / f"{symbol}.csv")
        selected, counts = collect_events(symbol, features, funding, PRIMARY_START, PRIMARY_END)
        primary.extend(selected); primary_census[symbol] = counts
        selected, counts = collect_events(symbol, features, funding, REVERSE_START, REVERSE_END)
        reverse.extend(selected); reverse_census[symbol] = counts
    assign_folds(primary); assign_folds(reverse)
    primary_summary, reverse_summary = summarize(primary), summarize(reverse)
    concentration = positive_symbol_concentration(primary)
    overall = primary_summary["overall"]
    checks = {
        "primary_n": overall["n"] >= 500,
        "primary_positive": overall["expectancy"] is not None and overall["expectancy"] > 0,
        "primary_pf": overall["profit_factor"] is not None and overall["profit_factor"] > 1,
        "bootstrap": primary_summary["clustered_bootstrap_95_ci"][0] is not None and
        primary_summary["clustered_bootstrap_95_ci"][0] > 0,
        "folds": sum(v["n"] >= 75 and v["expectancy"] is not None and v["expectancy"] > 0
                     for v in primary_summary["by_fold"].values()) >= 3,
        "sides": all(v["n"] >= 150 and v["expectancy"] is not None and v["expectancy"] > 0
                     for v in primary_summary["by_side"].values()),
        "symbols": sum(v["n"] >= 50 and v["expectancy"] is not None and v["expectancy"] > 0
                       for v in primary_summary["by_symbol"].values()) >= 4,
        "years": all(primary_summary["by_year"].get(str(year), {"n": 0})["n"] >= 100 and
                     primary_summary["by_year"][str(year)]["expectancy"] > 0
                     for year in (2024, 2025, 2026)),
        "concentration": concentration is not None and concentration <= 0.30,
        "reverse": reverse_summary["overall"]["n"] >= 150 and
        reverse_summary["overall"]["expectancy"] is not None and
        reverse_summary["overall"]["expectancy"] > 0 and
        reverse_summary["overall"]["profit_factor"] is not None and
        reverse_summary["overall"]["profit_factor"] > 1,
        "cost_005": primary_summary["cost_sensitivity"]["0.005"]["expectancy"] is not None and
        primary_summary["cost_sensitivity"]["0.005"]["expectancy"] > 0,
    }
    return {
        "candidate": "C-28", "protocol": "edge-candidate-register-v27",
        "primary_census": primary_census, "reverse_census": reverse_census,
        "primary": primary_summary, "reverse": reverse_summary,
        "max_positive_pnl_symbol_concentration": concentration,
        "gate": {"checks": checks, "verdict": "KEEP_FOR_PROSPECTIVE_VALIDATION"
                 if all(checks.values()) else "REJECT"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--funding-dir", default="data/research/c16/funding")
    parser.add_argument("--output", default="docs/reports/edge_candidate_c28.json")
    args = parser.parse_args()
    report = build_report(Path(args.price_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
