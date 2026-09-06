import base64
import hashlib
import json

import pytest

from scripts.audit_c33_collection import InvalidC33Ledger, audit
from scripts.collect_c33_liquidation_events import BOUNDARY, SYMBOLS


def raw_fields(payload):
    raw = json.dumps(payload).encode()
    return {"raw_base64": base64.b64encode(raw).decode(), "raw_sha256": hashlib.sha256(raw).hexdigest()}


def fixture(tmp_path, *, missing_heartbeat=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    activation = BOUNDARY + 100
    start = ((activation * 1000) // 300_000 + 1) * 300_000
    output = tmp_path / "events.jsonl"
    manifest = tmp_path / "activation.json"
    manifest.write_text(json.dumps({
        "candidate": "C-33", "protocol": "edge-candidate-register-v32",
        "candidate_boundary": BOUNDARY, "activation_boundary": activation,
        "collector_commit": "abc", "output": str(output), "historical_import_allowed": False,
    }))
    session = "run"
    rows = [{"record_type": "session", "key": "session:run:STARTED", "session_id": session,
             "state": "STARTED", "timestamp_ms": (activation + 1) * 1000, "receipt_monotonic_ns": 1}]
    for offset in range(5):
        minute = start + offset * 60_000
        if not (missing_heartbeat and offset == 2):
            rows.append({"record_type": "heartbeat", "key": f"h:{minute}", "session_id": session,
                         "server_time_ms": minute + 1, "minute_ms": minute,
                         "receipt_monotonic_ns": 2, **raw_fields({"serverTime": minute + 1})})
        for symbol in SYMBOLS:
            rows.append({"record_type": "kline_close", "key": f"k:{symbol}:{minute}",
                         "session_id": session, "symbol": symbol, "open_time_ms": minute,
                         "close_time_ms": minute + 59_999, "event_time_ms": minute + 60_000,
                         "receipt_monotonic_ns": 3, **raw_fields({"k": symbol, "t": minute})})
    rows.append({"record_type": "liquidation", "key": "l:1", "session_id": session,
                 "symbol": "BTCUSDT", "side": "SELL", "trade_time_ms": start + 10,
                 "event_time_ms": start + 11, "observed_notional": 125.0,
                 "receipt_monotonic_ns": 4, **raw_fields({"l": 1})})
    output.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return manifest, output, start


def test_audit_marks_only_complete_liveness_bucket_eligible(tmp_path):
    manifest, _, start = fixture(tmp_path)
    result = audit(manifest)
    assert result["verdict"] == "COLLECTING"
    assert result["eligible_bucket_starts_ms"] == [start]
    assert result["eligible_liquidation_totals"] == [{
        "bucket_start_ms": start, "symbol": "BTCUSDT", "side": "SELL",
        "observed_count": 1, "observed_notional": 125.0,
    }]


def test_missing_heartbeat_makes_bucket_missing_not_zero(tmp_path):
    manifest, _, _ = fixture(tmp_path, missing_heartbeat=True)
    result = audit(manifest)
    assert result["eligible_completed_bucket_count"] == 0
    assert result["ineligible_completed_bucket_reasons"] == {"heartbeat": 1}
    assert result["eligible_liquidation_totals"] == []


def test_duplicate_or_modified_raw_record_fails_closed(tmp_path):
    manifest, output, _ = fixture(tmp_path)
    rows = output.read_text().splitlines()
    output.write_text("\n".join(rows + [rows[-1]]) + "\n")
    with pytest.raises(InvalidC33Ledger, match="duplicate"):
        audit(manifest)

    manifest, output, _ = fixture(tmp_path / "other")
    rows = output.read_text().splitlines()
    changed = json.loads(rows[-1])
    changed["raw_sha256"] = "0" * 64
    rows[-1] = json.dumps(changed)
    output.write_text("\n".join(rows) + "\n")
    with pytest.raises(InvalidC33Ledger, match="SHA-256"):
        audit(manifest)


def test_pre_activation_record_fails_closed(tmp_path):
    manifest, output, _ = fixture(tmp_path)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    rows[0]["timestamp_ms"] = (BOUNDARY + 100) * 1000
    output.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(InvalidC33Ledger, match="activation boundary"):
        audit(manifest)
