#!/usr/bin/env python3
"""Verify the frozen public BingX perpetual fee snapshot without broker access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.observability.fee_schedule_snapshot import admit_exit_fee_schedule


DEFAULT_SNAPSHOT = Path(
    "data/research/exit_shadow/bingx_perpetual_fee_snapshot-20260912T164438Z.json"
)


def verify(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot payload is missing")
    if snapshot.get("source_scope") != (
        "PUBLIC_STANDARD_BASE_RATE; ACCOUNT_OR_VIP_DISCOUNTS_NOT_ASSUMED"
    ):
        raise ValueError("fee snapshot scope is not conservative public base")
    if snapshot.get("maker_fee_rate") != "0.0002":
        raise ValueError("BingX public maker rate drift")
    result = admit_exit_fee_schedule(
        snapshot,
        activation_utc=str(payload.get("activation_not_before_utc") or ""),
        exchange="BINGX",
        market="PERPETUAL",
    )
    if not result.get("eligible"):
        raise ValueError(str(result.get("exclusion_reason") or "fee snapshot rejected"))
    if result["snapshot_sha256"] != payload.get("expected_snapshot_sha256"):
        raise ValueError("fee snapshot canonical hash mismatch")
    return {
        "exchange": "BINGX",
        "market": "PERPETUAL",
        "account_tier": result["account_tier"],
        "expected_exit_fee_price_pct": result["expected_exit_fee_price_pct"],
        "snapshot_sha256": result["snapshot_sha256"],
        "eligible_for_activation_not_before_utc": payload["activation_not_before_utc"],
        "authorizes_broker_access": False,
        "authorizes_runtime": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    args = parser.parse_args()
    payload = json.loads((ROOT / args.snapshot).read_text(encoding="utf-8"))
    print(json.dumps(verify(payload), sort_keys=True))


if __name__ == "__main__":
    main()
