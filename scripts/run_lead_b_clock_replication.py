#!/usr/bin/env python3
"""Run the frozen Lead-B quarter-hour replication on retained raw aggTrades."""

import argparse
import hashlib
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


WINDOWS = {"opening": 0, "control_5m": 300_000, "control_10m": 600_000}
HORIZONS = (4, 8, 12)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_archive(path: Path):
    frame = pd.read_csv(
        path,
        compression="zip",
        usecols=["price", "quantity", "transact_time", "is_buyer_maker"],
        dtype={"price": float, "quantity": float, "transact_time": "int64", "is_buyer_maker": bool},
    )
    frame["boundary_ms"] = (frame["transact_time"] // 900_000) * 900_000
    offset = frame["transact_time"] - frame["boundary_ms"]
    frame["window"] = None
    for name, start in WINDOWS.items():
        frame.loc[(offset >= start) & (offset < start + 10_000), "window"] = name
    frame = frame.dropna(subset=["window"])
    frame["notional"] = frame["price"] * frame["quantity"]
    frame["buyer_notional"] = np.where(~frame["is_buyer_maker"], frame["notional"], 0.0)
    frame["seller_notional"] = np.where(frame["is_buyer_maker"], frame["notional"], 0.0)
    previous = frame.groupby(["boundary_ms", "window"], sort=False)["price"].shift()
    frame["abs_log_step"] = np.abs(np.log(frame["price"] / previous)).fillna(0.0)
    buckets = {}
    for (boundary_ms, window), group in frame.groupby(["boundary_ms", "window"], sort=False):
        buckets[(int(boundary_ms) // 1000, window)] = {
            "trade_count": int(len(group)),
            "quote_volume": float(group["notional"].sum()),
            "buyer_quote_volume": float(group["buyer_notional"].sum()),
            "seller_quote_volume": float(group["seller_notional"].sum()),
            "first_price": float(group["price"].iloc[0]),
            "last_price": float(group["price"].iloc[-1]),
            "abs_log_path": float(group["abs_log_step"].sum()),
        }
    return buckets


def finalize_bucket(bucket):
    total = bucket["buyer_quote_volume"] + bucket["seller_quote_volume"]
    first = bucket["first_price"]
    last = bucket["last_price"]
    return {
        "trade_count": bucket["trade_count"],
        "quote_volume": bucket["quote_volume"],
        "signed_imbalance": (
            (bucket["buyer_quote_volume"] - bucket["seller_quote_volume"]) / total
            if total else 0.0
        ),
        "price_change": math.log(last / first) if first and last and first > 0 and last > 0 else 0.0,
        "abs_log_path": bucket["abs_log_path"],
    }


def bootstrap_mean(values, days, seed=381, draws=2000):
    unique_days = np.array(sorted(set(days)))
    grouped = {day: np.asarray([v for v, d in zip(values, days) if d == day]) for day in unique_days}
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(draws):
        sample = rng.choice(unique_days, len(unique_days), replace=True)
        estimates.append(np.concatenate([grouped[day] for day in sample]).mean())
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def coefficient(frame, outcome):
    clean = frame[["opening_signed_imbalance", "prior_15m_return", "log_volume", outcome]].dropna()
    if len(clean) < 4:
        return float("nan")
    x = clean[["opening_signed_imbalance", "prior_15m_return", "log_volume"]].to_numpy(float)
    x = np.column_stack([np.ones(len(x)), x])
    return float(np.linalg.lstsq(x, clean[outcome].to_numpy(float), rcond=None)[0][1])


def bootstrap_coefficient(frame, outcome, seed=381, draws=1000):
    days = np.array(sorted(frame["day"].unique()))
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(draws):
        sample = rng.choice(days, len(days), replace=True)
        sampled = pd.concat([frame[frame["day"] == day] for day in sample], ignore_index=True)
        estimates.append(coefficient(sampled, outcome))
    estimates = np.asarray([value for value in estimates if np.isfinite(value)])
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def run(root: Path):
    base = root / "data/research/btc_aggtrades"
    frozen = json.loads((root / "data/research/lead_b/replication_manifest.json").read_text())
    source_manifest = json.loads((base / "manifest.json").read_text())
    rows = []
    integrity = []
    for day in frozen["selected_dates"]:
        path = base / "raw" / f"BTCUSDT-aggTrades-{day}.zip"
        expected_hash = source_manifest["days"][day]["zip_sha256"]
        hash_ok = sha256(path) == expected_hash
        buckets = aggregate_archive(path) if hash_ok else {}
        complete_events = 0
        for boundary in sorted({key[0] for key in buckets}):
            if all((boundary, window) in buckets for window in WINDOWS):
                record = {"boundary": boundary, "day": day}
                for window in WINDOWS:
                    for name, value in finalize_bucket(buckets[(boundary, window)]).items():
                        record[f"{window}_{name}"] = value
                rows.append(record)
                complete_events += 1
        integrity.append({"day": day, "hash_ok": hash_ok, "complete_events": complete_events})

    frame = pd.DataFrame(rows)
    price = pd.read_csv(base.parent / "taker_flow/normalized/BTCUSDT.csv.gz")
    price = price.set_index("timestamp").sort_index()
    frame["prior_15m_return"] = frame["boundary"].map(
        lambda t: (
            math.log(price.loc[t - 900, "close"] / price.loc[t - 900, "open"])
            if t - 900 in price.index else np.nan
        )
    )
    frame["log_volume"] = np.log1p(frame["opening_quote_volume"])
    for horizon in HORIZONS:
        frame[f"return_{horizon}h"] = frame["boundary"].map(
            lambda t, h=horizon: (
                math.log(price.loc[t + h * 3600, "close"] / price.loc[t, "open"])
                if t in price.index and t + h * 3600 in price.index else np.nan
            )
        )

    activity = {}
    for metric in ("trade_count", "quote_volume", "abs_log_path"):
        control = (frame[f"control_5m_{metric}"] + frame[f"control_10m_{metric}"]) / 2
        diff = frame[f"opening_{metric}"] - control
        fold_means = {}
        for fold, dates in frozen["folds"].items():
            fold_means[fold] = float(diff[frame["day"].isin(dates)].mean())
        activity[metric] = {
            "mean_difference": float(diff.mean()),
            "day_block_ci": bootstrap_mean(diff.to_numpy(), frame["day"].to_numpy()),
            "positive_folds": int(sum(value > 0 for value in fold_means.values())),
            "fold_means": fold_means,
        }

    predictive = {}
    for horizon in HORIZONS:
        outcome = f"return_{horizon}h"
        fold_values = {
            fold: coefficient(frame[frame["day"].isin(dates)], outcome)
            for fold, dates in frozen["folds"].items()
        }
        full = coefficient(frame, outcome)
        predictive[f"{horizon}h"] = {
            "imbalance_coefficient": full,
            "day_block_ci": bootstrap_coefficient(frame.dropna(subset=[outcome]), outcome),
            "same_sign_folds": int(sum(np.sign(value) == np.sign(full) for value in fold_values.values())),
            "fold_coefficients": fold_values,
        }

    passing_days = sum(item["hash_ok"] and item["complete_events"] == 96 for item in integrity)
    activity_pass = sum(
        result["mean_difference"] > 0 and result["positive_folds"] >= 3
        for result in activity.values()
    ) >= 2
    predictive_pass = any(
        result["same_sign_folds"] >= 3
        and not (result["day_block_ci"][0] <= 0 <= result["day_block_ci"][1])
        for result in predictive.values()
    )
    passes = passing_days >= frozen["minimum_passing_days"] and activity_pass and predictive_pass
    return {
        "lead": frozen["candidate"],
        "integrity": {"passing_days": passing_days, "required_days": frozen["minimum_passing_days"], "days": integrity},
        "nominal_events": len(frame),
        "independent_day_clusters": int(frame["day"].nunique()),
        "activity": activity,
        "predictive": predictive,
        "verdict": "PREREGISTER_ECONOMIC_TEST_NEXT" if passes else "REJECT_TRANSFERABILITY",
        "economic_edge_claimed": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
