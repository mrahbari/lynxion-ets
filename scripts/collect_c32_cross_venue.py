#!/usr/bin/env python3
"""Prospective public-book collector for C-32. Contains no broker or order imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Callable

import requests


BOUNDARY = 1788669552
SYMBOLS = {
    "BTCUSDT": "BTC-USDT",
    "ETHUSDT": "ETH-USDT",
    "SOLUSDT": "SOL-USDT",
}
BINANCE_DEPTH_URL = "https://fapi.binance.com/fapi/v1/depth"
BINGX_DEPTH_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/depth"
REFERENCE_NOTIONAL = 1_000.0
MAX_SKEW_MS = 2_000
MAX_AGE_MS = 3_000
SIGNAL_FLOOR = 0.006


class InvalidObservation(ValueError):
    """A fail-closed C-32 observation rejection."""


def _positive(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise InvalidObservation("book values must be numeric") from error
    if not math.isfinite(number) or number <= 0:
        raise InvalidObservation("book values must be finite and positive")
    return number


def _levels(payload: dict[str, Any], side: str) -> list[tuple[float, float]]:
    raw_levels = payload.get(side)
    if not isinstance(raw_levels, list):
        raise InvalidObservation(f"{side} must be a list")
    levels = []
    for row in raw_levels:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            raise InvalidObservation(f"{side} contains a malformed level")
        levels.append((_positive(row[0]), _positive(row[1])))
    return levels


def parse_book(venue: str, payload: Any) -> dict[str, Any]:
    if venue == "bingx":
        if not isinstance(payload, dict) or payload.get("code") not in (0, "0"):
            raise InvalidObservation("bingx response is unsuccessful")
        payload = payload.get("data")
    if not isinstance(payload, dict):
        raise InvalidObservation("book payload must be an object")

    timestamp = next((payload[key] for key in ("T", "ts", "timestamp", "E") if key in payload), None)
    if timestamp is None:
        raise InvalidObservation("book server timestamp is missing")
    try:
        timestamp_ms = int(timestamp)
    except (TypeError, ValueError) as error:
        raise InvalidObservation("book server timestamp is malformed") from error
    bids = _levels(payload, "bids")
    asks = _levels(payload, "asks")
    if not bids or not asks:
        raise InvalidObservation("book side is empty")
    if bids != sorted(bids, key=lambda row: row[0], reverse=True):
        raise InvalidObservation("bids are not descending")
    if asks != sorted(asks, key=lambda row: row[0]):
        raise InvalidObservation("asks are not ascending")
    if bids[0][0] >= asks[0][0]:
        raise InvalidObservation("book is crossed")
    return {"server_timestamp_ms": timestamp_ms, "bids": bids, "asks": asks}


def depth_vwap(levels: list[tuple[float, float]], quantity: float) -> float:
    remaining = _positive(quantity)
    cost = 0.0
    for price, available in levels:
        take = min(remaining, available)
        cost += take * price
        remaining -= take
        if remaining <= 1e-12:
            return cost / quantity
    raise InvalidObservation("insufficient depth for reference quantity")


def build_observation(
    *,
    scheduled_minute: int,
    symbol: str,
    binance_raw: bytes,
    bingx_raw: bytes,
    comparison_time_ms: int,
    receipt_monotonic_ns: dict[str, int],
) -> dict[str, Any]:
    if scheduled_minute % 60 or scheduled_minute <= BOUNDARY:
        raise InvalidObservation("scheduled minute is outside prospective boundary")
    if symbol not in SYMBOLS:
        raise InvalidObservation("symbol is outside frozen universe")
    try:
        binance_payload = json.loads(binance_raw)
        bingx_payload = json.loads(bingx_raw)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidObservation("response is not valid JSON") from error

    books = {
        "binance": parse_book("binance", binance_payload),
        "bingx": parse_book("bingx", bingx_payload),
    }
    if set(receipt_monotonic_ns) != {"binance", "bingx"}:
        raise InvalidObservation("both receipt timestamps are required")
    receipts = [int(receipt_monotonic_ns[venue]) for venue in ("binance", "bingx")]
    if min(receipts) <= 0 or max(receipts) - min(receipts) > MAX_SKEW_MS * 1_000_000:
        raise InvalidObservation("venue books exceed frozen receipt skew")
    timestamps = [book["server_timestamp_ms"] for book in books.values()]
    if max(timestamps) - min(timestamps) > MAX_SKEW_MS:
        raise InvalidObservation("venue books exceed frozen timestamp skew")
    if any(comparison_time_ms - stamp < 0 or comparison_time_ms - stamp > MAX_AGE_MS for stamp in timestamps):
        raise InvalidObservation("venue book is stale or future-dated")

    expensive_ask = max(book["asks"][0][0] for book in books.values())
    quantity = REFERENCE_NOTIONAL / expensive_ask
    binance_bid = depth_vwap(books["binance"]["bids"], quantity)
    binance_ask = depth_vwap(books["binance"]["asks"], quantity)
    bingx_bid = depth_vwap(books["bingx"]["bids"], quantity)
    bingx_ask = depth_vwap(books["bingx"]["asks"], quantity)
    spreads = {
        "SELL_BINANCE_BUY_BINGX": binance_bid / bingx_ask - 1.0,
        "SELL_BINGX_BUY_BINANCE": bingx_bid / binance_ask - 1.0,
    }
    qualified = [direction for direction, spread in spreads.items() if spread >= SIGNAL_FLOOR]
    if len(qualified) > 1:
        raise InvalidObservation("both directions qualify")
    return {
        "key": f"{scheduled_minute}:{symbol}",
        "scheduled_minute": scheduled_minute,
        "symbol": symbol,
        "comparison_time_ms": comparison_time_ms,
        "receipt_monotonic_ns": {venue: int(receipt_monotonic_ns[venue]) for venue in ("binance", "bingx")},
        "server_timestamps_ms": {venue: book["server_timestamp_ms"] for venue, book in books.items()},
        "raw_sha256": {
            "binance": hashlib.sha256(binance_raw).hexdigest(),
            "bingx": hashlib.sha256(bingx_raw).hexdigest(),
        },
        "base_quantity": quantity,
        "normalized_books": {
            venue: {side: [[price, size] for price, size in book[side]] for side in ("bids", "asks")}
            for venue, book in books.items()
        },
        "vwap": {
            "binance_bid": binance_bid,
            "binance_ask": binance_ask,
            "bingx_bid": bingx_bid,
            "bingx_ask": bingx_ask,
        },
        "gross_spreads": spreads,
        "signal_direction": qualified[0] if qualified else None,
    }


def append_observation(path: Path, observation: dict[str, Any]) -> bool:
    if int(observation.get("scheduled_minute", 0)) <= BOUNDARY:
        raise InvalidObservation("cannot append pre-boundary observation")
    keys: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError as error:
                raise InvalidObservation("ledger contains malformed JSON") from error
            if int(existing.get("scheduled_minute", 0)) <= BOUNDARY:
                raise InvalidObservation("ledger contains pre-boundary observation")
            key = str(existing.get("key", ""))
            if not key or key in keys:
                raise InvalidObservation("ledger contains invalid or duplicate key")
            keys.add(key)
    if observation["key"] in keys:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(observation, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def fetch_raw(url: str, params: dict[str, Any], get: Callable[..., Any] = requests.get) -> tuple[bytes, int]:
    response = get(url, params=params, timeout=10)
    response.raise_for_status()
    return bytes(response.content), time.monotonic_ns()


def collect_once(symbol: str, scheduled_minute: int, get: Callable[..., Any] = requests.get) -> dict[str, Any]:
    binance_raw, binance_receipt = fetch_raw(BINANCE_DEPTH_URL, {"symbol": symbol, "limit": 20}, get)
    bingx_raw, bingx_receipt = fetch_raw(BINGX_DEPTH_URL, {"symbol": SYMBOLS[symbol], "limit": 20}, get)
    return build_observation(
        scheduled_minute=scheduled_minute,
        symbol=symbol,
        binance_raw=binance_raw,
        bingx_raw=bingx_raw,
        comparison_time_ms=int(time.time() * 1000),
        receipt_monotonic_ns={"binance": binance_receipt, "bingx": bingx_receipt},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/research/c32/observations.jsonl"))
    parser.add_argument("--enable-network", action="store_true")
    args = parser.parse_args()
    if not args.enable_network:
        raise SystemExit("network collection is fail-closed; pass --enable-network explicitly")
    scheduled_minute = int(time.time()) // 60 * 60
    for symbol in SYMBOLS:
        observation = collect_once(symbol, scheduled_minute)
        append_observation(args.output, observation)
        print(json.dumps(observation, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
