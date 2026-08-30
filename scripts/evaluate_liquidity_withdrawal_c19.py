#!/usr/bin/env python3
"""Evaluate preregistered C-19 liquidity-withdrawal differential."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _base():
    path = Path(__file__).with_name("evaluate_bookdepth_imbalance_c18.py")
    spec = importlib.util.spec_from_file_location("c18_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def causal_features(price: pd.DataFrame, book: pd.DataFrame) -> pd.DataFrame:
    base = _base()
    decisions = np.asarray(sorted(int(timestamp) for timestamp in price.index
                                  if int(timestamp) % base.DECISION_SECONDS == 0), dtype=np.int64)
    book_timestamps = book.index.to_numpy(dtype=np.int64)
    current_positions = np.searchsorted(book_timestamps, decisions, side="left") - 1
    lag_anchors = decisions - base.DECISION_SECONDS
    lag_positions = np.searchsorted(book_timestamps, lag_anchors, side="left") - 1
    rows = []
    for decision, lag_anchor, current_position, lag_position in zip(
            decisions, lag_anchors, current_positions, lag_positions):
        if current_position < 0 or lag_position < 0:
            continue
        current_timestamp = int(book_timestamps[current_position])
        lag_timestamp = int(book_timestamps[lag_position])
        current_age = int(decision) - current_timestamp
        lag_age = int(lag_anchor) - lag_timestamp
        if not (0 < current_age <= base.MAX_BOOK_AGE and 0 < lag_age <= base.MAX_BOOK_AGE):
            continue
        current = book.iloc[current_position]
        lagged = book.iloc[lag_position]
        values = np.asarray([current["notional_m1"], current["notional_p1"],
                             lagged["notional_m1"], lagged["notional_p1"]], dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            continue
        bid_change = float(np.log(values[0] / values[2]))
        ask_change = float(np.log(values[1] / values[3]))
        rows.append({"decision_timestamp": int(decision),
                     "snapshot_timestamp": current_timestamp,
                     "lag_snapshot_timestamp": lag_timestamp,
                     "book_age_seconds": max(current_age, lag_age),
                     "bid_change": bid_change, "ask_change": ask_change,
                     "imbalance": bid_change - ask_change})
    columns = ["snapshot_timestamp", "lag_snapshot_timestamp", "book_age_seconds",
               "bid_change", "ask_change", "imbalance", "threshold"]
    if not rows:
        return pd.DataFrame(columns=columns).rename_axis("decision_timestamp")
    frame = pd.DataFrame(rows).set_index("decision_timestamp")
    frame["threshold"] = frame["imbalance"].abs().shift(1).rolling(
        base.WARMUP, min_periods=base.WARMUP
    ).quantile(0.90)
    return frame


def build_report(price_dir: Path, book_dir: Path, funding_dir: Path):
    base = _base()
    base.causal_features = causal_features
    report = base.build_report(price_dir, book_dir, funding_dir)
    report["candidate"] = "C-19"
    report["protocol"] = "edge-candidate-register-v18"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--book-dir", default="data/research/bookdepth/normalized")
    parser.add_argument("--funding-dir", default="data/research/c16/funding")
    parser.add_argument("--output", default="docs/reports/edge_candidate_c19_holdout.json")
    args = parser.parse_args()
    report = build_report(Path(args.price_dir), Path(args.book_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
