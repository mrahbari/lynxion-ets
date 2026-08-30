#!/usr/bin/env python3
"""Evaluate preregistered C-18 near-book depth imbalance."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
DECISION_SECONDS = 4 * 3600
MAX_BOOK_AGE = 300
EXIT_SECONDS = 24 * 3600
BAR_SECONDS = 900
WARMUP = 180
FOLDS = 4
PRIMARY_START = int(pd.Timestamp("2024-01-01", tz="UTC").timestamp())
PRIMARY_END = int(pd.Timestamp("2026-08-29 23:59:59", tz="UTC").timestamp())
REVERSE_START = int(pd.Timestamp("2023-01-01", tz="UTC").timestamp())
REVERSE_END = int(pd.Timestamp("2023-12-31 23:59:59", tz="UTC").timestamp())
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)


def _mechanics():
    path = Path(__file__).with_name("evaluate_oi_confirmed_impulse_c16.py")
    spec = importlib.util.spec_from_file_location("c16_mechanics", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_book(path: Path) -> pd.DataFrame:
    columns = ["timestamp", "notional_m1", "notional_p1"]
    frame = pd.read_csv(path, usecols=columns).sort_values("timestamp").drop_duplicates("timestamp")
    frame[columns] = frame[columns].apply(pd.to_numeric, errors="coerce")
    return frame.dropna().set_index("timestamp")


def causal_features(price: pd.DataFrame, book: pd.DataFrame) -> pd.DataFrame:
    decisions = np.asarray(sorted(int(timestamp) for timestamp in price.index
                                  if int(timestamp) % DECISION_SECONDS == 0), dtype=np.int64)
    book_timestamps = book.index.to_numpy(dtype=np.int64)
    positions = np.searchsorted(book_timestamps, decisions, side="left") - 1
    rows = []
    for decision, position in zip(decisions, positions):
        if position < 0:
            continue
        snapshot_timestamp = int(book_timestamps[position])
        age = int(decision) - snapshot_timestamp
        if age <= 0 or age > MAX_BOOK_AGE:
            continue
        bid = float(book.iloc[position]["notional_m1"])
        ask = float(book.iloc[position]["notional_p1"])
        denominator = bid + ask
        if not np.isfinite(denominator) or denominator <= 0:
            continue
        imbalance = (bid - ask) / denominator
        if not np.isfinite(imbalance):
            continue
        rows.append({"decision_timestamp": int(decision), "snapshot_timestamp": snapshot_timestamp,
                     "book_age_seconds": age, "imbalance": imbalance})
    if not rows:
        return pd.DataFrame(columns=["snapshot_timestamp", "book_age_seconds", "imbalance",
                                     "threshold"]).rename_axis("decision_timestamp")
    frame = pd.DataFrame(rows).set_index("decision_timestamp")
    frame["threshold"] = frame["imbalance"].abs().shift(1).rolling(
        WARMUP, min_periods=WARMUP
    ).quantile(0.90)
    return frame


def collect_trades(symbol: str, price: pd.DataFrame, book: pd.DataFrame, funding: pd.Series,
                   start: int, end: int, fold_boundaries: list[int] | None = None
                   ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    features = causal_features(price, book)
    in_sample = features.loc[(features.index >= start) & (features.index <= end)]
    eligible = in_sample.dropna(subset=["threshold"])
    total_decisions = sum(start <= int(timestamp) <= end and int(timestamp) % DECISION_SECONDS == 0
                          for timestamp in price.index)
    trades: list[dict[str, Any]] = []
    last_exit = -1
    census: dict[str, Any] = {
        "price_decisions": total_decisions, "valid_book_decisions": len(in_sample),
        "missing_or_stale_book": total_decisions - len(in_sample),
        "eligible_after_warmup": len(eligible), "non_signal": 0, "overlap_rejected": 0,
        "missing_entry_or_exit": 0, "unresolved_at_fold_end": 0,
        "mean_book_age_seconds": float(in_sample["book_age_seconds"].mean()) if len(in_sample) else None,
        "max_book_age_seconds": int(in_sample["book_age_seconds"].max()) if len(in_sample) else None,
    }
    for timestamp, row in eligible.iterrows():
        timestamp = int(timestamp)
        imbalance, threshold = float(row["imbalance"]), float(row["threshold"])
        if abs(imbalance) < threshold or imbalance == 0:
            census["non_signal"] += 1
            continue
        exit_timestamp = timestamp + EXIT_SECONDS
        exit_bar = exit_timestamp - BAR_SECONDS
        if timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        if timestamp not in price.index or exit_bar not in price.index:
            census["missing_entry_or_exit"] += 1
            continue
        fold = None
        if fold_boundaries is not None:
            fold_index = max(index for index in range(FOLDS) if timestamp >= fold_boundaries[index])
            if exit_timestamp >= fold_boundaries[fold_index + 1]:
                census["unresolved_at_fold_end"] += 1
                continue
            fold = fold_index + 1
        direction = 1.0 if imbalance > 0 else -1.0
        entry = float(price.loc[timestamp, "open"])
        exit_price = float(price.loc[exit_bar, "close"])
        rates = funding.loc[(funding.index > timestamp) & (funding.index <= exit_timestamp)]
        funding_return = -direction * float(rates.sum())
        trade = {
            "symbol": symbol, "side": "LONG" if direction > 0 else "SHORT", "fold": fold,
            "decision_timestamp": timestamp, "snapshot_timestamp": int(row["snapshot_timestamp"]),
            "book_age_seconds": int(row["book_age_seconds"]), "entry_timestamp": timestamp,
            "exit_timestamp": exit_timestamp, "imbalance": imbalance, "threshold": threshold,
            "extremeness_ratio": abs(imbalance) / threshold if threshold else None,
            "entry_price": entry, "exit_price": exit_price,
            "price_pnl_return": direction * (exit_price - entry) / entry,
            "funding_return": funding_return,
        }
        trade["gross_return"] = trade["price_pnl_return"] + funding_return
        trades.append(trade)
        last_exit = exit_timestamp
    return trades, census


def evaluate_sample(price_dir: Path, book_dir: Path, funding_dir: Path, start: int, end: int,
                    primary: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mechanics = _mechanics()
    prices = {symbol: mechanics.load_price(price_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    books = {symbol: load_book(book_dir / f"{symbol}.csv.gz") for symbol in SYMBOLS}
    funding = {symbol: mechanics.load_funding(funding_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    eligible_union = sorted({int(timestamp) for symbol in SYMBOLS
                             for timestamp in causal_features(prices[symbol], books[symbol]).dropna().index
                             if start <= int(timestamp) <= end})
    boundaries = None
    if primary:
        boundaries = [eligible_union[index * len(eligible_union) // FOLDS] for index in range(FOLDS)]
        boundaries.append(eligible_union[-1] + DECISION_SECONDS)
    trades: list[dict[str, Any]] = []
    census = {}
    for symbol in SYMBOLS:
        selected, counts = collect_trades(symbol, prices[symbol], books[symbol], funding[symbol],
                                          start, end, boundaries)
        trades.extend(selected)
        census[symbol] = counts
    trades.sort(key=lambda trade: (trade["entry_timestamp"], trade["symbol"]))
    return trades, {"census": census, "fold_boundaries": boundaries}


def build_report(price_dir: Path, book_dir: Path, funding_dir: Path) -> dict[str, Any]:
    mechanics = _mechanics()
    primary, primary_info = evaluate_sample(price_dir, book_dir, funding_dir,
                                            PRIMARY_START, PRIMARY_END, True)
    reverse, reverse_info = evaluate_sample(price_dir, book_dir, funding_dir,
                                            REVERSE_START, REVERSE_END, False)
    overall = mechanics.metrics(primary)
    ci = mechanics.day_cluster_ci(primary)
    by_fold = {f"F{fold}": mechanics.metrics([t for t in primary if t["fold"] == fold])
               for fold in range(1, FOLDS + 1)}
    by_side = {side: mechanics.metrics([t for t in primary if t["side"] == side])
               for side in ("LONG", "SHORT")}
    by_symbol = {symbol: mechanics.metrics([t for t in primary if t["symbol"] == symbol])
                 for symbol in SYMBOLS}
    costs = {f"{cost:.3f}": mechanics.metrics(primary, cost) for cost in COSTS}
    reverse_metrics = mechanics.metrics(reverse)
    positive = {symbol: sum(max(0.0, t["gross_return"] - PRIMARY_COST) for t in primary
                            if t["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    adequate_folds = [item for item in by_fold.values() if item["n"] >= 120]
    gate = {
        "adequately_sampled_folds": len(adequate_folds),
        "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate_folds),
        "both_sides_positive_and_sampled": all(item["n"] >= 150 and item["expectancy"] > 0
                                                for item in by_side.values()),
        "positive_sampled_symbols": sum(item["n"] >= 80 and item["expectancy"] > 0
                                        for item in by_symbol.values()),
        "max_positive_pnl_symbol_concentration": concentration,
    }
    keep = (overall["n"] >= 600 and overall["expectancy"] is not None and overall["expectancy"] > 0
            and overall["profit_factor"] is not None and overall["profit_factor"] > 1
            and ci[0] is not None and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["both_sides_positive_and_sampled"] and gate["positive_sampled_symbols"] >= 4
            and concentration is not None and concentration <= 0.30
            and reverse_metrics["n"] >= 250 and reverse_metrics["expectancy"] > 0
            and reverse_metrics["profit_factor"] is not None and reverse_metrics["profit_factor"] > 1
            and costs["0.005"]["expectancy"] is not None and costs["0.005"]["expectancy"] > 0)
    gate["verdict"] = "KEEP_FOR_PATH_DEPENDENT_CONFIRMATION" if keep else "REJECT"
    return {
        "candidate": "C-18", "protocol": "edge-candidate-register-v17",
        "primary": {"overall_funding_inclusive": overall,
                    "overall_price_only": mechanics.metrics(primary, field="price_pnl_return"),
                    "mean_funding_return": float(np.mean([t["funding_return"] for t in primary]))
                    if primary else None,
                    "day_cluster_bootstrap_95_ci": ci, "by_fold": by_fold, "by_side": by_side,
                    "by_symbol": by_symbol, "cost_sensitivity": costs, **primary_info},
        "reverse_time": {"overall_funding_inclusive": reverse_metrics, **reverse_info},
        "gate": gate,
        "limitations": ["Fixed 24-hour exits isolate signal information and are not production exits."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--book-dir", default="data/research/bookdepth/normalized")
    parser.add_argument("--funding-dir", default="data/research/c16/funding")
    parser.add_argument("--output", default="docs/reports/edge_candidate_c18_holdout.json")
    args = parser.parse_args()
    report = build_report(Path(args.price_dir), Path(args.book_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
