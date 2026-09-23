"""Frozen Phase 3A Family-A matching using timestamps only, never price/outcome values."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PHASE = ROOT / "research/external_signal_study/phase3_point_in_time"
DATA = ROOT / "data/research/phase3_point_in_time/binance_futures_15m"
SPEC_HASH = "96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193"
BAR_SECONDS = 900
BAR_CLOSE_OFFSET = 899
LOOKBACK_BARS = 168
EXCLUSION_SECONDS = 6 * 3600


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, records, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def utc_epoch(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc).timestamp())


def utc_text(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def last_closed_open(epoch):
    """A bar stamped at its OPEN is usable only after OPEN+899 seconds."""
    return ((epoch - BAR_CLOSE_OFFSET) // BAR_SECONDS) * BAR_SECONDS


def has_full_lookback(epoch, opens):
    last = last_closed_open(epoch)
    return all(last - n * BAR_SECONDS in opens for n in range(LOOKBACK_BARS))


def load_open_times(path, expected_sha):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha, f"source changed: {path}"
    with path.open(encoding="utf-8") as handle:
        assert handle.readline().strip() == "timestamp,open,high,low,close,volume"
        return {int(line.split(",", 1)[0]) for line in handle if line.strip()}


def main():
    spec = PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md"
    assert hashlib.sha256(spec.read_bytes()).hexdigest() == SPEC_HASH
    manifest = json.loads((PHASE / "manifests/phase3_proxy_source_manifest.json").read_text())
    assert manifest["preregistration_sha256"] == SPEC_HASH
    cases = read_csv(PHASE / "extracted/phase3_cases.csv")
    primary = [c for c in cases if c["primary_hmt_eligible"] == "YES"]
    assert len(primary) == 58
    evidence_times = defaultdict(list)
    for c in cases:
        evidence_times[c["symbol"]].append(utc_epoch(c["signal_timestamp_utc"]))
    opens = {}
    for symbol, item in manifest["symbols"].items():
        if item["status"] == "COMPLETE_VALIDATED":
            opens[symbol] = load_open_times(DATA / f"{symbol}.csv", item["sha256"])
    assert "BTCUSDT" in opens

    controls, diagnostics, leakage = [], [], []
    for case in primary:
        sid, symbol = case["signal_id"], case["symbol"]
        t = utc_epoch(case["signal_timestamp_utc"])
        item = manifest["symbols"].get(symbol)
        status = "UNVERIFIED_SOURCE"
        candidates = []
        selected = []
        if item and item["status"] == "COMPLETE_VALIDATED":
            if has_full_lookback(t, opens[symbol]) and has_full_lookback(t, opens["BTCUSDT"]):
                status = "MATCHED"
                case_close = last_closed_open(t) + BAR_CLOSE_OFFSET
                assert case_close <= t
                leakage.append(dict(record_type="CASE", case_id=sid, record_id=sid, event_time_utc=utc_text(t), max_input_close_utc=utc_text(case_close), passes_close_le_t="YES"))
                dt = datetime.fromtimestamp(t, timezone.utc)
                week_start = dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=dt.weekday())
                start = int(week_start.timestamp())
                end = start + 7 * 86400
                target_block = dt.hour // 4
                for control_t in range(start, end, BAR_SECONDS):
                    control_dt = datetime.fromtimestamp(control_t, timezone.utc)
                    if control_dt.hour // 4 != target_block or control_t == t:
                        continue
                    if any(abs(control_t - signal_t) <= EXCLUSION_SECONDS for signal_t in evidence_times[symbol]):
                        continue
                    if not (has_full_lookback(control_t, opens[symbol]) and has_full_lookback(control_t, opens["BTCUSDT"])):
                        continue
                    stamp = utc_text(control_t)
                    h = hashlib.sha256(f"phase3a-v1|{sid}|{stamp}".encode()).hexdigest()
                    candidates.append((h, control_t, stamp))
                seen_dates = set()
                for h, control_t, stamp in sorted(candidates):
                    date = stamp[:10]
                    if date in seen_dates:
                        continue
                    seen_dates.add(date)
                    selected.append((h, control_t, stamp))
                    if len(selected) == 3:
                        break
                if len(selected) < 2:
                    status = "UNMATCHED_FEWER_THAN_TWO_CONTROLS"
            else:
                status = "MISSING_PRE_T_LOOKBACK"
        for rank, (h, control_t, stamp) in enumerate(selected, 1):
            close = last_closed_open(control_t) + BAR_CLOSE_OFFSET
            assert close <= control_t
            cid = f"{sid}-A{rank}"
            controls.append(dict(case_id=sid, control_id=cid, symbol=symbol, copied_side=case["side"], execution_timeframe=case["execution_timeframe"], case_time_utc=utc_text(t), control_time_utc=stamp, control_date_utc=stamp[:10], selection_sha256=h, source_sha256=item["sha256"], max_input_close_utc=utc_text(close), matched_case="YES" if len(selected) >= 2 else "NO"))
            leakage.append(dict(record_type="CONTROL", case_id=sid, record_id=cid, event_time_utc=stamp, max_input_close_utc=utc_text(close), passes_close_le_t="YES"))
        diagnostics.append(dict(case_id=sid, symbol=symbol, side=case["side"], case_time_utc=utc_text(t), execution_timeframe=case["execution_timeframe"], source_status=item["status"] if item else "MISSING", candidate_grid_count=len(candidates), selected_controls=len(selected), selected_distinct_utc_dates=len({x[2][:10] for x in selected}), matching_status=status))
    write_csv(PHASE / "controls/matched_controls.csv", controls, list(controls[0]))
    write_csv(PHASE / "controls/control_diagnostics.csv", diagnostics, list(diagnostics[0]))
    write_csv(PHASE / "diagnostics/leakage_audit.csv", leakage, list(leakage[0]))
    counts = Counter(d["matching_status"] for d in diagnostics)
    print(json.dumps({"nominal_cases": len(primary), "controls": len(controls), "matching_status": dict(counts), "matched_days": len({d["case_time_utc"][:10] for d in diagnostics if d["matching_status"] == "MATCHED"}), "leakage_records": len(leakage)}, sort_keys=True))


if __name__ == "__main__":
    main()
