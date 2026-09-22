"""Read-only Phase 3A-0 provenance audit. Never opens market outcomes."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
UPSTREAM = ROOT / "tasks/1k-event/research/external_signal_study"
V2 = UPSTREAM / "temporal_forensic_v2"
RAW = Path("/Users/mojtaba.rahbari/Desktop/orders-1k-event")
OUT = ROOT / "research/external_signal_study/phase3_point_in_time"


def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path, data, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def ids(value):
    return [x.strip() for x in str(value or "").split(";") if x.strip() and x.strip() != "NONE"]


def main():
    inputs = [p for p in UPSTREAM.rglob("*") if p.is_file() and p.suffix != ".pyc" and p.name != ".DS_Store"]
    inputs += [RAW / "jan-jul/result.json", RAW / "aug/result.json", RAW / "research/external_signal_study/cache/image_features.json"]
    inputs += list((RAW / "jan-jul/photos").glob("*")) + list((RAW / "aug/photos").glob("*"))
    inventory = []
    for p in sorted(set(inputs)):
        if not p.is_file():
            continue
        rel = str(p.relative_to(RAW)) if p.is_relative_to(RAW) else str(p.relative_to(ROOT))
        count = ""
        if p.suffix == ".csv":
            count = len(rows(p))
        elif p.suffix == ".jsonl":
            count = sum(1 for _ in p.open(encoding="utf-8"))
        elif p.name == "result.json":
            count = len(json.loads(p.read_text(encoding="utf-8"))["messages"])
        inventory.append(dict(source="RAW" if p.is_relative_to(RAW) else "PASS1_V2", path=rel, bytes=p.stat().st_size, records=count, sha256=digest(p)))
    write_csv(OUT / "manifests/upstream_inventory.csv", inventory, ["source", "path", "bytes", "records", "sha256"])

    manifest = rows(V2 / "manifests/v2_evidence_manifest.csv")
    evidence = {r["evidence_id"]: r for r in manifest}
    signals = [r for r in rows(V2 / "extracted/temporal_signals.csv") if r["strategy_label"] == "1K_EVENT"]
    raw_messages = {}
    for rel in ("jan-jul/result.json", "aug/result.json"):
        for m in json.loads((RAW / rel).read_text(encoding="utf-8"))["messages"]:
            raw_messages[(rel, str(m["id"]))] = m
    assert len(signals) == 100 and len(manifest) == 2051
    lineage = []
    audit = []
    missing = []
    for s in signals:
        sid, t = s["signal_id"], s["published_at"]
        links = ids(s["source_evidence_ids"])
        counts = Counter()
        for eid in links:
            e = evidence.get(eid)
            if e is None:
                missing.append((sid, eid))
                continue
            raw = raw_messages.get((e["source_file"], e["source_message_id"]))
            raw_t = raw.get("date") if raw else None
            if raw_t != e["published_at"]:
                missing.append((sid, eid, "timestamp_mismatch"))
            relation = "PRE" if e["published_at"] < t else "AT" if e["published_at"] == t else "POST"
            counts[relation] += 1
            lineage.append(dict(signal_id=sid, signal_timestamp=t, evidence_id=eid, source_file=e["source_file"], source_message_id=e["source_message_id"], evidence_timestamp=e["published_at"], relation=relation, phase3a_feature_eligible="YES" if relation != "POST" else "NO_QUARANTINED", raw_reply_to_message_id=raw.get("reply_to_message_id", "") if raw else "MISSING"))
        metadata = bool(t and s["symbol_normalized"] not in ("", "UNKNOWN") and s["side"] in ("LONG", "SHORT"))
        timely = counts["PRE"] + counts["AT"] > 0
        tf = s["timeframe"] not in ("", "UNKNOWN")
        audit.append(dict(signal_id=sid, signal_timestamp=t, symbol=s["symbol_normalized"], side=s["side"], timeframe=s["timeframe"], evidence_ids=";".join(links), pre_count=counts["PRE"], at_count=counts["AT"], post_count=counts["POST"], core_pit_usable="YES" if metadata and timely else "NO", timeframe_pit_usable="YES" if metadata and timely and tf else "NO", engine_attribution="UNDETERMINED_FOR_FUTURE_TEST"))
    assert not missing, missing
    write_csv(OUT / "extracted/signal_evidence_lineage.csv", lineage, list(lineage[0]))
    write_csv(OUT / "diagnostics/point_in_time_audit.csv", audit, list(audit[0]))
    print(json.dumps({"inventory": len(inventory), "raw_photos": sum(x["source"] == "RAW" and "/photos/" in x["path"] for x in inventory), "signals": len(audit), "core_usable": sum(x["core_pit_usable"] == "YES" for x in audit), "timeframe_usable": sum(x["timeframe_pit_usable"] == "YES" for x in audit), "relations": dict(Counter(x["relation"] for x in lineage)), "post_signal_cases": sum(int(x["post_count"]) > 0 for x in audit)}, sort_keys=True))


if __name__ == "__main__":
    main()
