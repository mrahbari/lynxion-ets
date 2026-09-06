#!/usr/bin/env python3
"""Evaluate preregistered C-34 cross-venue aggressive-flow divergence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
BAR_SECONDS = 900
DECISION_SECONDS = 14_400
WINDOW_BARS = 16
WARMUP = 180
HOLD_BARS = 96
PRIMARY_COST = 0.003
COSTS = (0.002, 0.003, 0.005)
PRIMARY_START, PRIMARY_END = 1704067200, 1788134400
REVERSE_START, REVERSE_END = 1672531200, 1704067200
SPOT_HASH = {
    "BTCUSDT": "2b58717c3f464e84ab531db07f4263b4c83b52c2f6b460a5445ec150f9c5dec3",
    "ETHUSDT": "79e83e1947022c51126093ef72ab97f0e38fe3d40851fed8c3ad5a15afce75fa",
    "BNBUSDT": "29294ff4fe8c7ee52b3e35f36e944735c7fed09fb5e3878f0720d7ae3352c4c8",
    "XRPUSDT": "a87b83e107e7536fa4e68b280c27700da9bd3f6dbd8b96ca8e39aa104c817455",
    "ADAUSDT": "f081b9da47ce30e2746a235d6a78ad7269ef7add8d6738eac49ac8b1af7c5452",
    "SOLUSDT": "7ac0701eeb2b50ac30cd3575219ada620d567783a3cd10be98813f39869c9011",
}
FUTURES_FLOW_HASH = {
    "BTCUSDT": "f0af424c2b0d001b479f91f3ed0429d0d089b990c007f8968e09761138dd5a93",
    "ETHUSDT": "166467c924a404d5c9927c450c9da927532aabcbd828918c38bd53638d3fd970",
    "BNBUSDT": "79d701f617d3d1920cea26f0217c9a5c8ef6cc24a869a59cc846fcbb93e49276",
    "XRPUSDT": "e11d0e30bdd00574dbc6b2bef2c60b66bd6a8a102806544ad3305d0a24898805",
    "ADAUSDT": "b088031506c7fa0c42f609b1afa6eb9a49ab9898cb848ed6dd00c6b5b71b9520",
    "SOLUSDT": "d45916f83648f1f534e1cc6ab2adba28679403491963279134118a8e8b2c1b29",
}
PERP_HASH = {
    "BTCUSDT": "30e02acebd29a4e47032be70baa7dd3ec0c38a246915fa8329e899edbc07aabb",
    "ETHUSDT": "d44a16a5a7363d6833d0e4e60035acd63826e3e9f65fb3aef260e4c4fde08843",
    "BNBUSDT": "7c9f289c34040f6228f8cdfe415fa045f641b2e7292108bf97bdde34db74c0c0",
    "XRPUSDT": "89629283deadf39234f7d9cd07ad27f0e378c4c81e6d3a227798494667dcfd57",
    "ADAUSDT": "643dc2f29d3e50fb008391fd4787472836dd88eeab7dd92f71ff0820b5dea79a",
    "SOLUSDT": "e6efc15ec3544227426076b059bcaec71a2557520d64433f08cea398c554a382",
}
FUNDING_HASH = {
    "BTCUSDT": "2fe89ca06907e7953cb49c2db052e74158ea9319f50f0bd9dac08fb2a579c097",
    "ETHUSDT": "b978d9a54809ad232583b9419ed2695647d0557bc58074112082fa1472057148",
    "BNBUSDT": "7edf30b5a20f5572361ba7bc41ff89b02df8105a82ff24c1b32a5dc807bca08d",
    "XRPUSDT": "2886be913f6678b660e827d481a2b60d426de6c8b406bcff3c282d3f275e74f9",
    "ADAUSDT": "f27f351e603c0563d9c1e0ea6be10640a8bf38c4a1640383d914cd5aaaa79301",
    "SOLUSDT": "be28b9621e6baf0d3b50365c73e59352996274f4097cae60fe4ffce2528c55a3",
}


def verify(path: Path, expected: str) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"frozen source hash mismatch: {path}")


def load_flow(path: Path) -> pd.DataFrame:
    columns = ["timestamp", "quote_volume", "taker_buy_quote_volume"]
    frame = pd.read_csv(path, usecols=columns)
    frame[columns] = frame[columns].apply(pd.to_numeric, errors="coerce")
    return frame.dropna().sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")


def load_price(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=["timestamp", "open"])
    frame[["timestamp", "open"]] = frame[["timestamp", "open"]].apply(pd.to_numeric, errors="coerce")
    return frame.dropna().sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")


def load_funding(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=["timestamp", "funding_rate"])
    frame[["timestamp", "funding_rate"]] = frame[["timestamp", "funding_rate"]].apply(pd.to_numeric, errors="coerce")
    return frame.dropna().sort_values("timestamp").drop_duplicates("timestamp")


def causal_features(spot: pd.DataFrame, futures: pd.DataFrame) -> pd.DataFrame:
    common = set(spot.index.astype(int)) & set(futures.index.astype(int))
    rows = []
    for decision in sorted(ts for ts in common if ts % DECISION_SECONDS == 0):
        window = [decision - DECISION_SECONDS + index * BAR_SECONDS for index in range(WINDOW_BARS)]
        if any(timestamp not in common for timestamp in window):
            continue
        spot_window, futures_window = spot.loc[window], futures.loc[window]
        values = []
        valid = True
        for frame in (spot_window, futures_window):
            total = float(frame["quote_volume"].sum())
            buy = float(frame["taker_buy_quote_volume"].sum())
            if not np.isfinite(total) or not np.isfinite(buy) or total <= 0 or buy < 0 or buy > total:
                valid = False
                break
            values.append(2 * buy / total - 1)
        if valid:
            spot_score, futures_score = values
            rows.append({
                "decision_timestamp": decision,
                "spot_score": spot_score,
                "futures_score": futures_score,
                "divergence": spot_score - futures_score,
            })
    columns = ["spot_score", "futures_score", "divergence", "spot_threshold", "divergence_threshold"]
    if not rows:
        return pd.DataFrame(columns=columns).rename_axis("decision_timestamp")
    features = pd.DataFrame(rows).set_index("decision_timestamp")
    features["spot_threshold"] = features["spot_score"].abs().shift(1).rolling(WARMUP, min_periods=WARMUP).quantile(0.90)
    features["divergence_threshold"] = features["divergence"].abs().shift(1).rolling(WARMUP, min_periods=WARMUP).quantile(0.90)
    return features


def collect(symbol: str, features: pd.DataFrame, price: pd.DataFrame, funding: pd.DataFrame, start: int, end: int):
    events, last_exit = [], -1
    census = {key: 0 for key in (
        "period_rows", "warmup_rejected", "opposition_rejected", "spot_threshold_rejected",
        "divergence_threshold_rejected", "signals", "missing_path", "overlap_rejected",
    )}
    price_index = set(price.index.astype(int))
    for raw_timestamp, row in features.iterrows():
        timestamp = int(raw_timestamp)
        if not start <= timestamp < end:
            continue
        census["period_rows"] += 1
        if pd.isna(row.spot_threshold) or pd.isna(row.divergence_threshold):
            census["warmup_rejected"] += 1
            continue
        if not row.spot_score * row.futures_score < 0:
            census["opposition_rejected"] += 1
            continue
        if not abs(row.spot_score) > row.spot_threshold:
            census["spot_threshold_rejected"] += 1
            continue
        if not abs(row.divergence) > row.divergence_threshold:
            census["divergence_threshold_rejected"] += 1
            continue
        census["signals"] += 1
        exit_timestamp = timestamp + HOLD_BARS * BAR_SECONDS
        if any(timestamp + index * BAR_SECONDS not in price_index for index in range(HOLD_BARS + 1)):
            census["missing_path"] += 1
            continue
        if timestamp < last_exit:
            census["overlap_rejected"] += 1
            continue
        direction = 1 if row.spot_score > 0 else -1
        entry_price = float(price.loc[timestamp, "open"])
        exit_price = float(price.loc[exit_timestamp, "open"])
        rates = funding.loc[
            (funding["timestamp"] > timestamp) & (funding["timestamp"] <= exit_timestamp), "funding_rate"
        ].sum()
        funding_return = -direction * float(rates)
        price_return = direction * (exit_price / entry_price - 1)
        events.append({
            "symbol": symbol,
            "side": "LONG" if direction > 0 else "SHORT",
            "entry_timestamp": timestamp,
            "exit_timestamp": exit_timestamp,
            "spot_score": float(row.spot_score),
            "futures_score": float(row.futures_score),
            "divergence": float(row.divergence),
            "spot_threshold": float(row.spot_threshold),
            "divergence_threshold": float(row.divergence_threshold),
            "price_return": price_return,
            "funding_return": funding_return,
            "gross_return": price_return + funding_return,
        })
        last_exit = exit_timestamp
    return events, census


def assign_primary_folds(events: list[dict]) -> list[dict]:
    timestamps = sorted(event["entry_timestamp"] for event in events)
    if not timestamps:
        return []
    boundaries = [timestamps[index * len(timestamps) // 4] for index in range(4)] + [max(timestamps) + HOLD_BARS * BAR_SECONDS + 1]
    kept = []
    for event in events:
        fold = max(index for index, boundary in enumerate(boundaries[:-1]) if event["entry_timestamp"] >= boundary)
        if event["exit_timestamp"] < boundaries[fold + 1]:
            event["fold"] = fold + 1
            kept.append(event)
    return kept


def metrics(events: list[dict], cost: float = PRIMARY_COST) -> dict:
    returns = np.asarray([event["gross_return"] - cost for event in events], dtype=float)
    if not len(returns):
        return {"n": 0, "expectancy": None, "profit_factor": None, "win_rate": None, "max_drawdown": None}
    wins, losses = returns[returns > 0], returns[returns <= 0]
    equity = returns.cumsum()
    peak = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    return {
        "n": int(len(returns)),
        "expectancy": float(returns.mean()),
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None,
        "win_rate": float((returns > 0).mean()),
        "max_drawdown": float((peak - equity).max(initial=0)),
    }


def bootstrap(events: list[dict]) -> list[float | None]:
    if not events:
        return [None, None]
    clusters: dict[int, list[float]] = {}
    for event in events:
        clusters.setdefault(event["entry_timestamp"] // 86_400, []).append(event["gross_return"] - PRIMARY_COST)
    days = sorted(clusters)
    random = np.random.default_rng(340034)
    samples = []
    for _ in range(10_000):
        selected = random.choice(days, len(days), replace=True)
        samples.append(np.mean([value for day in selected for value in clusters[int(day)]]))
    return [float(value) for value in np.quantile(samples, [0.025, 0.975])]


def summary(events: list[dict]) -> dict:
    years = sorted({pd.to_datetime(event["entry_timestamp"], unit="s", utc=True).year for event in events})
    return {
        "overall": metrics(events),
        "clustered_bootstrap_95_ci": bootstrap(events),
        "by_fold": {f"F{fold}": metrics([event for event in events if event.get("fold") == fold]) for fold in range(1, 5)},
        "by_side": {side: metrics([event for event in events if event["side"] == side]) for side in ("LONG", "SHORT")},
        "by_symbol": {symbol: metrics([event for event in events if event["symbol"] == symbol]) for symbol in SYMBOLS},
        "by_year": {str(year): metrics([event for event in events if pd.to_datetime(event["entry_timestamp"], unit="s", utc=True).year == year]) for year in years},
        "cost_sensitivity": {f"{cost:.3f}": metrics(events, cost) for cost in COSTS},
        "mean_funding_return": float(np.mean([event["funding_return"] for event in events])) if events else None,
    }


def build_report(spot_dir: Path, futures_flow_dir: Path, price_dir: Path, funding_dir: Path) -> dict:
    primary_events, reverse_events, primary_census, reverse_census = [], [], {}, {}
    for symbol in SYMBOLS:
        paths = (
            (spot_dir / f"{symbol}.csv.gz", SPOT_HASH[symbol]),
            (futures_flow_dir / f"{symbol}.csv.gz", FUTURES_FLOW_HASH[symbol]),
            (price_dir / f"{symbol}.csv", PERP_HASH[symbol]),
            (funding_dir / f"{symbol}.csv", FUNDING_HASH[symbol]),
        )
        for path, digest in paths:
            verify(path, digest)
        spot, futures = load_flow(paths[0][0]), load_flow(paths[1][0])
        price, funding = load_price(paths[2][0]), load_funding(paths[3][0])
        features = causal_features(spot, futures)
        selected, census = collect(symbol, features, price, funding, PRIMARY_START, PRIMARY_END)
        primary_events.extend(selected); primary_census[symbol] = census
        selected, census = collect(symbol, features, price, funding, REVERSE_START, REVERSE_END)
        reverse_events.extend(selected); reverse_census[symbol] = census
    primary_events = assign_primary_folds(primary_events)
    primary, reverse = summary(primary_events), summary(reverse_events)
    positive = {symbol: sum(max(0.0, event["gross_return"] - PRIMARY_COST) for event in primary_events if event["symbol"] == symbol) for symbol in SYMBOLS}
    total_positive = sum(positive.values())
    concentration = max(positive.values(), default=0.0) / total_positive if total_positive else None
    overall = primary["overall"]
    checks = {
        "primary_n": overall["n"] >= 300,
        "primary_positive": overall["expectancy"] is not None and overall["expectancy"] > 0,
        "primary_pf": overall["profit_factor"] is not None and overall["profit_factor"] > 1,
        "bootstrap": primary["clustered_bootstrap_95_ci"][0] is not None and primary["clustered_bootstrap_95_ci"][0] > 0,
        "folds": sum(value["n"] >= 50 and value["expectancy"] is not None and value["expectancy"] > 0 for value in primary["by_fold"].values()) >= 3,
        "sides": all(value["n"] >= 75 and value["expectancy"] is not None and value["expectancy"] > 0 for value in primary["by_side"].values()),
        "symbols": sum(value["n"] >= 40 and value["expectancy"] is not None and value["expectancy"] > 0 for value in primary["by_symbol"].values()) >= 4,
        "years": all(primary["by_year"].get(str(year), {"n": 0})["n"] >= 50 and primary["by_year"][str(year)]["expectancy"] > 0 for year in (2024, 2025, 2026)),
        "concentration": concentration is not None and concentration <= 0.35,
        "drawdown": overall["max_drawdown"] is not None and overall["max_drawdown"] <= 0.20,
        "reverse": reverse["overall"]["n"] >= 150 and reverse["overall"]["expectancy"] is not None and reverse["overall"]["expectancy"] > 0 and reverse["overall"]["profit_factor"] is not None and reverse["overall"]["profit_factor"] > 1,
        "cost_005": primary["cost_sensitivity"]["0.005"]["expectancy"] is not None and primary["cost_sensitivity"]["0.005"]["expectancy"] > 0,
    }
    return {
        "candidate": "C-34", "protocol": "edge-candidate-register-v33",
        "primary_census": primary_census, "reverse_census": reverse_census,
        "primary": primary, "reverse": reverse,
        "max_positive_pnl_symbol_concentration": concentration,
        "gate": {"checks": checks, "verdict": "KEEP_FOR_PROSPECTIVE_VALIDATION" if all(checks.values()) else "REJECT"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spot-dir", type=Path, default=Path("data/research/spot_15m/normalized"))
    parser.add_argument("--futures-flow-dir", type=Path, default=Path("data/research/taker_flow/normalized"))
    parser.add_argument("--price-dir", type=Path, default=Path("data/research/c06/binance_futures_15m"))
    parser.add_argument("--funding-dir", type=Path, default=Path("data/research/c16/funding"))
    parser.add_argument("--output", type=Path, default=Path("docs/reports/edge_candidate_c34.json"))
    args = parser.parse_args()
    report = build_report(args.spot_dir, args.futures_flow_dir, args.price_dir, args.funding_dir)
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
