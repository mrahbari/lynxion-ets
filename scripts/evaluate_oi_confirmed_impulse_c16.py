#!/usr/bin/env python3
"""Evaluate preregistered C-16 OI-confirmed price impulse."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
DECISION_SECONDS = 4 * 3600
OI_LAG_SECONDS = 300
PRICE_LAG_SECONDS = 900
EXIT_SECONDS = 24 * 3600
WARMUP = 180
FOLDS = 4
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)


def load_price(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=["timestamp", "open", "close"])
    frame = frame.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
    frame[["open", "close"]] = frame[["open", "close"]].apply(pd.to_numeric, errors="coerce")
    return frame.dropna()


def load_oi(path: Path) -> pd.Series:
    frame = pd.read_csv(path, usecols=["create_time", "sum_open_interest"])
    timestamps = pd.to_datetime(frame["create_time"], utc=True).astype("int64") // 10**9
    values = pd.to_numeric(frame["sum_open_interest"], errors="coerce")
    series = pd.Series(values.to_numpy(), index=timestamps.to_numpy(), name="open_interest")
    return series[~series.index.duplicated(keep="first")].sort_index().dropna()


def causal_features(price: pd.DataFrame, oi: pd.Series) -> pd.DataFrame:
    price_index = set(price.index.astype(int))
    oi_index = set(oi.index.astype(int))
    decisions = [int(timestamp) for timestamp in price.index
                 if int(timestamp) % DECISION_SECONDS == 0
                 and int(timestamp) - PRICE_LAG_SECONDS in price_index
                 and int(timestamp) - DECISION_SECONDS - PRICE_LAG_SECONDS in price_index
                 and int(timestamp) - OI_LAG_SECONDS in oi_index
                 and int(timestamp) - DECISION_SECONDS - OI_LAG_SECONDS in oi_index]
    rows = []
    for timestamp in decisions:
        current_close = float(price.loc[timestamp - PRICE_LAG_SECONDS, "close"])
        prior_close = float(price.loc[timestamp - DECISION_SECONDS - PRICE_LAG_SECONDS, "close"])
        current_oi = float(oi.loc[timestamp - OI_LAG_SECONDS])
        prior_oi = float(oi.loc[timestamp - DECISION_SECONDS - OI_LAG_SECONDS])
        rows.append({"decision_timestamp": timestamp, "price_return": current_close / prior_close - 1,
                     "oi_return": current_oi / prior_oi - 1 if prior_oi > 0 else np.nan})
    frame = pd.DataFrame(rows).set_index("decision_timestamp")
    frame["price_threshold"] = frame["price_return"].abs().shift(1).rolling(WARMUP, min_periods=WARMUP).quantile(0.75)
    frame["oi_threshold"] = frame["oi_return"].shift(1).rolling(WARMUP, min_periods=WARMUP).quantile(0.75)
    return frame


def load_funding(path: Path) -> pd.Series:
    frame = pd.read_csv(path).sort_values("timestamp").drop_duplicates("timestamp")
    return pd.Series(pd.to_numeric(frame["funding_rate"], errors="coerce").to_numpy(),
                     index=frame["timestamp"].astype(int).to_numpy()).dropna()


def collect_trades(symbol: str, price: pd.DataFrame, oi: pd.Series, funding: pd.Series,
                   fold_boundaries: list[int] | None = None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    features = causal_features(price, oi)
    eligible = features.dropna().copy()
    trades: list[dict[str, Any]] = []
    last_exit = -1
    census = {"valid_feature_decisions": len(features), "eligible_after_warmup": len(eligible),
              "non_signal": 0, "overlap_rejected": 0, "missing_exit": 0,
              "unresolved_at_fold_end": 0}
    for timestamp, row in eligible.iterrows():
        timestamp = int(timestamp)
        price_return, oi_return = float(row["price_return"]), float(row["oi_return"])
        if (abs(price_return) < float(row["price_threshold"]) or oi_return <= 0
                or oi_return < float(row["oi_threshold"]) or price_return == 0):
            census["non_signal"] += 1
            continue
        exit_timestamp = timestamp + EXIT_SECONDS
        if timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        if exit_timestamp not in price.index:
            census["missing_exit"] += 1
            continue
        fold = None
        if fold_boundaries is not None:
            fold_index = max(index for index in range(FOLDS) if timestamp >= fold_boundaries[index])
            if exit_timestamp >= fold_boundaries[fold_index + 1]:
                census["unresolved_at_fold_end"] += 1
                continue
            fold = fold_index + 1
        direction = 1.0 if price_return > 0 else -1.0
        entry, exit_price = float(price.loc[timestamp, "open"]), float(price.loc[exit_timestamp, "open"])
        funding_rates = funding.loc[(funding.index > timestamp) & (funding.index <= exit_timestamp)]
        funding_return = -direction * float(funding_rates.sum())
        trade = {"symbol": symbol, "side": "LONG" if direction > 0 else "SHORT", "fold": fold,
                 "decision_timestamp": timestamp, "entry_timestamp": timestamp,
                 "exit_timestamp": exit_timestamp, "price_return_feature": price_return,
                 "oi_return_feature": oi_return,
                 "price_impulse_ratio": abs(price_return) / float(row["price_threshold"]),
                 "oi_expansion_ratio": oi_return / float(row["oi_threshold"]) if row["oi_threshold"] else None,
                 "entry_price": entry, "exit_price": exit_price,
                 "price_pnl_return": direction * (exit_price - entry) / entry,
                 "funding_return": funding_return}
        trade["gross_return"] = trade["price_pnl_return"] + funding_return
        trades.append(trade)
        last_exit = exit_timestamp
    return trades, census


def metrics(trades: list[dict[str, Any]], cost: float = PRIMARY_COST,
            field: str = "gross_return") -> dict[str, Any]:
    values = np.asarray([trade[field] - cost for trade in trades], dtype=float)
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None,
                "average_win": None, "average_loss": None, "payoff_ratio": None,
                "max_drawdown": None}
    wins, losses = values[values > 0], values[values <= 0]
    average_win = float(wins.mean()) if len(wins) else None
    average_loss = float(losses.mean()) if len(losses) else None
    equity = values.cumsum(); drawdown = np.maximum.accumulate(np.r_[0.0, equity])[1:] - equity
    return {"n": len(values), "expectancy": float(values.mean()),
            "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
            "win_rate": float((values > 0).mean()), "average_win": average_win,
            "average_loss": average_loss,
            "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
            "max_drawdown": float(drawdown.max(initial=0.0))}


def day_cluster_ci(trades: list[dict[str, Any]], samples: int = 10_000) -> list[float | None]:
    if not trades:
        return [None, None]
    clusters: dict[int, list[float]] = {}
    for trade in trades:
        clusters.setdefault(trade["decision_timestamp"] // 86400, []).append(trade["gross_return"] - PRIMARY_COST)
    keys = list(clusters); rng = np.random.default_rng(42); estimates = np.empty(samples)
    for index in range(samples):
        sampled = rng.choice(len(keys), len(keys), replace=True)
        values = [value for cluster_index in sampled for value in clusters[keys[int(cluster_index)]]]
        estimates[index] = np.mean(values)
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def evaluate_sample(price_dir: Path, oi_dir: Path, funding_dir: Path,
                    primary: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prices = {symbol: load_price(price_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    oi = {symbol: load_oi(oi_dir / f"{symbol}.csv.gz") for symbol in SYMBOLS}
    funding = {symbol: load_funding(funding_dir / f"{symbol}.csv") for symbol in SYMBOLS}
    decision_union = sorted({int(timestamp) for symbol in SYMBOLS
                             for timestamp in causal_features(prices[symbol], oi[symbol]).dropna().index})
    boundaries = None
    if primary:
        boundaries = [decision_union[index * len(decision_union) // FOLDS] for index in range(FOLDS)]
        boundaries.append(decision_union[-1] + 2 * DECISION_SECONDS)
    trades: list[dict[str, Any]] = []
    census = {}
    for symbol in SYMBOLS:
        selected, counts = collect_trades(symbol, prices[symbol], oi[symbol], funding[symbol], boundaries)
        trades.extend(selected); census[symbol] = counts
    trades.sort(key=lambda trade: (trade["entry_timestamp"], trade["symbol"]))
    return trades, {"census": census, "fold_boundaries": boundaries}


def build_report(primary_price_dir: Path, reverse_price_dir: Path, oi_dir: Path,
                 funding_dir: Path) -> dict[str, Any]:
    primary, primary_info = evaluate_sample(primary_price_dir, oi_dir, funding_dir, True)
    reverse, reverse_info = evaluate_sample(reverse_price_dir, oi_dir, funding_dir, False)
    overall = metrics(primary); ci = day_cluster_ci(primary)
    by_fold = {f"F{fold}": metrics([trade for trade in primary if trade["fold"] == fold])
               for fold in range(1, FOLDS + 1)}
    by_side = {side: metrics([trade for trade in primary if trade["side"] == side])
               for side in ("LONG", "SHORT")}
    by_symbol = {symbol: metrics([trade for trade in primary if trade["symbol"] == symbol])
                 for symbol in SYMBOLS}
    positive = {symbol: sum(max(0.0, trade["gross_return"] - PRIMARY_COST) for trade in primary
                            if trade["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    costs = {f"{cost:.3f}": metrics(primary, cost) for cost in COSTS}
    reverse_metrics = metrics(reverse)
    adequate_folds = [item for item in by_fold.values() if item["n"] >= 100]
    gate = {"adequately_sampled_folds": len(adequate_folds),
            "positive_adequate_folds": sum(item["expectancy"] > 0 for item in adequate_folds),
            "both_sides_positive_and_sampled": all(item["n"] >= 100 and item["expectancy"] > 0
                                                    for item in by_side.values()),
            "positive_sampled_symbols": sum(item["n"] >= 80 and item["expectancy"] > 0
                                            for item in by_symbol.values()),
            "max_positive_pnl_symbol_concentration": concentration}
    keep = (overall["expectancy"] is not None and overall["expectancy"] > 0
            and overall["profit_factor"] is not None and overall["profit_factor"] > 1
            and ci[0] is not None and ci[0] > 0 and gate["positive_adequate_folds"] >= 3
            and gate["both_sides_positive_and_sampled"] and gate["positive_sampled_symbols"] >= 4
            and concentration is not None and concentration <= 0.35
            and reverse_metrics["n"] >= 300 and reverse_metrics["expectancy"] > 0
            and reverse_metrics["profit_factor"] is not None and reverse_metrics["profit_factor"] > 1
            and costs["0.005"]["expectancy"] > 0)
    gate["verdict"] = "KEEP_FOR_PATH_DEPENDENT_CONFIRMATION" if keep else "REJECT"
    return {"candidate": "C-16", "protocol": "edge-candidate-register-v15",
            "primary": {"overall_funding_inclusive": overall,
                        "overall_price_only": metrics(primary, field="price_pnl_return"),
                        "mean_funding_return": float(np.mean([trade["funding_return"] for trade in primary])) if primary else None,
                        "day_cluster_bootstrap_95_ci": ci, "by_fold": by_fold, "by_side": by_side,
                        "by_symbol": by_symbol, "cost_sensitivity": costs, **primary_info},
            "reverse_time": {"overall_funding_inclusive": reverse_metrics, **reverse_info},
            "gate": gate, "limitations": ["Fixed 24-hour exits isolate signal information and are not production exits."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-price-dir", default="data/research/c06/binance_futures_15m")
    parser.add_argument("--reverse-price-dir", default="data/research/c09/binance_futures_15m")
    parser.add_argument("--oi-dir", default="data/research/oi_metrics/normalized")
    parser.add_argument("--funding-dir", default="data/research/c16/funding")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(Path(args.primary_price_dir), Path(args.reverse_price_dir),
                          Path(args.oi_dir), Path(args.funding_dir))
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
