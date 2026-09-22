"""Build provenance-only Phase 3A cases after preregistration freeze."""
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PHASE = ROOT / "research/external_signal_study/phase3_point_in_time"
V2 = ROOT / "tasks/1k-event/research/external_signal_study/temporal_forensic_v2/extracted/temporal_signals.csv"
SPEC = PHASE / "preregistration/PHASE3_RESEARCH_SPEC.md"
EXPECTED = "96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193"


def read(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def main():
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest() == EXPECTED, "preregistration changed"
    rows = [r for r in read(V2) if r["strategy_label"] == "1K_EVENT"]
    audit = {r["signal_id"]: r for r in read(PHASE / "diagnostics/point_in_time_audit.csv")}
    assert len(rows) == len(audit) == 100
    attribution, cases = [], []
    for r in rows:
        sid, t = r["signal_id"], r["published_at"]
        if "2026-08-16T00:00:00" <= t < "2026-09-13T21:55:16":
            engine, kind, confidence, basis = "HMT", "INTERVAL_LEVEL_ENGINE_ATTRIBUTION", "MEDIUM", "raw_aug_msg_596_past_month_except_last_two"
        elif sid in ("SIG-000300", "SIG-000301"):
            engine, kind, confidence, basis = "TFS", "DIRECT_OPERATOR_DISCLOSURE", "HIGH", "raw_aug_msg_594_reply_to_580_and_msg_596"
        else:
            engine, kind, confidence, basis = "UNKNOWN", "UNKNOWN_ENGINE", "UNKNOWN", "no_defensible_raw_attribution"
        symbol = "LDOUSDT" if sid == "SIG-000300" else r["symbol_normalized"]
        tf = "15m" if sid == "SIG-000300" else r["timeframe"]
        correction = "raw_aug_msg_579_580_photo_257" if sid == "SIG-000300" else "NONE"
        attribution.append(dict(signal_id=sid, engine_attribution=engine, attribution_type=kind, confidence=confidence, basis=basis))
        cases.append(dict(signal_id=sid, symbol=symbol, side=r["side"], signal_timestamp_utc=t, execution_timeframe=tf, observed_generation="1K_EVENT", engine_attribution=engine, attribution_type=kind, attribution_confidence=confidence, decision_origin=r["decision_origin"], source_evidence_ids=r["source_evidence_ids"], first_message_anchor="V2_FIRST_MESSAGE", derived_correction=correction, pit_core_usable=audit[sid]["core_pit_usable"], primary_hmt_eligible="YES" if engine == "HMT" and tf in ("15m", "1h", "4h", "1d") else "NO"))
    assert sum(x["engine_attribution"] == "HMT" for x in cases) == 64
    assert sum(x["engine_attribution"] == "TFS" for x in cases) == 2
    assert sum(x["engine_attribution"] == "UNKNOWN" for x in cases) == 34
    assert sum(x["primary_hmt_eligible"] == "YES" for x in cases) == 58
    write(PHASE / "extracted/engine_attribution.csv", attribution)
    write(PHASE / "extracted/phase3_cases.csv", cases)
    print("100 cases; 64 interval HMT, 2 retrospective TFS, 34 unknown; 58 primary HMT eligible")


if __name__ == "__main__":
    main()
