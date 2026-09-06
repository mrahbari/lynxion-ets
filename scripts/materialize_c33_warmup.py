#!/usr/bin/env python3
"""Materialize frozen C-33 eligible bucket inputs without calculating signals or outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from scripts.audit_c33_collection import audit
    from scripts.collect_c33_liquidation_events import SYMBOLS
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from audit_c33_collection import audit
    from collect_c33_liquidation_events import SYMBOLS


def materialize(manifest_path: Path, events_path: Path | None = None) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = events_path or Path(manifest["output"])
    if events_path is not None and str(events_path) != str(manifest["output"]):
        raise ValueError("event path differs from the activation manifest")
    event_bytes = source.read_bytes()
    audited = audit(manifest_path, source, event_bytes=event_bytes)
    totals = {
        (row["bucket_start_ms"], row["symbol"], row["side"]): row
        for row in audited["eligible_liquidation_totals"]
    }
    buckets = []
    for bucket_start in audited["eligible_bucket_starts_ms"]:
        for symbol in SYMBOLS:
            buy = totals.get((bucket_start, symbol, "BUY"), {})
            sell = totals.get((bucket_start, symbol, "SELL"), {})
            buckets.append({
                "bucket_start_ms": bucket_start,
                "bucket_end_ms": bucket_start + 300_000,
                "symbol": symbol,
                "observed_buy_count": int(buy.get("observed_count", 0)),
                "observed_buy_notional": float(buy.get("observed_notional", 0.0)),
                "observed_sell_count": int(sell.get("observed_count", 0)),
                "observed_sell_notional": float(sell.get("observed_notional", 0.0)),
            })
    return {
        "schema_version": 1,
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "activation_boundary": audited["activation_boundary"],
        "source_sha256": hashlib.sha256(event_bytes).hexdigest(),
        "source_record_counts": audited["record_counts"],
        "eligible_bucket_count": audited["eligible_completed_bucket_count"],
        "rows": buckets,
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation-manifest", type=Path, default=Path("data/research/c33/activation_manifest.json"))
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = materialize(args.activation_manifest, args.events)
    if args.output:
        write_atomic(args.output, result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
