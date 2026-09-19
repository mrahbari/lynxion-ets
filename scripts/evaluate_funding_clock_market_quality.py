#!/usr/bin/env python3
"""Evaluate the frozen funding-settlement market-quality diagnostic."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT")
PRIMARY = ("log_quote_volume", "log_trade_count", "absolute_log_return")


def flow_window(frame, start):
    timestamps = (start - 2700, start - 1800, start - 900)
    if not all(timestamp in frame.index for timestamp in timestamps):
        return None
    rows = frame.loc[list(timestamps)]
    quote = float(rows["quote_volume"].sum())
    count = float(rows["count"].sum())
    if quote <= 0 or count <= 0 or (rows[["open", "close"]] <= 0).any().any():
        return None
    imbalance = 2.0 * float(rows["taker_buy_quote_volume"].sum()) / quote - 1.0
    return {
        "log_quote_volume": math.log(quote),
        "log_trade_count": math.log(count),
        "absolute_log_return": float(np.abs(np.log(rows["close"] / rows["open"])).sum()),
        "absolute_taker_imbalance": abs(imbalance),
    }


def depth_before(frame, boundary, tolerance=300):
    position = int(frame.index.searchsorted(boundary, side="left")) - 1
    if position < 0:
        return None
    timestamp = int(frame.index[position])
    if timestamp < boundary - tolerance:
        return None
    row = frame.iloc[position]
    minus = float(row["notional_m1"])
    plus = float(row["notional_p1"])
    total = minus + plus
    if total <= 0:
        return None
    return {"depth_1pct": total, "depth_imbalance": (plus - minus) / total}


def paired_record(flow, depth, settlement, control):
    settlement_pre = flow_window(flow, settlement)
    settlement_post = flow_window(flow, settlement + 2700)
    control_pre = flow_window(flow, control)
    control_post = flow_window(flow, control + 2700)
    if any(value is None for value in (settlement_pre, settlement_post, control_pre, control_post)):
        return None, "MISSING_PRIMARY_WINDOW"
    result = {}
    for metric in (*PRIMARY, "absolute_taker_imbalance"):
        result[metric] = (
            settlement_post[metric] - settlement_pre[metric]
            - (control_post[metric] - control_pre[metric])
        )
        result[f"settlement_pre_{metric}"] = settlement_pre[metric]

    depth_points = [
        depth_before(depth, settlement),
        depth_before(depth, settlement + 2700),
        depth_before(depth, control),
        depth_before(depth, control + 2700),
    ]
    if any(value is None for value in depth_points):
        result["depth_available"] = False
    else:
        result["depth_available"] = True
        for metric in ("depth_1pct", "depth_imbalance"):
            result[metric] = (
                depth_points[1][metric] - depth_points[0][metric]
                - (depth_points[3][metric] - depth_points[2][metric])
            )
            result[f"settlement_pre_{metric}"] = depth_points[0][metric]
    return result, None


def bootstrap_cluster_mean(frame, column, seed=392, draws=5000):
    grouped = frame.groupby("settlement")[column].agg(["sum", "count"]).sort_index()
    sums = grouped["sum"].to_numpy(float)
    counts = grouped["count"].to_numpy(float)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(draws):
        sample = rng.integers(0, len(grouped), len(grouped))
        values.append(float(sums[sample].sum() / counts[sample].sum()))
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]


def fold_for(timestamp):
    return str(pd.to_datetime(timestamp, unit="s", utc=True).year)


def evaluate(root):
    root = Path(root)
    records = []
    exclusions = {}
    total_candidates = 0
    for symbol in SYMBOLS:
        funding = pd.read_csv(root / f"data/research/c16/funding/{symbol}.csv")
        funding = funding[
            (funding["timestamp"] >= 1672531200) & (funding["timestamp"] <= 1788019200)
        ].sort_values("timestamp")
        flow = pd.read_csv(root / f"data/research/taker_flow/normalized/{symbol}.csv.gz")
        flow = flow.set_index("timestamp").sort_index()
        depth = pd.read_csv(root / f"data/research/bookdepth/normalized/{symbol}.csv.gz")
        depth = depth.set_index("timestamp").sort_index()
        settlements = funding["timestamp"].astype(int).tolist()
        settlement_set = np.asarray(settlements)
        for index in range(1, len(settlements) - 1):
            settlement = settlements[index]
            next_settlement = settlements[index + 1]
            control = settlement + (next_settlement - settlement) // 2
            total_candidates += 1
            if np.min(np.abs(settlement_set - control)) <= 2700:
                exclusions["CONTROL_NEAR_SETTLEMENT"] = exclusions.get("CONTROL_NEAR_SETTLEMENT", 0) + 1
                continue
            result, reason = paired_record(flow, depth, settlement, control)
            if reason:
                exclusions[reason] = exclusions.get(reason, 0) + 1
                continue
            result.update({"symbol": symbol, "settlement": settlement, "fold": fold_for(settlement)})
            records.append(result)

    frame = pd.DataFrame(records)
    clusters = int(frame["settlement"].nunique()) if not frame.empty else 0
    completeness = len(frame) / total_candidates if total_candidates else 0.0
    folds = sorted(frame["fold"].unique()) if not frame.empty else []
    fold_breadth = all(
        set(frame.loc[frame["fold"] == fold, "symbol"]) == set(SYMBOLS) for fold in folds
    )
    integrity = clusters >= 2000 and completeness >= 0.90 and folds == ["2023", "2024", "2025", "2026"] and fold_breadth
    if not integrity:
        return {
            "candidate": "FUNDING_SETTLEMENT_MARKET_QUALITY_CLOCK",
            "integrity": "FAIL",
            "total_candidates": total_candidates,
            "eligible_records": int(len(frame)),
            "independent_settlement_clusters": clusters,
            "primary_completeness": completeness,
            "exclusions": exclusions,
            "verdict": "INVALID_DATA",
        }

    metrics = {}
    for metric in (*PRIMARY, "absolute_taker_imbalance"):
        mean = float(frame[metric].mean())
        fold_means = frame.groupby("fold")[metric].mean().astype(float).to_dict()
        symbol_means = frame.groupby("symbol")[metric].mean().astype(float).to_dict()
        metrics[metric] = {
            "paired_mean": mean,
            "cluster_ci": bootstrap_cluster_mean(frame, metric),
            "same_sign_folds": int(sum(np.sign(value) == np.sign(mean) for value in fold_means.values())),
            "same_sign_symbols": int(sum(np.sign(value) == np.sign(mean) for value in symbol_means.values())),
            "fold_means": fold_means,
            "symbol_means": symbol_means,
            "relative_to_settlement_pre": float(mean / frame[f"settlement_pre_{metric}"].mean()),
        }

    depth_frame = frame[frame["depth_available"]].copy()
    for metric in ("depth_1pct", "depth_imbalance"):
        mean = float(depth_frame[metric].mean())
        metrics[metric] = {
            "n": int(len(depth_frame)),
            "paired_mean": mean,
            "cluster_ci": bootstrap_cluster_mean(depth_frame, metric),
            "relative_to_settlement_pre": float(mean / depth_frame[f"settlement_pre_{metric}"].mean()),
        }

    primary_pass = [
        metric for metric in PRIMARY
        if not (metrics[metric]["cluster_ci"][0] <= 0 <= metrics[metric]["cluster_ci"][1])
        and metrics[metric]["same_sign_folds"] >= 3
        and metrics[metric]["same_sign_symbols"] >= 5
    ]
    adverse = {
        "absolute_log_return": metrics["absolute_log_return"]["relative_to_settlement_pre"] >= 0.10
        and metrics["absolute_log_return"]["cluster_ci"][0] > 0,
        "absolute_taker_imbalance": metrics["absolute_taker_imbalance"]["relative_to_settlement_pre"] >= 0.10
        and metrics["absolute_taker_imbalance"]["cluster_ci"][0] > 0,
        "depth_1pct": metrics["depth_1pct"]["relative_to_settlement_pre"] <= -0.10
        and metrics["depth_1pct"]["cluster_ci"][1] < 0,
    }
    passes = len(primary_pass) >= 2 and any(adverse.values())
    return {
        "candidate": "FUNDING_SETTLEMENT_MARKET_QUALITY_CLOCK",
        "integrity": "PASS",
        "total_candidates": total_candidates,
        "eligible_records": int(len(frame)),
        "independent_settlement_clusters": clusters,
        "primary_completeness": completeness,
        "exclusions": exclusions,
        "metrics": metrics,
        "primary_metrics_passing": primary_pass,
        "adverse_proxy_gates": adverse,
        "spread_available": False,
        "execution_edge_claimed": False,
        "verdict": "INFORMATION_VALUE_CONFIRMED" if passes else "LOW_INFORMATION_VALUE — DO_NOT_BUILD",
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
