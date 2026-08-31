#!/usr/bin/env python3
"""Evaluate preregistered C-23 delta-neutral positive-funding carry."""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
PRIMARY_START, PRIMARY_END = 1704067200, 1788134400
REVERSE_START, REVERSE_END = 1672531200, 1704067200
PRIMARY_COST = 0.002
COSTS = (0.0015, 0.002, 0.003, 0.005)
FOLDS = 4


def causal_funding(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    frame["funding_rate"] = pd.to_numeric(frame["funding_rate"], errors="coerce")
    frame["threshold"] = frame["funding_rate"].shift(1).rolling(180, min_periods=180).quantile(0.75)
    frame["next_timestamp"] = frame["timestamp"].shift(-1)
    frame["next_rate"] = frame["funding_rate"].shift(-1)
    return frame


def load_open(path: Path) -> pd.Series:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        frame = pd.read_csv(handle, usecols=["timestamp", "open"])
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp")
    frame["open"] = pd.to_numeric(frame["open"], errors="coerce")
    return frame.set_index("timestamp")["open"]


def symbol_events(symbol: str, funding: pd.DataFrame, spot: pd.Series, perp: pd.Series,
                  start: int, end: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    census = {"settlements": 0, "warmup_rejected": 0, "non_signal": 0,
              "missing_next_settlement": 0, "missing_exact_price": 0, "overlap_rejected": 0}
    events: list[dict[str, Any]] = []
    last_exit = -1
    for row in funding.itertuples(index=False):
        timestamp = int(row.timestamp)
        if not start <= timestamp < end:
            continue
        census["settlements"] += 1
        if pd.isna(row.threshold):
            census["warmup_rejected"] += 1
            continue
        rate, threshold = float(row.funding_rate), float(row.threshold)
        if not rate > 0 or not rate > threshold:
            census["non_signal"] += 1
            continue
        if pd.isna(row.next_timestamp) or pd.isna(row.next_rate):
            census["missing_next_settlement"] += 1
            continue
        entry_timestamp = timestamp + 900
        next_settlement = int(row.next_timestamp)
        exit_timestamp = next_settlement + 900
        if entry_timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        if (entry_timestamp not in spot.index or exit_timestamp not in spot.index or
                entry_timestamp not in perp.index or exit_timestamp not in perp.index):
            census["missing_exact_price"] += 1
            continue
        spot_entry, spot_exit = float(spot.loc[entry_timestamp]), float(spot.loc[exit_timestamp])
        perp_entry, perp_exit = float(perp.loc[entry_timestamp]), float(perp.loc[exit_timestamp])
        if min(spot_entry, spot_exit, perp_entry, perp_exit) <= 0:
            census["missing_exact_price"] += 1
            continue
        spot_return = spot_exit / spot_entry - 1.0
        perp_short_return = (perp_entry - perp_exit) / perp_entry
        short_funding_return = float(row.next_rate)
        basis_return = (spot_return + perp_short_return) / 2.0
        funding_return = short_funding_return / 2.0
        gross_return = basis_return + funding_return
        events.append({"symbol": symbol, "signal_timestamp": timestamp,
                       "entry_timestamp": entry_timestamp, "next_settlement": next_settlement,
                       "exit_timestamp": exit_timestamp, "signal_rate": rate,
                       "threshold": threshold, "next_funding_rate": short_funding_return,
                       "spot_return": spot_return, "perp_short_return": perp_short_return,
                       "basis_return": basis_return, "funding_return": funding_return,
                       "gross_return": gross_return})
        last_exit = exit_timestamp
    return events, census


def assign_folds(events: list[dict[str, Any]]) -> None:
    timestamps = sorted(event["entry_timestamp"] for event in events)
    if not timestamps:
        return
    boundaries = [timestamps[index * len(timestamps) // FOLDS] for index in range(FOLDS)]
    for event in events:
        event["fold"] = max(index for index, boundary in enumerate(boundaries)
                            if event["entry_timestamp"] >= boundary) + 1


def metrics(events: list[dict[str, Any]], cost: float = PRIMARY_COST) -> dict[str, Any]:
    values = np.asarray([event["gross_return"] - cost for event in events], dtype=float)
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "max_drawdown": None}
    wins, losses = values[values > 0], values[values <= 0]
    equity = values.cumsum(); peaks = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    return {"n": int(len(values)), "expectancy": float(values.mean()),
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
            "win_rate": float((values > 0).mean()), "max_drawdown": float((peaks - equity).max(initial=0.0))}


def clustered_bootstrap_ci(events: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not events:
        return [None, None]
    clusters: dict[int, list[float]] = {}
    for event in events:
        day = event["entry_timestamp"] // 86400
        clusters.setdefault(day, []).append(event["gross_return"] - PRIMARY_COST)
    days = sorted(clusters); rng = np.random.default_rng(230023); estimates = np.empty(samples)
    for index in range(samples):
        selected = rng.choice(days, len(days), replace=True)
        values = [value for day in selected for value in clusters[int(day)]]
        estimates[index] = np.mean(values)
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def period_events(spot_dir: Path, perp_dir: Path, funding_dir: Path, start: int, end: int):
    events: list[dict[str, Any]] = []; census = {}
    for symbol in SYMBOLS:
        funding = causal_funding(funding_dir / f"{symbol}.csv")
        spot = load_open(spot_dir / f"{symbol}.csv.gz")
        perp = load_open(perp_dir / f"{symbol}.csv")
        selected, counts = symbol_events(symbol, funding, spot, perp, start, end)
        events.extend(selected); census[symbol] = counts
    assign_folds(events)
    return events, census


def summarize(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {"overall": metrics(events), "clustered_bootstrap_95_ci": clustered_bootstrap_ci(events),
            "by_fold": {f"F{i}": metrics([e for e in events if e["fold"] == i]) for i in range(1, 5)},
            "by_symbol": {s: metrics([e for e in events if e["symbol"] == s]) for s in SYMBOLS},
            "by_year": {str(year): metrics([e for e in events if pd.to_datetime(e["entry_timestamp"], unit="s", utc=True).year == year]) for year in sorted({pd.to_datetime(e["entry_timestamp"], unit="s", utc=True).year for e in events})},
            "cost_sensitivity": {f"{cost:.4f}": metrics(events, cost) for cost in COSTS},
            "mean_spot_return": float(np.mean([e["spot_return"] for e in events])) if events else None,
            "mean_perp_short_return": float(np.mean([e["perp_short_return"] for e in events])) if events else None,
            "mean_basis_return": float(np.mean([e["basis_return"] for e in events])) if events else None,
            "mean_funding_return": float(np.mean([e["funding_return"] for e in events])) if events else None}


def build_report(spot_dir: Path, perp_dir: Path, funding_dir: Path) -> dict[str, Any]:
    primary, primary_census = period_events(spot_dir, perp_dir, funding_dir, PRIMARY_START, PRIMARY_END)
    reverse, reverse_census = period_events(spot_dir, perp_dir, funding_dir, REVERSE_START, REVERSE_END)
    p, r = summarize(primary), summarize(reverse)
    positive = {s: sum(max(0.0, e["gross_return"] - PRIMARY_COST) for e in primary if e["symbol"] == s) for s in SYMBOLS}
    total = sum(positive.values()); concentration = max(positive.values(), default=0.0) / total if total else None
    folds = p["by_fold"]; symbols = p["by_symbol"]
    checks = {"primary_n": p["overall"]["n"] >= 1000,
              "primary_positive": p["overall"]["expectancy"] is not None and p["overall"]["expectancy"] > 0,
              "primary_pf": p["overall"]["profit_factor"] is not None and p["overall"]["profit_factor"] > 1,
              "bootstrap_lower_positive": p["clustered_bootstrap_95_ci"][0] is not None and p["clustered_bootstrap_95_ci"][0] > 0,
              "fold_breadth": sum(v["n"] >= 150 and v["expectancy"] > 0 for v in folds.values()) >= 3,
              "symbol_breadth": sum(v["n"] >= 100 and v["expectancy"] > 0 for v in symbols.values()) >= 5,
              "concentration": concentration is not None and concentration <= 0.30,
              "reverse": r["overall"]["n"] >= 250 and r["overall"]["expectancy"] > 0 and r["overall"]["profit_factor"] > 1,
              "cost_003_positive": p["cost_sensitivity"]["0.0030"]["expectancy"] > 0}
    return {"candidate": "C-23", "protocol": "edge-candidate-register-v22",
            "primary_census": primary_census, "reverse_census": reverse_census,
            "primary": p, "reverse": r, "max_positive_pnl_symbol_concentration": concentration,
            "gate": {"checks": checks, "verdict": "KEEP_FOR_PROSPECTIVE_VALIDATION" if all(checks.values()) else "REJECT"}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spot-dir", default="data/research/spot_15m/normalized")
    parser.add_argument("--perp-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--funding-dir", default="data/research/c16/funding")
    parser.add_argument("--output", default="docs/reports/edge_candidate_c23.json")
    args = parser.parse_args(); report = build_report(Path(args.spot_dir), Path(args.perp_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
