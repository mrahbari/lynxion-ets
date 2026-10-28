#!/usr/bin/env python3
"""Offline observed-cohort radar; never emits orders or market-wide claims."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import fmean

from infrastructure.replay.historical_closed_bar_source import ClosedBar, HistoricalClosedBarSource


M15 = timedelta(minutes=15)
H1 = timedelta(hours=1)
UTC = timezone.utc
CONTRACT_VERSION = "OPPORTUNITY_RADAR_V1_RESEARCH"


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_bars(path, symbol, cutoff):
    bars = []
    previous_open = None
    with path.open(newline="") as source:
        for row in csv.DictReader(source):
            opened = datetime.fromtimestamp(int(row["timestamp"]), UTC)
            if previous_open is not None and opened <= previous_open:
                raise ValueError(f"duplicate or out-of-order source timestamp for {symbol}")
            previous_open = opened
            closed = opened + M15
            if closed > cutoff:
                continue
            bars.append(ClosedBar(symbol, M15, opened, closed,
                                  *(float(row[field]) for field in ("open", "high", "low", "close", "volume"))))
    return tuple(HistoricalClosedBarSource(bars).completed_through(cutoff))


def _h1_context(bars, cutoff):
    """Research adapter for the watcher's 30-close normalized regression slope.

    Importing the live watcher also imports its logger/shared runtime and NumPy,
    so only the pure formula is mirrored here; no watcher state is constructed.
    """
    groups = {}
    for bar in bars:
        h1_end = datetime.fromtimestamp(((int(bar.open_time.timestamp()) // 3600) + 1) * 3600, UTC)
        if h1_end <= cutoff:
            groups.setdefault(h1_end, []).append(bar)
    closes = []
    for end in sorted(groups):
        block = groups[end]
        if len(block) == 4 and block[0].open_time == end - H1 and all(
            block[i].close_time == block[i + 1].open_time for i in range(3)
        ):
            closes.append((end, block[-1].close))
    if len(closes) < 30:
        return {"status": "INCOMPLETE", "timeframe": "1h", "last_confirmed_close": None}
    window = closes[-30:]
    values = [v for _, v in window]
    xs = range(len(values))
    mean_x, mean_y = fmean(xs), fmean(values)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    raw_slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denominator
    slope = raw_slope / mean_y
    predicted = [mean_y + raw_slope * (x - mean_x) for x in xs]
    total = sum((y - mean_y) ** 2 for y in values)
    residual = sum((y - p) ** 2 for y, p in zip(values, predicted))
    strength = min(1.0, abs(slope) * (1 - residual / total) if total else abs(slope))
    return {"status": "VALID", "timeframe": "1h", "last_confirmed_close": window[-1][0].isoformat(),
            "available_at": window[-1][0].isoformat(), "state": "UP" if slope > 0 else "DOWN" if slope < 0 else "FLAT",
            "normalized_slope": float(slope), "trend_strength": float(strength),
            "source": "research adapter of TrendMTFWatcher.calculate_trend on 30 completed H1 closes"}


def build_radar(data_dir, cutoff, setup_records=None):
    """Return a deterministic observed-cohort record from a hash-matched local panel."""
    if cutoff.tzinfo is None or cutoff.utcoffset() != timedelta(0):
        raise ValueError("cutoff must be UTC aware")
    manifest_path = data_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("interval") != "15m" or not manifest.get("symbols"):
        raise ValueError("unsupported or missing source manifest")
    rows = []
    for symbol, meta in sorted(manifest["symbols"].items()):
        path = data_dir / f"{symbol}.csv"
        if _sha(path) != meta["sha256"]:
            raise ValueError(f"source hash mismatch for {symbol}")
        bars = _read_bars(path, symbol, cutoff)
        last = bars[-1] if bars else None
        quality = "INCOMPLETE" if len(bars) < 5 else "STALE" if cutoff - last.close_time > M15 else "VALID"
        movement = None
        if quality == "VALID":
            five = bars[-5:]
            if all(five[i].close_time == five[i + 1].open_time for i in range(4)):
                movement = (five[-1].close / five[0].close - 1.0) * 100.0
            else:
                quality = "INCOMPLETE"
        context = _h1_context(bars, cutoff) if bars else {"status": "INCOMPLETE", "timeframe": "1h"}
        rows.append({"symbol": symbol, "venue": "BINANCE_USDM_REPORTED", "instrument": "PERPETUAL_REPORTED",
                     "eligibility": "OBSERVED_IN_PANEL_TRADABILITY_UNKNOWN", "eligibility_at": None,
                     "eligibility_source": "NO_POINT_IN_TIME_EXCHANGE_INFO",
                     "movement_pct_4_closed_m15": movement, "magnitude_pct": abs(movement) if movement is not None else None,
                     "movement_direction": ("UPWARD_MOVEMENT" if movement > 0 else "DOWNWARD_MOVEMENT" if movement < 0
                                            else "NO_CLEAR_DIRECTION") if movement is not None else "NO_CLEAR_DIRECTION",
                     "window_start": bars[-5].close_time.isoformat() if movement is not None else None,
                     "observation_close": last.close_time.isoformat() if last else None,
                     "data_quality": quality,
                     "source_qualification": "MANIFEST_HASH_MATCHED_DEVELOPMENT_ONLY_NO_RECEIPT",
                     "source_sha256": meta["sha256"],
                     "htf_context": context, "ltf_setup": {"status": "SETUP_UNAVAILABLE"}})
    if setup_records is not None:
        candidates = [json.loads(line) for line in setup_records.read_text().splitlines() if line.strip()]
        for row in rows:
            matching = [item for item in candidates if item.get("symbol") == row["symbol"]
                        and item.get("decision_time")
                        and item.get("signal_confirmation_time")
                        and datetime.fromisoformat(item["decision_time"].replace("Z", "+00:00")) == cutoff
                        and datetime.fromisoformat(item["signal_confirmation_time"].replace("Z", "+00:00")) == cutoff
                        and item.get("dataset_sha256") == row["source_sha256"]
                        and item.get("contract_sha256") and item.get("candidate_id")]
            if matching:
                events = {}
                for item in matching:
                    event = {"candidate_id": item["candidate_id"], "direction": item["direction"],
                             "decision_time": item["decision_time"],
                             "confirmation_time": item["signal_confirmation_time"],
                             "contract_sha256": item["contract_sha256"]}
                    prior = events.get(item["candidate_id"])
                    if prior is not None and prior != event:
                        raise ValueError(f"conflicting setup records for {item['candidate_id']}")
                    events[item["candidate_id"]] = event
                row["ltf_setup"] = {"status": "RESEARCH_CANDIDATE_AT_CUTOFF",
                                    "events": [events[key] for key in sorted(events)]}
    ranked = sorted((row for row in rows if row["movement_pct_4_closed_m15"] is not None),
                    key=lambda row: (-abs(row["movement_pct_4_closed_m15"]), row["symbol"]))
    for rank, row in enumerate(ranked, 1):
        row["movement_rank_magnitude"] = rank
    return {"version": CONTRACT_VERSION, "classification": "OBSERVED_COHORT_RANKING_DEVELOPMENT_ONLY",
            "cutoff_utc": cutoff.isoformat(), "source_manifest_sha256": _sha(manifest_path),
            "universe_status": "HISTORICAL_MARKET_WIDE_UNQUALIFIED", "ranked_count": len(ranked),
            "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--cutoff", required=True, help="UTC ISO timestamp, e.g. 2023-01-15T00:00:00+00:00")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--setup-records", type=Path)
    args = parser.parse_args()
    record = build_radar(args.data_dir, datetime.fromisoformat(args.cutoff), args.setup_records)
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload)
    print(f"{args.output} sha256={hashlib.sha256(payload.encode()).hexdigest()} rows={record['ranked_count']}")


if __name__ == "__main__":
    main()
