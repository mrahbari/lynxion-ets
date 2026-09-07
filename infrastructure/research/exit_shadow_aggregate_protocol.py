"""Frozen aggregate evaluation interface, sealed behind the coverage gate."""

from __future__ import annotations

from typing import Any

from infrastructure.research.exit_shadow_coverage_gate import FROZEN_MINIMUMS, shadow_coverage_gate


AGGREGATE_PROTOCOL = {
    "bootstrap_seed": 20260907,
    "bootstrap_resamples": 10_000,
    "bootstrap_cluster": "POSITION_KEY",
    "confidence_level": 0.95,
    "chronological_folds": 4,
    "fold_method": "CONTIGUOUS_EQUAL_COUNT_TERMINAL_TIME",
    "profit_factor_minimum": 1.10,
    "expected_shortfall_tail_fraction": 0.05,
    "tail_relative_worsening_limit": 0.10,
    "top_symbol_exclusion_metric": "PAIRED_PRIMARY_CONTRIBUTION",
    "drawdown_method": "EQUAL_WEIGHT_CUMULATIVE_NET_RETURN_PEAK_TO_TROUGH",
}

AGGREGATE_RECORD_FIELDS = {
    "position_key", "symbol", "side", "terminal_time_utc", "candidate_activated",
    "baseline_primary_net_roe_pct", "candidate_primary_net_roe_pct",
    "baseline_stress_net_roe_pct", "candidate_stress_net_roe_pct",
}


def admit_aggregate_request(
    coverage: dict[str, Any], records: list[dict[str, Any]], *, protocol: dict[str, Any]
) -> dict[str, Any]:
    """Admit an aggregate request without calculating or returning any metric."""
    gates = coverage.get("gates", {})
    if (
        coverage.get("status") != "READY_TO_OPEN_AGGREGATES"
        or set(gates) != set(FROZEN_MINIMUMS)
        or not all(gates.values())
    ):
        return {"eligible": False, "reason": "minimum coverage gate is closed"}
    if protocol != AGGREGATE_PROTOCOL:
        return {"eligible": False, "reason": "aggregate protocol differs from frozen contract"}
    if not isinstance(records, list) or len(records) != coverage.get("counts", {}).get("paired_positions"):
        return {"eligible": False, "reason": "aggregate record count mismatch"}
    identities = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != AGGREGATE_RECORD_FIELDS:
            return {"eligible": False, "reason": "aggregate record schema mismatch"}
        key = record.get("position_key")
        if not isinstance(key, str) or not key or key in identities:
            return {"eligible": False, "reason": "aggregate position identity invalid"}
        identities.add(key)
    metadata = [{
        key: record[key] for key in (
            "position_key", "symbol", "side", "terminal_time_utc", "candidate_activated",
        )
    } for record in records]
    derived = shadow_coverage_gate(metadata)
    if (
        derived["membership_sha256"] != coverage.get("membership_sha256")
        or derived["counts"] != coverage.get("counts")
        or derived["gates"] != gates
    ):
        return {"eligible": False, "reason": "aggregate membership differs from coverage evidence"}
    return {
        "eligible": True,
        "reason": None,
        "record_count": len(records),
        "protocol": dict(AGGREGATE_PROTOCOL),
        "metrics_exposed": False,
    }
