#!/usr/bin/env python3
"""Fetch and validate the frozen TASK-0112 Binance premium-index archive."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

import requests


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
START = date(2020, 1, 1)
END = date(2026, 8, 29)
INTERVAL_SECONDS = 15 * 60
REVERSE_START = 1_672_531_200  # 2023-01-01 UTC
REVERSE_END = 1_704_067_199    # 2023-12-31 UTC
PRIMARY_START = 1_704_067_200  # 2024-01-01 UTC
S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DATA_URL = "https://data.binance.vision/"
COLUMNS = ("open_time", "open", "high", "low", "close", "volume", "close_time",
           "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore")
DATE_PATTERN = re.compile(r"-(\d{4}-\d{2}-\d{2})\.zip$")


def _common():
    path = Path(__file__).with_name("fetch_binance_oi_metrics_panel.py")
    spec = importlib.util.spec_from_file_location("archive_common", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def list_archives(symbol: str, start: date = START, end: date = END,
                  get: Callable[..., Any] = requests.get) -> list[str]:
    prefix = f"data/futures/um/daily/premiumIndexKlines/{symbol}/15m/"
    keys: list[str] = []
    token = None
    while True:
        params = {"list-type": "2", "prefix": prefix, "max-keys": 1000}
        if token:
            params["continuation-token"] = token
        response = get(S3_LIST_URL, params=params, timeout=30)
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        for item in root.findall("s3:Contents", namespace):
            key = item.findtext("s3:Key", namespaces=namespace) or ""
            match = DATE_PATTERN.search(key)
            if match and start <= date.fromisoformat(match.group(1)) <= end:
                keys.append(key)
        if root.findtext("s3:IsTruncated", default="false", namespaces=namespace) != "true":
            break
        token = root.findtext("s3:NextContinuationToken", namespaces=namespace)
        if not token:
            raise ValueError(f"{symbol}: truncated listing without continuation token")
    return sorted(set(keys))


def download_archive(key: str, raw_root: Path,
                     get: Callable[..., Any] = requests.get) -> dict[str, Any]:
    common = _common()
    filename = Path(key).name
    symbol = key.split("/premiumIndexKlines/", 1)[1].split("/", 1)[0]
    target = raw_root / symbol / filename
    checksum_response = get(DATA_URL + key + ".CHECKSUM", timeout=30)
    checksum_response.raise_for_status()
    expected = common.expected_checksum(checksum_response.text, filename)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return {"key": key, "sha256": expected, "bytes": target.stat().st_size, "cached": True}
    response = get(DATA_URL + key, timeout=60)
    response.raise_for_status()
    payload = response.content
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"{key}: checksum mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(target)
    return {"key": key, "sha256": actual, "bytes": len(payload), "cached": False}


def epoch_seconds(value: str) -> int:
    raw = int(value)
    return raw // 1_000_000 if raw >= 10**15 else raw // 1_000


def parse_archive(path: Path) -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    checks = {"raw_rows": 0, "schema_violations": 0, "numeric_violations": 0,
              "timestamp_violations": 0, "ohlc_violations": 0}
    rows: list[tuple[Any, ...]] = []
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one CSV member")
        with archive.open(members[0]) as binary:
            reader = csv.reader(io.TextIOWrapper(binary, encoding="utf-8"))
            for raw in reader:
                if raw and raw[0] == "open_time":
                    if tuple(raw) != COLUMNS:
                        checks["schema_violations"] += 1
                    continue
                checks["raw_rows"] += 1
                if len(raw) != len(COLUMNS):
                    checks["schema_violations"] += 1
                    continue
                try:
                    opened, closed = epoch_seconds(raw[0]), epoch_seconds(raw[6])
                    prices = tuple(float(raw[index]) for index in range(1, 5))
                    if not all(math.isfinite(value) for value in prices):
                        raise ValueError
                except (TypeError, ValueError, OverflowError):
                    checks["numeric_violations"] += 1
                    continue
                if opened % INTERVAL_SECONDS or closed != opened + INTERVAL_SECONDS - 1:
                    checks["timestamp_violations"] += 1
                    continue
                open_price, high, low, close = prices
                if high < max(open_price, close, low) or low > min(open_price, close, high):
                    checks["ohlc_violations"] += 1
                    continue
                rows.append((opened, *prices))
    return rows, checks


def normalize_symbol(symbol: str, records: list[dict[str, Any]], raw_root: Path,
                     normalized_root: Path) -> dict[str, Any]:
    totals = {"archives": len(records), "raw_rows": 0, "unique_rows": 0,
              "exact_duplicates": 0, "conflicting_duplicates": 0, "schema_violations": 0,
              "numeric_violations": 0, "timestamp_violations": 0, "ohlc_violations": 0,
              "missing_intervals": 0, "reverse_sample_rows": 0, "primary_sample_rows": 0}
    by_timestamp: dict[int, tuple[Any, ...]] = {}
    for record in sorted(records, key=lambda item: item["key"]):
        path = raw_root / symbol / Path(record["key"]).name
        rows, checks = parse_archive(path)
        for key, value in checks.items():
            totals[key] += value
        for row in rows:
            previous = by_timestamp.get(row[0])
            if previous is None:
                by_timestamp[row[0]] = row
            elif previous == row:
                totals["exact_duplicates"] += 1
            else:
                totals["conflicting_duplicates"] += 1
    ordered = [by_timestamp[key] for key in sorted(by_timestamp)]
    totals["unique_rows"] = len(ordered)
    totals["reverse_sample_rows"] = sum(REVERSE_START <= row[0] <= REVERSE_END for row in ordered)
    totals["primary_sample_rows"] = sum(row[0] >= PRIMARY_START for row in ordered)
    totals["missing_intervals"] = sum(max(0, (right[0] - left[0]) // INTERVAL_SECONDS - 1)
                                      for left, right in zip(ordered, ordered[1:]))
    target = normalized_root / f"{symbol}.csv.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    with gzip.open(temporary, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("timestamp", "open", "high", "low", "close"))
        for row in ordered:
            writer.writerow(row)
            digest.update((",".join(map(str, row)) + "\n").encode())
    temporary.replace(target)
    totals.update({"first_timestamp": ordered[0][0] if ordered else None,
                   "last_timestamp": ordered[-1][0] if ordered else None,
                   "normalized_sha256": digest.hexdigest(), "normalized_file": str(target)})
    return totals


def panel_gate(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    core = sum(summary[key] for summary in summaries.values()
               for key in ("conflicting_duplicates", "schema_violations", "numeric_violations",
                           "timestamp_violations", "ohlc_violations"))
    gaps = sum(summary["missing_intervals"] for summary in summaries.values())
    adequate = all(summary["reverse_sample_rows"] >= 35_000
                   and summary["primary_sample_rows"] >= 90_000
                   for summary in summaries.values())
    return {"core_integrity_violations": core, "source_gap_intervals": gaps,
            "adequate_sample_coverage": adequate,
            "verdict": "KEEP" if core == 0 and adequate else "REJECT"}


def build(output_root: Path, workers: int = 24, symbols: tuple[str, ...] = SYMBOLS,
          start: date = START, end: date = END) -> dict[str, Any]:
    raw_root, normalized_root = output_root / "raw", output_root / "normalized"
    listings = {symbol: list_archives(symbol, start, end) for symbol in symbols}
    records: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    jobs = [(symbol, key) for symbol, keys in listings.items() for key in keys]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_archive, key, raw_root): symbol for symbol, key in jobs}
        for completed, future in enumerate(as_completed(futures), 1):
            records[futures[future]].append(future.result())
            if completed % 500 == 0 or completed == len(jobs):
                print(f"downloaded/verified {completed}/{len(jobs)} archives", flush=True)
    summaries = {symbol: normalize_symbol(symbol, records[symbol], raw_root, normalized_root)
                 for symbol in symbols}
    manifest = {"task": "TASK-0112", "source": DATA_URL, "interval": "15m",
                "requested_start": start.isoformat(), "requested_end": end.isoformat(),
                "symbols": summaries,
                "archives": {symbol: sorted(records[symbol], key=lambda item: item["key"])
                             for symbol in symbols},
                "gate": panel_gate(summaries)}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def normalize_only(output_root: Path) -> dict[str, Any]:
    manifest_path = output_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summaries = {
        symbol: normalize_symbol(symbol, records, output_root / "raw", output_root / "normalized")
        for symbol, records in manifest["archives"].items()
    }
    manifest["symbols"] = summaries
    manifest["gate"] = panel_gate(summaries)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="data/research/premium_index")
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    parser.add_argument("--start", type=date.fromisoformat, default=START)
    parser.add_argument("--end", type=date.fromisoformat, default=END)
    parser.add_argument("--normalize-only", action="store_true")
    args = parser.parse_args()
    report = normalize_only(Path(args.output_root)) if args.normalize_only else build(
        Path(args.output_root), args.workers, tuple(args.symbols), args.start, args.end
    )
    print(json.dumps({"task": report["task"], "symbols": report["symbols"],
                      "gate": report["gate"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
