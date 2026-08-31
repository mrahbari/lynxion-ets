#!/usr/bin/env python3
"""Evaluate preregistered C-20 symmetric premium-basis convergence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd


def _base():
    path = Path(__file__).with_name("evaluate_bookdepth_imbalance_c18.py")
    spec = importlib.util.spec_from_file_location("c18_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_premium(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=["timestamp", "close"])
    frame["timestamp"] = pd.to_numeric(frame["timestamp"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    return frame.dropna().sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")


def causal_features(price: pd.DataFrame, premium: pd.DataFrame) -> pd.DataFrame:
    base = _base()
    premium_index = set(premium.index.astype(int))
    rows = []
    for timestamp in price.index:
        decision = int(timestamp)
        source_timestamp = decision - base.BAR_SECONDS
        if decision % base.DECISION_SECONDS or source_timestamp not in premium_index:
            continue
        premium_close = float(premium.loc[source_timestamp, "close"])
        rows.append({"decision_timestamp": decision, "snapshot_timestamp": source_timestamp,
                     "book_age_seconds": base.BAR_SECONDS, "premium_close": premium_close,
                     "imbalance": -premium_close})
    columns = ["snapshot_timestamp", "book_age_seconds", "premium_close", "imbalance", "threshold"]
    if not rows:
        return pd.DataFrame(columns=columns).rename_axis("decision_timestamp")
    frame = pd.DataFrame(rows).set_index("decision_timestamp")
    frame["threshold"] = frame["premium_close"].abs().shift(1).rolling(
        base.WARMUP, min_periods=base.WARMUP
    ).quantile(0.95)
    return frame


def build_report(price_dir: Path, premium_dir: Path, funding_dir: Path):
    base = _base()
    base.load_book = load_premium
    base.causal_features = causal_features
    report = base.build_report(price_dir, premium_dir, funding_dir)
    report["candidate"] = "C-20"
    report["protocol"] = "edge-candidate-register-v19"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--price-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--premium-dir", default="data/research/premium_index/normalized")
    parser.add_argument("--funding-dir", default="data/research/c16/funding")
    parser.add_argument("--output", default="docs/reports/edge_candidate_c20_holdout.json")
    args = parser.parse_args()
    report = build_report(Path(args.price_dir), Path(args.premium_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
