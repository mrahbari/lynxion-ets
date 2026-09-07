#!/usr/bin/env python3
"""Build a deterministic source/test manifest for the preregistered exit shadow."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ARTIFACT_PATHS = (
    "tasks/research/exit-policy-register-v1.md",
    "infrastructure/research/exit_policy_shadow.py",
    "infrastructure/research/exit_policy_shadow_input.py",
    "infrastructure/observability/entry_fee_evidence_extractor.py",
    "infrastructure/observability/fee_schedule_snapshot.py",
    "infrastructure/observability/terminal_evidence_extractor.py",
    "infrastructure/research/shadow_position_inputs.py",
    "infrastructure/research/shadow_friction_inputs.py",
    "infrastructure/research/paired_exit_outcome.py",
    "infrastructure/research/paired_exit_evaluator.py",
    "infrastructure/research/exit_shadow_coverage_gate.py",
    "infrastructure/research/exit_shadow_aggregate_protocol.py",
    "infrastructure/research/exit_shadow_aggregate_evaluator.py",
    "tests/unit/test_task0190_shadow_net_floor_math.py",
    "tests/unit/test_task0192_shadow_input_binding.py",
    "tests/unit/test_task0194_entry_fee_evidence.py",
    "tests/unit/test_task0195_fee_schedule_snapshot.py",
    "tests/unit/test_task0196_shadow_position_inputs.py",
    "tests/unit/test_task0199_shadow_friction_inputs.py",
    "tests/unit/test_task0200_paired_exit_outcome.py",
    "tests/unit/test_task0201_paired_exit_evaluator.py",
    "tests/unit/test_task0202_exit_shadow_coverage_gate.py",
    "tests/unit/test_task0203_exit_shadow_aggregate_protocol.py",
    "tests/unit/test_task0204_exit_shadow_aggregate_evaluator.py",
)


def build_manifest(root: Path) -> dict:
    artifacts = []
    for relative in ARTIFACT_PATHS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"required exit-shadow artifact missing: {relative}")
        raw = path.read_bytes()
        artifacts.append({
            "path": relative,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    canonical = json.dumps(artifacts, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "candidate": "EXIT_NET_FLOOR_12_5",
        "status": "EVALUATOR_FROZEN_OUTCOMES_UNOPENED",
        "artifacts": artifacts,
        "artifact_set_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.root)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
