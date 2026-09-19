#!/usr/bin/env python3
"""Evaluate the frozen Lead-B 2026 economic holdout without parameter search."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


DAY_MS = 86_400_000
DECISION_OFFSETS_MS = (0, 43_200_000)
MAX_DELAY_MS = 10_000


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_archive(path):
    return pd.read_csv(
        path,
        compression="zip",
        usecols=["price", "quantity", "transact_time", "is_buyer_maker"],
        dtype={"price": float, "quantity": float, "transact_time": "int64", "is_buyer_maker": bool},
    ).sort_values("transact_time", kind="stable")


def first_trade(frame, target_ms, max_delay_ms=MAX_DELAY_MS):
    matches = frame[
        (frame["transact_time"] >= target_ms)
        & (frame["transact_time"] < target_ms + max_delay_ms)
    ]
    if matches.empty:
        return None
    row = matches.iloc[0]
    return {"timestamp_ms": int(row["transact_time"]), "price": float(row["price"])}


def build_trade(frame, boundary_ms, funding):
    observation = frame[
        (frame["transact_time"] >= boundary_ms)
        & (frame["transact_time"] < boundary_ms + 10_000)
    ].copy()
    if observation.empty:
        return None, "MISSING_OBSERVATION"
    observation["notional"] = observation["price"] * observation["quantity"]
    buyer = float(observation.loc[~observation["is_buyer_maker"], "notional"].sum())
    seller = float(observation.loc[observation["is_buyer_maker"], "notional"].sum())
    total = buyer + seller
    imbalance = (buyer - seller) / total if total else 0.0
    if imbalance == 0:
        return None, "ZERO_IMBALANCE"

    entry = first_trade(frame, boundary_ms + 10_000)
    exit_trade = first_trade(frame, boundary_ms + 12 * 3_600_000)
    if entry is None:
        return None, "MISSING_ENTRY"
    if exit_trade is None:
        return None, "MISSING_EXIT"
    if exit_trade["timestamp_ms"] <= entry["timestamp_ms"]:
        return None, "NON_POSITIVE_HOLD"

    direction = 1 if imbalance > 0 else -1
    applicable = funding[
        (funding["timestamp"] * 1000 > entry["timestamp_ms"])
        & (funding["timestamp"] * 1000 <= exit_trade["timestamp_ms"])
    ]
    gross = direction * (exit_trade["price"] / entry["price"] - 1.0)
    funding_return = -direction * float(applicable["funding_rate"].sum())
    return {
        "boundary_ms": int(boundary_ms),
        "clock_phase": "00:00" if boundary_ms % DAY_MS == 0 else "12:00",
        "direction": "LONG" if direction == 1 else "SHORT",
        "imbalance": float(imbalance),
        "entry_timestamp_ms": entry["timestamp_ms"],
        "entry_price": entry["price"],
        "exit_timestamp_ms": exit_trade["timestamp_ms"],
        "exit_price": exit_trade["price"],
        "gross_return": float(gross),
        "funding_return": float(funding_return),
    }, None


def profit_factor(values):
    values = np.asarray(values, dtype=float)
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    return positive / negative if negative else float("inf")


def max_drawdown(values):
    equity = np.cumprod(1.0 + np.asarray(values, dtype=float))
    peaks = np.maximum.accumulate(np.concatenate([[1.0], equity]))[1:]
    return float(np.min(equity / peaks - 1.0)) if len(equity) else 0.0


def bootstrap_day_mean(frame, column, seed=387, draws=5000):
    days = np.array(sorted(frame["day"].unique()))
    grouped = {day: frame.loc[frame["day"] == day, column].to_numpy(float) for day in days}
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(draws):
        sample = rng.choice(days, len(days), replace=True)
        estimates.append(float(np.concatenate([grouped[day] for day in sample]).mean()))
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def metrics(frame, column):
    values = frame[column].to_numpy(float)
    wins = values[values > 0]
    losses = values[values < 0]
    return {
        "n": int(len(values)),
        "expectancy": float(values.mean()),
        "profit_factor": profit_factor(values),
        "win_rate": float((values > 0).mean()),
        "average_win": float(wins.mean()) if len(wins) else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "payoff_ratio": float(wins.mean() / -losses.mean()) if len(wins) and len(losses) else 0.0,
    }


def evaluate(root):
    root = Path(root)
    frozen = json.loads((root / "data/research/lead_b/economic_holdout_manifest.json").read_text())
    source_path = root / "data/research/btc_aggtrades/manifest.json"
    funding_path = root / "data/research/c16/funding/BTCUSDT.csv"
    if sha256(source_path) != frozen["raw_manifest_sha256"]:
        raise ValueError("raw source manifest differs from preregistration")
    if sha256(funding_path) != frozen["funding_sha256"]:
        raise ValueError("funding source differs from preregistration")

    source = json.loads(source_path.read_text())
    funding = pd.read_csv(funding_path)
    dates = sorted(
        day for day in source["days"]
        if frozen["holdout_start"] <= day <= frozen["holdout_end"]
    )
    raw = root / "data/research/btc_aggtrades/raw"
    records = []
    exclusions = {}
    hash_failures = []
    current_day = None
    current_frame = None
    next_day = None
    next_frame = None

    for day in dates:
        day_start_ms = int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)
        tomorrow = (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        if current_day != day:
            current_path = raw / f"BTCUSDT-aggTrades-{day}.zip"
            if not current_path.exists() or sha256(current_path) != source["days"][day]["zip_sha256"]:
                hash_failures.append(day)
                continue
            current_frame = read_archive(current_path)
            current_day = day
        next_path = raw / f"BTCUSDT-aggTrades-{tomorrow}.zip"
        if tomorrow not in source["days"] or not next_path.exists() or sha256(next_path) != source["days"][tomorrow]["zip_sha256"]:
            hash_failures.append(tomorrow)
            continue
        if next_day != tomorrow:
            next_frame = read_archive(next_path)
            next_day = tomorrow
        combined = pd.concat([current_frame, next_frame], ignore_index=True)

        for offset in DECISION_OFFSETS_MS:
            record, reason = build_trade(combined, day_start_ms + offset, funding)
            if reason:
                exclusions[reason] = exclusions.get(reason, 0) + 1
                continue
            record["day"] = day
            record["fold"] = "2026_JAN_APR" if day <= "2026-04-30" else "2026_MAY_AUG"
            record["pre_cost_return"] = record["gross_return"] + record["funding_return"]
            record["primary_net_return"] = (
                record["pre_cost_return"] - frozen["execution_cost_primary"]
            )
            record["stress_net_return"] = (
                record["pre_cost_return"] - frozen["execution_cost_stress"]
            )
            records.append(record)

        # Tomorrow becomes the next iteration's current day. Reuse the verified frame instead of
        # decompressing every several-hundred-thousand-row archive twice.
        current_day = tomorrow
        current_frame = next_frame

    frame = pd.DataFrame(records).sort_values("boundary_ms", kind="stable")
    eligible_days = int(frame["day"].nunique()) if not frame.empty else 0
    integrity_pass = (
        not hash_failures
        and eligible_days >= frozen["minimum_eligible_days"]
        and len(frame) >= frozen["minimum_eligible_trades"]
    )
    if not integrity_pass:
        return {
            "candidate": frozen["candidate"],
            "integrity": "FAIL",
            "eligible_days": eligible_days,
            "eligible_trades": int(len(frame)),
            "hash_failures": sorted(set(hash_failures)),
            "exclusions": exclusions,
            "verdict": "INVALID_DATA",
        }

    primary = metrics(frame, "primary_net_return")
    stress = metrics(frame, "stress_net_return")
    pre_cost = metrics(frame, "pre_cost_return")
    gross = metrics(frame, "gross_return")
    primary["day_block_ci"] = bootstrap_day_mean(frame, "primary_net_return")
    splits = {
        "fold": {
            key: metrics(group, "primary_net_return")
            for key, group in frame.groupby("fold", sort=True)
        },
        "clock_phase": {
            key: metrics(group, "primary_net_return")
            for key, group in frame.groupby("clock_phase", sort=True)
        },
        "direction": {
            key: metrics(group, "primary_net_return")
            for key, group in frame.groupby("direction", sort=True)
        },
    }
    gross_profit_by_side = {
        key: float(group.loc[group["gross_return"] > 0, "gross_return"].sum())
        for key, group in frame.groupby("direction", sort=True)
    }
    total_gross_profit = sum(gross_profit_by_side.values())
    side_concentration = (
        max(gross_profit_by_side.values()) / total_gross_profit if total_gross_profit else 1.0
    )
    drawdown = max_drawdown(frame["primary_net_return"])
    gates = {
        "positive_primary_expectancy": primary["expectancy"] > 0,
        "primary_ci_above_zero": primary["day_block_ci"][0] > 0,
        "primary_pf_above_1_10": primary["profit_factor"] > 1.10,
        "both_folds_positive": all(value["expectancy"] > 0 for value in splits["fold"].values()),
        "both_clock_phases_positive": all(
            value["expectancy"] > 0 for value in splits["clock_phase"].values()
        ),
        "side_concentration_at_most_0_80": side_concentration <= 0.80,
        "stress_expectancy_non_negative": stress["expectancy"] >= 0,
        "drawdown_at_least_minus_0_20": drawdown >= -0.20,
    }
    return {
        "candidate": frozen["candidate"],
        "integrity": "PASS",
        "eligible_days": eligible_days,
        "eligible_trades": int(len(frame)),
        "hash_failures": [],
        "exclusions": exclusions,
        "gross": gross,
        "mean_funding_return": float(frame["funding_return"].mean()),
        "pre_cost": pre_cost,
        "primary": primary,
        "stress": stress,
        "splits": splits,
        "side_gross_profit_concentration": float(side_concentration),
        "primary_max_drawdown": drawdown,
        "gates": gates,
        "verdict": (
            "KEEP_FOR_PROSPECTIVE_CONFIRMATION"
            if all(gates.values()) else "REJECT_ECONOMIC_EDGE"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.root)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
