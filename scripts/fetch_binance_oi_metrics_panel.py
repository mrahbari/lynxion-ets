#!/usr/bin/env python3
"""Fetch and validate the frozen TASK-0106 Binance Futures metrics archive."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

import requests


SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT")
START = date(2020, 9, 1)
END = date(2026, 8, 29)
S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DATA_URL = "https://data.binance.vision/"
EXPECTED_COLUMNS = (
    "create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
    "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
    "count_long_short_ratio", "sum_taker_long_short_vol_ratio",
)
DATE_PATTERN = re.compile(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip$")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def list_archives(symbol: str, start: date = START, end: date = END,
                  get: Callable[..., Any] = requests.get) -> list[str]:
    prefix = f"data/futures/um/daily/metrics/{symbol}/"
    token = None
    keys: list[str] = []
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
        truncated = root.findtext("s3:IsTruncated", default="false", namespaces=namespace) == "true"
        if not truncated:
            break
        token = root.findtext("s3:NextContinuationToken", namespaces=namespace)
        if not token:
            raise ValueError(f"{symbol}: truncated listing without continuation token")
    return sorted(set(keys))


def expected_checksum(text: str, filename: str) -> str:
    parts = text.strip().split()
    if len(parts) < 2 or parts[1].lstrip("*") != filename or len(parts[0]) != 64:
        raise ValueError(f"malformed official checksum for {filename}")
    return parts[0].lower()


def download_archive(key: str, raw_root: Path, get: Callable[..., Any] = requests.get) -> dict[str, Any]:
    filename = Path(key).name
    symbol = filename.split("-metrics-", 1)[0]
    target = raw_root / symbol / filename
    checksum_response = get(DATA_URL + key + ".CHECKSUM", timeout=30)
    checksum_response.raise_for_status()
    expected = expected_checksum(checksum_response.text, filename)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
        return {"key": key, "sha256": expected, "bytes": target.stat().st_size, "cached": True}
    response = get(DATA_URL + key, timeout=60)
    response.raise_for_status()
    payload = response.content
    actual = sha256(payload)
    if actual != expected:
        raise ValueError(f"{key}: checksum mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(target)
    return {"key": key, "sha256": actual, "bytes": len(payload), "cached": False}


def parse_archive(path: Path, expected_symbol: str) -> tuple[list[tuple[Any, ...]], dict[str, int]]:
    checks = {"raw_rows": 0, "exact_duplicates": 0, "conflicting_duplicates": 0,
              "schema_violations": 0, "symbol_violations": 0, "oi_numeric_violations": 0,
              "ratio_missing_rows": 0, "ratio_numeric_violations": 0}
    by_timestamp: dict[str, tuple[Any, ...]] = {}
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{path.name}: expected one CSV member")
        with archive.open(members[0]) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8"))
            if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
                checks["schema_violations"] += 1
                return [], checks
            for row in reader:
                checks["raw_rows"] += 1
                timestamp = row["create_time"]
                if row["symbol"] != expected_symbol:
                    checks["symbol_violations"] += 1
                values = tuple(row[column] for column in EXPECTED_COLUMNS)
                try:
                    oi_values = [float(row[column]) for column in EXPECTED_COLUMNS[2:4]]
                    if not all(math.isfinite(value) and value >= 0 for value in oi_values):
                        checks["oi_numeric_violations"] += 1
                except (TypeError, ValueError):
                    checks["oi_numeric_violations"] += 1
                ratio_text = [row[column] for column in EXPECTED_COLUMNS[4:]]
                if any(value == "" for value in ratio_text):
                    checks["ratio_missing_rows"] += 1
                present_ratios = [value for value in ratio_text if value != ""]
                if present_ratios:
                    try:
                        ratios = [float(value) for value in present_ratios]
                        if not all(math.isfinite(value) for value in ratios):
                            checks["ratio_numeric_violations"] += 1
                    except (TypeError, ValueError):
                        checks["ratio_numeric_violations"] += 1
                previous = by_timestamp.get(timestamp)
                if previous is None:
                    by_timestamp[timestamp] = values
                elif previous == values:
                    checks["exact_duplicates"] += 1
                else:
                    checks["conflicting_duplicates"] += 1
    return [by_timestamp[key] for key in sorted(by_timestamp)], checks


def normalize_symbol(symbol: str, archive_records: list[dict[str, Any]], raw_root: Path,
                     normalized_root: Path) -> dict[str, Any]:
    totals = {"archives": len(archive_records), "raw_rows": 0, "unique_rows": 0,
              "exact_duplicates": 0, "conflicting_duplicates": 0, "schema_violations": 0,
              "symbol_violations": 0, "oi_numeric_violations": 0,
              "ratio_missing_rows": 0, "ratio_numeric_violations": 0,
              "missing_intervals": 0}
    first = last = None
    previous_epoch = None
    digest = hashlib.sha256()
    target = normalized_root / f"{symbol}.csv.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    with gzip.open(temporary, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPECTED_COLUMNS)
        for record in sorted(archive_records, key=lambda item: item["key"]):
            path = raw_root / symbol / Path(record["key"]).name
            rows, checks = parse_archive(path, symbol)
            for key in checks:
                if key in totals:
                    totals[key] += checks[key]
            totals["unique_rows"] += len(rows)
            for row in rows:
                epoch = int(datetime.fromisoformat(str(row[0])).replace(tzinfo=timezone.utc).timestamp())
                if previous_epoch is not None and epoch > previous_epoch + 300:
                    totals["missing_intervals"] += (epoch - previous_epoch) // 300 - 1
                previous_epoch = epoch
                first = epoch if first is None else first
                last = epoch
                writer.writerow(row)
                digest.update((",".join(map(str, row)) + "\n").encode())
    temporary.replace(target)
    totals.update({"first_timestamp": first, "last_timestamp": last,
                   "normalized_sha256": digest.hexdigest(), "normalized_file": str(target)})
    return totals


def build(output_root: Path, workers: int = 12, symbols: tuple[str, ...] = SYMBOLS,
          start: date = START, end: date = END) -> dict[str, Any]:
    raw_root = output_root / "raw"
    normalized_root = output_root / "normalized"
    listings = {symbol: list_archives(symbol, start, end) for symbol in symbols}
    records: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    jobs = [(symbol, key) for symbol, keys in listings.items() for key in keys]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_archive, key, raw_root): symbol for symbol, key in jobs}
        completed = 0
        for future in as_completed(futures):
            symbol = futures[future]
            records[symbol].append(future.result())
            completed += 1
            if completed % 250 == 0 or completed == len(jobs):
                print(f"downloaded/verified {completed}/{len(jobs)} archives", flush=True)
    summaries = {symbol: normalize_symbol(symbol, records[symbol], raw_root, normalized_root)
                 for symbol in symbols}
    violations = sum(summary[key] for summary in summaries.values()
                     for key in ("conflicting_duplicates", "schema_violations",
                                 "symbol_violations", "oi_numeric_violations",
                                 "ratio_numeric_violations"))
    adequate = all(summary["unique_rows"] >= 100_000 for summary in summaries.values())
    manifest = {"task": "TASK-0106", "source": DATA_URL, "requested_start": start.isoformat(),
                "requested_end": end.isoformat(), "symbols": summaries,
                "archives": {symbol: sorted(records[symbol], key=lambda item: item["key"])
                             for symbol in symbols},
                "gate": {"integrity_violations": violations, "adequate_coverage": adequate,
                         "verdict": "KEEP" if violations == 0 and adequate else "REJECT"}}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def normalize_only(output_root: Path) -> dict[str, Any]:
    manifest_path = output_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["archives"]
    summaries = {
        symbol: normalize_symbol(symbol, items, output_root / "raw", output_root / "normalized")
        for symbol, items in records.items()
    }
    violations = sum(summary[key] for summary in summaries.values()
                     for key in ("conflicting_duplicates", "schema_violations", "symbol_violations",
                                 "oi_numeric_violations", "ratio_numeric_violations"))
    adequate = all(summary["unique_rows"] >= 100_000 for summary in summaries.values())
    manifest["symbols"] = summaries
    manifest["gate"] = {"integrity_violations": violations, "adequate_coverage": adequate,
                        "verdict": "KEEP" if violations == 0 and adequate else "REJECT"}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="data/research/oi_metrics")
    parser.add_argument("--workers", type=int, default=12)
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
