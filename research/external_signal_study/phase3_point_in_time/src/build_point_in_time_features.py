"""Compute only six frozen Phase 3A pre-event features for cases and controls."""
import bisect
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PHASE = ROOT / "research/external_signal_study/phase3_point_in_time"
DATA = ROOT / "data/research/phase3_point_in_time/binance_futures_15m"
SPEC_HASH = "96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193"
BAR = 900
F4H = 16 * BAR
FEATURES = (
    "F1_directional_4h_return",
    "F2_range_location_20",
    "F3_countertrend_pullback_8",
    "F4_compression_ratio",
    "F5_relative_volume_8",
    "F9_BTC_directional_4h_return",
)


def read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path, records, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def epoch(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp())


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_bars(symbol, expected_sha):
    path = DATA / f"{symbol}.csv"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha, f"changed source: {symbol}"
    bars = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            t = int(row["timestamp"])
            bars[t] = {k: float(row[k]) for k in ("open", "high", "low", "close", "volume")}
    times = sorted(bars)
    assert len(times) == len(bars)
    return bars, times


def closed_15m_window(bars, times, t, count):
    # The API/CSV timestamp is the bar OPEN. A bar becomes available at open+899s.
    index = bisect.bisect_right(times, t - (BAR - 1)) - 1
    if index + 1 < count:
        return None, None
    stamps = times[index - count + 1:index + 1]
    if any(b - a != BAR for a, b in zip(stamps, stamps[1:])):
        return None, None
    assert stamps[-1] + BAR - 1 <= t
    return [bars[x] for x in stamps], stamps[-1] + BAR - 1


