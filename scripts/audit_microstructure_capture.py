"""Read-only raw-file integrity check for a frozen microstructure capture.

This checks evidence storage, not book reconstruction, coverage, or a verdict.
"""

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path


def audit(activation_path: Path) -> dict:
    activation = json.loads(activation_path.read_text())
    root = Path(activation["output_root"]).resolve()
    manifest = json.loads((root / "capture_manifest.json").read_text())
    errors: list[str] = []
    if manifest.get("activation") != activation:
        errors.append("activation_mismatch")
    finalized = 0
    orphans = 0
    checked: set[Path] = set()

    def check_path(entry: dict, label: str) -> Path | None:
        try:
            path = Path(entry["path"]).resolve(strict=True)
            if not path.is_relative_to(root / "raw") or not path.is_file():
                raise ValueError("outside_raw_root")
            checked.add(path)
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            if path.stat().st_size != entry["bytes"]:
                errors.append(f"{label}:size:{path.name}")
            if digest.hexdigest() != entry["sha256"]:
                errors.append(f"{label}:sha256:{path.name}")
            return path
        except (OSError, KeyError, ValueError) as exc:
            errors.append(f"{label}:path:{entry.get('path', '?')}:{exc}")
            return None

    for session in manifest.get("sessions", []):
        for entry in session.get("files", []):
            finalized += 1
            path = check_path(entry, "finalized")
            if path is None:
                continue
            try:
                count = 0
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    for line in handle:
                        record = json.loads(line)
                        count += 1
                        if record["symbol"] != session["symbol"] or record["session"] != session["session"]:
                            raise ValueError("envelope_identity")
                        if record["kind"] not in {"depth", "snapshot", "collector_error"}:
                            raise ValueError("envelope_kind")
                        payload = record["payload_b64"]
                        if payload is not None:
                            base64.b64decode(payload, validate=True)
                        if record["kind"] == "depth" and not (
                            activation["start_utc_ns"] <= record["receipt_utc_ns"] < activation["stop_utc_ns"]
                        ):
                            raise ValueError("depth_outside_boundary")
                if count != entry["records"]:
                    errors.append(f"finalized:records:{path.name}:{count}")
            except (OSError, EOFError, UnicodeError, KeyError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"finalized:content:{path.name}:{exc}")

    for failure in manifest.get("failures", []):
        for entry in failure.get("unfinalized_raw_chunks", []):
            orphans += 1
            check_path(entry, "orphan")  # Never promote an orphan into valid coverage.

    raw_root = root / "raw"
    unlisted = sorted(str(path) for path in raw_root.rglob("*.jsonl.gz") if path.resolve() not in checked) if raw_root.exists() else []
    return {"integrity_ok": not errors, "finalized_files": finalized,
            "orphan_files": orphans, "unlisted_files": unlisted, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("activation", type=Path)
    result = audit(parser.parse_args().activation)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["integrity_ok"] else 1)
