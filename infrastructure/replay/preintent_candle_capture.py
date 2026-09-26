"""Read the frozen public pre-intent candle capture without market/network access.

This adapter changes only DataSource: it does not calculate signals or outcomes.
The raw JSON and capture manifest must already exist and match their hashes.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource


HOUR_MS = 3_600_000
EXPECTED_SYMBOLS = ("BTCUSDT", "ETHUSDT")
EXPECTED_START_MS = 1780185600000
EXPECTED_END_MS = 1782950400000
EXPECTED_PARENT_HASH = "454485ff11fad12a9ad355517d3c1461b1df1676e182937c6c2d7e02d10a8cac"
EXPECTED_ADDENDUM_HASH = "b17e50a75591b26d08f435d460e9a9a8ca928ef0aab633b73de2ba495416bae5"


def _utc_milliseconds(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("exchange time must be integer milliseconds")
    return datetime.fromtimestamp(value / 1000, timezone.utc)


def load_frozen_capture(manifest_path, repository_root):
    """Return validated closed bars and fixed-window counts; fail on any defect."""
    manifest_path = Path(manifest_path)
    repository_root = Path(repository_root).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("parent_preregistration_sha256") != EXPECTED_PARENT_HASH:
        raise ValueError("parent preregistration identity mismatch")
    if manifest.get("data_addendum_sha256") != EXPECTED_ADDENDUM_HASH:
        raise ValueError("data addendum identity mismatch")
    if manifest.get("acquisition_open_time_start_ms") != EXPECTED_START_MS:
        raise ValueError("acquisition start mismatch")
    if manifest.get("acquisition_open_time_end_exclusive_ms") != EXPECTED_END_MS:
        raise ValueError("acquisition end mismatch")

    records = manifest.get("records", [])
    if tuple(record.get("symbol") for record in records) != EXPECTED_SYMBOLS:
        raise ValueError("symbol/source cohort mismatch")
    by_symbol = {}
    counts = {}
    for record in records:
        symbol = record["symbol"]
        if record.get("source") != "Binance USD-M Futures public klines":
            raise ValueError("source mismatch")
        if record.get("endpoint") != "https://fapi.binance.com/fapi/v1/klines":
            raise ValueError("endpoint mismatch")
        raw_path = (repository_root / record["path"]).resolve()
        if repository_root not in raw_path.parents or "candle_capture_v1/raw" not in str(raw_path):
            raise ValueError("raw path escapes frozen capture")
        raw = raw_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["sha256"] or len(raw) != record["bytes"]:
            raise ValueError("raw response hash/size mismatch")
        rows = json.loads(raw)
        if not isinstance(rows, list) or len(rows) != record["row_count"]:
            raise ValueError("raw row count mismatch")
        if len(rows) != (EXPECTED_END_MS - EXPECTED_START_MS) // HOUR_MS:
            raise ValueError("incomplete acquisition interval")
        bars = []
        for index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != 12:
                raise ValueError("invalid raw kline schema")
            open_ms, exchange_close_ms = row[0], row[6]
            expected_open_ms = EXPECTED_START_MS + index * HOUR_MS
            if open_ms != expected_open_ms or exchange_close_ms != open_ms + HOUR_MS - 1:
                raise ValueError("gap, duplicate, ordering, alignment or close-time defect")
            try:
                o, h, l, c, v = (float(row[column]) for column in range(1, 6))
            except (ValueError, TypeError, OverflowError) as exc:
                raise ValueError("non-numeric OHLCV") from exc
            if not all(isfinite(value) for value in (o, h, l, c, v)):
                raise ValueError("nonfinite OHLCV")
            if min(o, h, l, c) <= 0 or v < 0 or l > min(o, c) or h < max(o, c):
                raise ValueError("invalid OHLCV geometry or volume")
            bars.append(ClosedBar(
                symbol=symbol, timeframe=timedelta(hours=1),
                open_time=_utc_milliseconds(open_ms),
                close_time=_utc_milliseconds(exchange_close_ms + 1),
                open=o, high=h, low=l, close=c, volume=v,
            ))
        if rows[0][0] != record["first_open_time_ms"] or rows[-1][0] != record["last_open_time_ms"]:
            raise ValueError("open-time record mismatch")
        if rows[0][6] != record["first_close_time_ms"] or rows[-1][6] != record["last_close_time_ms"]:
            raise ValueError("close-time record mismatch")
        by_symbol[symbol] = bars
        counts[symbol] = {
            "outside_leading": 24,
            "warmup": 50,
            "evaluation": 670,
            "outside_trailing": 24,
            "total": len(bars),
            "first_open_time": bars[0].open_time.isoformat(),
            "last_availability_time": bars[-1].close_time.isoformat(),
        }
    ordered = tuple(sorted((bar for bars in by_symbol.values() for bar in bars),
                           key=lambda bar: (bar.close_time, bar.symbol)))
    HistoricalClosedBarSource(ordered)
    return ordered, counts
