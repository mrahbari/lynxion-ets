import base64
import gzip
import hashlib
import json
from pathlib import Path

from scripts.audit_microstructure_capture import audit


def test_audit_finalized_and_orphan_evidence(tmp_path: Path):
    root = tmp_path / "capture"
    raw = root / "raw" / "BTCUSDT"
    raw.mkdir(parents=True)
    activation = {"output_root": str(root), "start_utc_ns": 100, "stop_utc_ns": 200}
    activation_path = tmp_path / "activation.json"
    activation_path.write_text(json.dumps(activation))
    record = {"kind": "depth", "symbol": "BTCUSDT", "session": "epoch-1",
              "receipt_utc_ns": 150, "receipt_monotonic_ns": 2,
              "payload_b64": base64.b64encode(b'{"u":1}').decode()}
    path = raw / "one.jsonl.gz"
    with gzip.open(path, "wt") as handle:
        handle.write(json.dumps(record) + "\n")
    entry = {"path": str(path), "bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "records": 1}
    orphan = raw / "orphan.jsonl.gz"
    orphan.write_bytes(b"partial")
    orphan_entry = {"path": str(orphan), "bytes": orphan.stat().st_size,
                    "sha256": hashlib.sha256(orphan.read_bytes()).hexdigest()}
    manifest = {"activation": activation,
                "sessions": [{"symbol": "BTCUSDT", "session": "epoch-1", "files": [entry]}],
                "failures": [{"unfinalized_raw_chunks": [orphan_entry]}]}
    (root / "capture_manifest.json").write_text(json.dumps(manifest))

    result = audit(activation_path)
    assert result == {"integrity_ok": True, "finalized_files": 1,
                      "orphan_files": 1, "unlisted_files": [], "errors": []}

    manifest["sessions"][0]["files"][0]["records"] = 2
    (root / "capture_manifest.json").write_text(json.dumps(manifest))
    assert "finalized:records:one.jsonl.gz:1" in audit(activation_path)["errors"]


def test_audit_rejects_out_of_boundary_depth(tmp_path: Path):
    root = tmp_path / "capture"
    raw = root / "raw" / "ETHUSDT"
    raw.mkdir(parents=True)
    activation = {"output_root": str(root), "start_utc_ns": 100, "stop_utc_ns": 200}
    activation_path = tmp_path / "activation.json"
    activation_path.write_text(json.dumps(activation))
    path = raw / "one.jsonl.gz"
    with gzip.open(path, "wt") as handle:
        handle.write(json.dumps({"kind": "depth", "symbol": "ETHUSDT", "session": "epoch-1",
                                 "receipt_utc_ns": 200, "payload_b64": None}) + "\n")
    entry = {"path": str(path), "bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "records": 1}
    (root / "capture_manifest.json").write_text(json.dumps({
        "activation": activation,
        "sessions": [{"symbol": "ETHUSDT", "session": "epoch-1", "files": [entry]}],
        "failures": []}))
    assert "depth_outside_boundary" in str(audit(activation_path)["errors"])
