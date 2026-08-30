#!/usr/bin/env python3
"""Update C-11 prospective shadow funding ledger. Never imports or calls broker code."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import requests


BOUNDARY = 1788082349
SYMBOLS = ("BTCUSDT", "ETHUSDT")
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
KLINE_URL = "https://fapi.binance.com/fapi/v1/klines"
LEDGER = Path("data/research/c11/prospective_ledger.json")
COST = 0.003


def fetch_funding(symbol: str, start_seconds: int, end_seconds: int,
                  get: Callable[..., Any] = requests.get) -> pd.DataFrame:
    cursor, end_ms, rows = start_seconds * 1000, end_seconds * 1000, {}
    while cursor <= end_ms:
        response = get(FUNDING_URL, params={"symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000}, timeout=30)
        response.raise_for_status(); payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("malformed funding response")
        if not payload:
            break
        for item in payload:
            timestamp = int(item["fundingTime"]); rows[timestamp] = float(item["fundingRate"])
        next_cursor = int(payload[-1]["fundingTime"]) + 1
        if next_cursor <= cursor:
            raise ValueError("funding pagination did not advance")
        cursor = next_cursor
        if len(payload) < 1000:
            break
        time.sleep(0.12)
    return pd.DataFrame({"timestamp": [item // 1000 for item in sorted(rows)],
                         "funding_rate": [rows[item] for item in sorted(rows)]})


def fetch_opens(symbol: str, start_seconds: int, end_seconds: int,
                get: Callable[..., Any] = requests.get) -> dict[int, float]:
    response = get(KLINE_URL, params={"symbol": symbol, "interval": "15m", "startTime": start_seconds * 1000,
                                      "endTime": end_seconds * 1000, "limit": 1000}, timeout=30)
    response.raise_for_status(); payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("malformed kline response")
    return {int(row[0]) // 1000: float(row[1]) for row in payload if len(row) >= 2}


def candidate_events(funding: pd.DataFrame, boundary: int = BOUNDARY) -> list[dict[str, Any]]:
    frame = funding.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True).copy()
    frame["threshold"] = frame["funding_rate"].shift(1).rolling(365, min_periods=365).quantile(0.10)
    selected = []
    for row in frame.itertuples(index=False):
        threshold = float(row.threshold) if pd.notna(row.threshold) else np.nan
        rate = float(row.funding_rate)
        if int(row.timestamp) <= boundary or not np.isfinite(threshold) or threshold == 0:
            continue
        severity = abs(rate) / abs(threshold)
        if rate < 0 and rate <= threshold and severity >= 2.0:
            entry = (int(row.timestamp) // 900 + 1) * 900
            selected.append({"funding_timestamp": int(row.timestamp), "funding_rate": rate,
                             "threshold": threshold, "severity_ratio": severity,
                             "expected_entry_timestamp": entry, "expected_exit_timestamp": entry + 86400})
    return selected


def non_overlapping(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accepted = []; last_exit = -1
    for event in sorted(events, key=lambda item: item["funding_timestamp"]):
        if event["expected_entry_timestamp"] < last_exit:
            continue
        accepted.append(event); last_exit = event["expected_exit_timestamp"]
    return accepted


def metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [record for record in records if record["status"] == "COMPLETE"]
    values = np.asarray([record["net_return"] for record in complete], dtype=float)
    if not len(values):
        return {"n": 0, "expectancy": None, "profit_factor": None, "verdict": "COLLECTING"}
    wins, losses = values[values > 0], values[values <= 0]
    pf = float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else None
    return {"n": int(len(values)), "expectancy": float(values.mean()), "profit_factor": pf,
            "verdict": "COLLECTING" if len(values) < 100 else "REVIEW_GATE_REQUIRED"}


def update(now: int | None = None, ledger_path: Path = LEDGER) -> dict[str, Any]:
    now = int(datetime.now(timezone.utc).timestamp()) if now is None else int(now)
    existing = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
        "candidate": "C-11", "protocol": "edge-candidate-register-v10", "boundary": BOUNDARY, "records": []}
    by_key = {record["key"]: record for record in existing["records"]}
    for symbol in SYMBOLS:
        funding = fetch_funding(symbol, BOUNDARY - 180 * 86400, now)
        for event in non_overlapping(candidate_events(funding)):
            key = f"{symbol}:{event['funding_timestamp']}"
            by_key.setdefault(key, {"key": key, "symbol": symbol, "status": "PENDING", **event})
        for record in [item for item in by_key.values() if item["symbol"] == symbol and item["status"] == "PENDING"]:
            if now < record["expected_exit_timestamp"]:
                continue
            try:
                opens = fetch_opens(symbol, record["expected_entry_timestamp"], record["expected_exit_timestamp"])
                entry = opens.get(record["expected_entry_timestamp"]); exit_price = opens.get(record["expected_exit_timestamp"])
                if entry is None or exit_price is None:
                    raise ValueError("exact entry/exit open unavailable")
                cashflows = funding.loc[(funding["timestamp"] > record["expected_entry_timestamp"])
                                        & (funding["timestamp"] <= record["expected_exit_timestamp"]), "funding_rate"]
                record.update({"status": "COMPLETE", "entry_price": entry, "exit_price": exit_price,
                               "price_return": (exit_price - entry) / entry,
                               "funding_return": -float(cashflows.sum())})
                record["net_return"] = record["price_return"] + record["funding_return"] - COST
            except Exception as error:
                record.update({"status": "ERROR", "error": f"{type(error).__name__}:{error}"})
    existing["records"] = sorted(by_key.values(), key=lambda item: (item["funding_timestamp"], item["symbol"]))
    existing["updated_at"] = datetime.fromtimestamp(now, timezone.utc).isoformat()
    existing["metrics"] = metrics(existing["records"])
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(existing, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return existing


if __name__ == "__main__":
    print(json.dumps(update(), indent=2, sort_keys=True, allow_nan=False))