def completed_4h_close(bars, t, four_h_bars_prior):
    # Last 4h candle must have fully closed; use its final completed 15m close.
    start = ((t - (F4H - 1)) // F4H) * F4H - four_h_bars_prior * F4H
    last_15m_open = start + 15 * BAR
    close_time = start + F4H - 1
    assert close_time <= t
    bar = bars.get(last_15m_open)
    return (bar["close"], close_time) if bar else (None, None)


def calculate(symbol_bars, btc_bars, t, side):
    s = 1 if side == "LONG" else -1
    bars, times = symbol_bars
    btc, btc_times = btc_bars
    # Longest frozen window: 8 current volume bars + 20 previous 8-bar blocks.
    window, latest_15m_close = closed_15m_window(bars, times, t, 168)
    btc_window, btc_latest_close = closed_15m_window(btc, btc_times, t, 168)
    if window is None or btc_window is None:
        return {f: None for f in FEATURES}, {f: None for f in FEATURES}
    values, availability = {}, {}
    last4, f1_time = completed_4h_close(bars, t, 0)
    prior4, _ = completed_4h_close(bars, t, 4)
    btc_last4, f9_time = completed_4h_close(btc, t, 0)
    btc_prior4, _ = completed_4h_close(btc, t, 4)
    values[FEATURES[0]] = s * math.log(last4 / prior4) if last4 and prior4 and prior4 > 0 else None
    recent20 = window[-20:]
    hi20, lo20 = max(x["high"] for x in recent20), min(x["low"] for x in recent20)
    values[FEATURES[1]] = s * (2 * (window[-1]["close"] - lo20) / (hi20 - lo20) - 1) if hi20 > lo20 else None
    c_now, c_8prior = window[-1]["close"], window[-9]["close"]
    values[FEATURES[2]] = -s * math.log(c_now / c_8prior) if c_now > 0 and c_8prior > 0 else None
    recent8, recent32 = window[-8:], window[-32:]
    range8 = max(x["high"] for x in recent8) - min(x["low"] for x in recent8)
    range32 = max(x["high"] for x in recent32) - min(x["low"] for x in recent32)
    values[FEATURES[3]] = range8 / range32 if range32 > 0 else None
    current_volume = sum(x["volume"] for x in window[-8:])
    prior_volume_mean = sum(x["volume"] for x in window[:-8]) / 20
    values[FEATURES[4]] = current_volume / prior_volume_mean if prior_volume_mean > 0 else None
    values[FEATURES[5]] = s * math.log(btc_last4 / btc_prior4) if btc_last4 and btc_prior4 and btc_prior4 > 0 else None
    for f in FEATURES:
        availability[f] = f1_time if f == FEATURES[0] else f9_time if f == FEATURES[5] else latest_15m_close
        assert availability[f] <= t
        if values[f] is not None:
            assert math.isfinite(values[f])
    assert btc_latest_close <= t
    return values, availability


def main():
    assert hashlib.sha256((PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md").read_bytes()).hexdigest() == SPEC_HASH
    manifest = json.loads((PHASE / "manifests/phase3_proxy_source_manifest.json").read_text())
    controls = read(PHASE / "controls/matched_controls.csv")
    cases = {c["signal_id"]: c for c in read(PHASE / "extracted/phase3_cases.csv")}
    assert len(controls) == 168
    panels = {}
    for symbol, item in manifest["symbols"].items():
        if item["status"] == "COMPLETE_VALIDATED":
            panels[symbol] = load_bars(symbol, item["sha256"])
    records = []
    case_ids = sorted({r["case_id"] for r in controls})
    assert len(case_ids) == 56
    for cid in case_ids:
        c = cases[cid]
        entries = [("CASE", cid, c["signal_timestamp_utc"], c["symbol"], c["side"], c["execution_timeframe"]) ]
        entries.extend(("CONTROL", r["control_id"], r["control_time_utc"], r["symbol"], r["copied_side"], r["execution_timeframe"]) for r in controls if r["case_id"] == cid)
        for kind, rid, stamp, symbol, side, tf in entries:
            t = epoch(stamp)
            values, availability = calculate(panels[symbol], panels["BTCUSDT"], t, side)
            row = dict(record_type=kind, case_id=cid, record_id=rid, symbol=symbol, side=side, execution_timeframe=tf, event_time_utc=utc(t), source_venue="Binance", source_instrument="USDT_PERPETUAL_PROXY", source_sha256=manifest["symbols"][symbol]["sha256"], btc_source_sha256=manifest["symbols"]["BTCUSDT"]["sha256"])
            for feature in FEATURES:
                row[feature] = "" if values[feature] is None else format(values[feature], ".15g")
                row[feature + "_max_input_close_utc"] = "" if availability[feature] is None else utc(availability[feature])
            row["max_input_close_utc"] = utc(max(x for x in availability.values() if x is not None)) if any(x is not None for x in availability.values()) else ""
            row["leakage_check"] = "PASS" if not row["max_input_close_utc"] or epoch(row["max_input_close_utc"]) <= t else "FAIL"
            assert row["leakage_check"] == "PASS"
            records.append(row)
    assert len(records) == 224
    write(PHASE / "features/point_in_time_features.csv", records, list(records[0]))
    definitions = [
        (FEATURES[0], "side*ln(last_completed_4h_close / 4_completed_4h_bars_prior_close)", "5 completed 4h bars"),
        (FEATURES[1], "side*(2*(last_15m_close-lowest_low_20)/(highest_high_20-lowest_low_20)-1)", "20 completed 15m bars"),
        (FEATURES[2], "-side*ln(last_15m_close / close_8_bars_prior)", "9 completed 15m bars"),
        (FEATURES[3], "range(last_8_completed_15m)/range(last_32_completed_15m)", "32 completed 15m bars"),
        (FEATURES[4], "sum(volume_last_8)/mean(sum(volume_each_8bar_block_for_20_prior_blocks))", "168 completed 15m bars"),
        (FEATURES[5], "side*ln(BTC_last_completed_4h_close / BTC_4_completed_4h_bars_prior_close)", "5 completed BTC 4h bars"),
    ]
    write(PHASE / "features/feature_dictionary.csv", [dict(feature=f, formula=formula, lookback=lookback, timestamp_rule="all component candle close_time <= record event_time; UTC close boundaries", provenance="frozen preregistration b9ec946") for f, formula, lookback in definitions], ["feature", "formula", "lookback", "timestamp_rule", "provenance"])
    missing = []
    for kind in ("CASE", "CONTROL", "ALL"):
        subset = records if kind == "ALL" else [r for r in records if r["record_type"] == kind]
        for f in FEATURES:
            absent = sum(r[f] == "" for r in subset)
            missing.append(dict(record_type=kind, feature=f, total=len(subset), present=len(subset)-absent, missing=absent, missing_rate=absent/len(subset)))
    write(PHASE / "diagnostics/missingness_report.csv", missing, list(missing[0]))
    print(json.dumps({"feature_rows": len(records), "case_rows": len(case_ids), "missing": {f: sum(r[f] == "" for r in records) for f in FEATURES}, "leakage_failures": sum(r["leakage_check"] != "PASS" for r in records)}, sort_keys=True))


if __name__ == "__main__":
    main()
