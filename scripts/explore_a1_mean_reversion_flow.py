#!/usr/bin/env python3
"""Bounded exploratory A1 comparison: 15m reversal with/without aggressive flow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


SYMBOLS = ("ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT")
LOOKBACK = 2_880
RETURN_PERCENTILE = 0.90
FLOW_PERCENTILES = (0.70, 0.75, 0.80)
PRIMARY_FLOW_PERCENTILE = 0.75
PRIMARY_COST = 0.003
STRESS_COST = 0.005
HOLD_BARS = 4
BOOTSTRAP_SAMPLES = 2_000
BOOTSTRAP_SEED = 360368


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    if negative == 0:
        return None if positive == 0 else float("inf")
    return positive / negative


def metrics(frame: pd.DataFrame, column: str = "net_return") -> dict:
    values = frame[column].astype(float)
    if frame.empty:
        return {"n": 0, "day_clusters": 0, "expectancy": None, "profit_factor": None, "win_rate": None}
    return {
        "n": int(len(frame)),
        "day_clusters": int(frame["entry_day"].nunique()),
        "expectancy": float(values.mean()),
        "profit_factor": profit_factor(values),
        "win_rate": float((values > 0).mean()),
    }


def clustered_interval(frame: pd.DataFrame) -> list[float] | None:
    if frame.empty:
        return None
    grouped = frame.groupby("entry_day")["net_return"].agg(["sum", "count"])
    if len(grouped) < 2:
        return None
    sums = grouped["sum"].to_numpy(float)
    counts = grouped["count"].to_numpy(float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    estimates = np.empty(BOOTSTRAP_SAMPLES)
    for index in range(BOOTSTRAP_SAMPLES):
        sampled = rng.integers(0, len(grouped), len(grouped))
        estimates[index] = sums[sampled].sum() / counts[sampled].sum()
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def load_funding(path: Path) -> tuple[np.ndarray, np.ndarray]:
    frame = pd.read_csv(path, usecols=["timestamp", "funding_rate"])
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna().sort_values("timestamp")
    return frame["timestamp"].to_numpy(np.int64), frame["funding_rate"].to_numpy(float)


def funding_return(
    entry: int,
    exit_: int,
    side: int,
    timestamps: np.ndarray,
    rates: np.ndarray,
) -> float:
    left = int(np.searchsorted(timestamps, entry, side="right"))
    right = int(np.searchsorted(timestamps, exit_, side="right"))
    return float(-side * rates[left:right].sum())


def build_symbol_events(flow_path: Path, funding_path: Path, symbol: str) -> pd.DataFrame:
    columns = ["timestamp", "open", "close", "quote_volume", "taker_buy_quote_volume"]
    frame = pd.read_csv(flow_path, usecols=columns)
    frame[columns] = frame[columns].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna().sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    if len(frame) < LOOKBACK + HOLD_BARS + 2:
        return pd.DataFrame()

    frame["formation_return"] = frame["close"].pct_change()
    frame["return_threshold"] = (
        frame["formation_return"].abs().shift(1).rolling(LOOKBACK, min_periods=LOOKBACK).quantile(RETURN_PERCENTILE)
    )
    frame["flow_score"] = (
        2.0 * frame["taker_buy_quote_volume"] - frame["quote_volume"]
    ) / frame["quote_volume"]
    for percentile in FLOW_PERCENTILES:
        frame[f"flow_threshold_{int(percentile * 100)}"] = (
            frame["flow_score"].abs().shift(1).rolling(LOOKBACK, min_periods=LOOKBACK).quantile(percentile)
        )

    funding_timestamps, funding_rates = load_funding(funding_path)
    timestamps = frame["timestamp"].to_numpy(np.int64)
    opens = frame["open"].to_numpy(float)
    formations = frame["formation_return"].to_numpy(float)
    return_thresholds = frame["return_threshold"].to_numpy(float)
    flow_scores = frame["flow_score"].to_numpy(float)
    flow_thresholds = {
        percentile: frame[f"flow_threshold_{int(percentile * 100)}"].to_numpy(float)
        for percentile in FLOW_PERCENTILES
    }
    valid = np.isfinite(formations) & np.isfinite(return_thresholds) & (np.abs(formations) > return_thresholds)
    candidate_indices = np.flatnonzero(valid)
    candidate_indices = candidate_indices[
        (candidate_indices >= LOOKBACK + 1) & (candidate_indices < len(frame) - HOLD_BARS - 1)
    ]
    selected_indices = []
    last_exit = -1
    for index in candidate_indices:
        entry_timestamp = int(timestamps[index + 1])
        exit_timestamp = int(timestamps[index + 1 + HOLD_BARS])
        if entry_timestamp >= last_exit:
            selected_indices.append(int(index))
            last_exit = exit_timestamp

    rows = []
    for index in selected_indices:
        formation = float(formations[index])
        entry_index = index + 1
        exit_index = entry_index + HOLD_BARS
        entry_timestamp = int(timestamps[entry_index])
        exit_timestamp = int(timestamps[exit_index])
        entry_price = float(opens[entry_index])
        exit_price = float(opens[exit_index])
        if not all(np.isfinite(value) and value > 0 for value in (entry_price, exit_price)):
            continue
        side = -1 if formation > 0 else 1
        gross = side * (exit_price / entry_price - 1.0)
        funding = funding_return(entry_timestamp, exit_timestamp, side, funding_timestamps, funding_rates)
        flow_score = float(flow_scores[index])
        output = {
            "symbol": symbol,
            "decision_timestamp": int(timestamps[index]) + 900,
            "entry_timestamp": entry_timestamp,
            "exit_timestamp": exit_timestamp,
            "entry_day": pd.to_datetime(entry_timestamp, unit="s", utc=True).strftime("%Y-%m-%d"),
            "side": "LONG" if side == 1 else "SHORT",
            "gross_return": gross,
            "funding_return": funding,
            "net_return": gross + funding - PRIMARY_COST,
            "stress_return": gross + funding - STRESS_COST,
            "flow_score": flow_score,
        }
        for percentile in FLOW_PERCENTILES:
            flow_threshold = float(flow_thresholds[percentile][index])
            output[f"flow_p{int(percentile * 100)}"] = bool(
                np.isfinite(flow_threshold)
                and np.sign(flow_score) == np.sign(formation)
                and abs(flow_score) > flow_threshold
            )
        rows.append(output)
        last_exit = exit_timestamp
    return pd.DataFrame(rows)


def fold_report(frame: pd.DataFrame, boundaries: np.ndarray) -> list[dict]:
    if frame.empty:
        return []
    labels = np.searchsorted(boundaries, frame["entry_timestamp"].to_numpy(), side="right")
    return [{"fold": int(fold + 1), **metrics(frame.loc[labels == fold])} for fold in range(4)]


def concentration(frame: pd.DataFrame) -> float | None:
    positive = frame.loc[frame["net_return"] > 0].groupby("symbol")["net_return"].sum()
    total = float(positive.sum())
    return None if total <= 0 else float(positive.max() / total)


def sample_report(frame: pd.DataFrame, boundaries: np.ndarray) -> dict:
    by_symbol = {symbol: metrics(part) for symbol, part in frame.groupby("symbol", sort=True)}
    by_side = {side: metrics(part) for side, part in frame.groupby("side", sort=True)}
    return {
        "metrics": metrics(frame),
        "stress_metrics": metrics(frame.rename(columns={"net_return": "primary_return", "stress_return": "net_return"})),
        "clustered_bootstrap_95": clustered_interval(frame),
        "folds": fold_report(frame, boundaries),
        "by_symbol": by_symbol,
        "by_side": by_side,
        "max_positive_pnl_symbol_concentration": concentration(frame),
        "funding_mean": None if frame.empty else float(frame["funding_return"].mean()),
    }


def build_report(flow_dir: Path, funding_dir: Path) -> dict:
    frames = [
        build_symbol_events(flow_dir / f"{symbol}.csv.gz", funding_dir / f"{symbol}.csv", symbol)
        for symbol in SYMBOLS
    ]
    baseline = pd.concat(frames, ignore_index=True).sort_values(["entry_timestamp", "symbol"])
    boundaries = np.quantile(baseline["entry_timestamp"].to_numpy(), [0.25, 0.50, 0.75])
    baseline_report = sample_report(baseline, boundaries)
    conditions = {}
    for percentile in FLOW_PERCENTILES:
        selected = baseline.loc[baseline[f"flow_p{int(percentile * 100)}"]].copy()
        report = sample_report(selected, boundaries)
        report["incremental_expectancy_vs_baseline"] = (
            None if selected.empty else float(selected["net_return"].mean() - baseline["net_return"].mean())
        )
        conditions[f"p{int(percentile * 100)}"] = report

    primary = conditions["p75"]
    primary_symbols_positive = sum(
        1 for value in primary["by_symbol"].values() if value["expectancy"] is not None and value["expectancy"] > 0
    )
    improved_folds = sum(
        1
        for base_fold, conditioned_fold in zip(baseline_report["folds"], primary["folds"])
        if conditioned_fold["expectancy"] is not None
        and base_fold["expectancy"] is not None
        and conditioned_fold["expectancy"] > base_fold["expectancy"]
        and conditioned_fold["expectancy"] > 0
    )
    interval = primary["clustered_bootstrap_95"]
    gates = {
        "positive_primary_expectancy": primary["metrics"]["expectancy"] is not None and primary["metrics"]["expectancy"] > 0,
        "improves_baseline": primary["incremental_expectancy_vs_baseline"] is not None and primary["incremental_expectancy_vs_baseline"] > 0,
        "three_positive_improved_folds": improved_folds >= 3,
        "positive_stress_expectancy": primary["stress_metrics"]["expectancy"] is not None and primary["stress_metrics"]["expectancy"] > 0,
        "four_positive_symbols": primary_symbols_positive >= 4,
        "bootstrap_lower_above_zero": interval is not None and interval[0] > 0,
        "concentration_at_most_35pct": primary["max_positive_pnl_symbol_concentration"] is not None and primary["max_positive_pnl_symbol_concentration"] <= 0.35,
    }
    return {
        "study": "A1_15M_MEAN_REVERSION_PLUS_AGGRESSIVE_FLOW",
        "label": "EXPLORATORY_NOT_CONFIRMATORY",
        "protocol": "TASK-0368",
        "configuration": {
            "symbols": list(SYMBOLS), "lookback_bars": LOOKBACK,
            "return_percentile": RETURN_PERCENTILE, "flow_percentiles": list(FLOW_PERCENTILES),
            "primary_cost": PRIMARY_COST, "stress_cost": STRESS_COST, "hold_bars": HOLD_BARS,
            "bootstrap_samples": BOOTSTRAP_SAMPLES, "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "baseline": baseline_report,
        "flow_conditions": conditions,
        "primary_gates": gates,
        "verdict": "PREREGISTRATION_JUSTIFIED" if all(gates.values()) else "REJECT_OR_PARK",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-dir", type=Path, default=Path("data/research/taker_flow/normalized"))
    parser.add_argument("--funding-dir", type=Path, default=Path("data/research/c16/funding"))
    parser.add_argument("--output", type=Path, default=Path("docs/reports/a1_mean_reversion_flow_exploratory.json"))
    args = parser.parse_args()
    report = build_report(args.flow_dir, args.funding_dir)
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
