from copy import deepcopy
from datetime import datetime, timedelta, timezone

from infrastructure.research.exit_shadow_aggregate_protocol import (
    AGGREGATE_PROTOCOL,
    admit_aggregate_request,
)
from infrastructure.research.exit_shadow_coverage_gate import FROZEN_MINIMUMS, shadow_coverage_gate


def record(index=0):
    return {
        "position_key": f"p{index}", "symbol": f"S{index % 5}USDT",
        "side": "LONG" if index < 50 else "SHORT",
        "terminal_time_utc": (
            datetime(2026, 1, 5, tzinfo=timezone.utc) + timedelta(weeks=index % 8)
        ).isoformat(),
        "candidate_activated": index < 30,
        "baseline_primary_net_roe_pct": 1.0, "candidate_primary_net_roe_pct": 2.0,
        "baseline_stress_net_roe_pct": 0.0, "candidate_stress_net_roe_pct": 1.0,
    }


def records():
    return [record(index) for index in range(100)]


def coverage(rows=None, ready=True):
    if not ready:
        return {
            "status": "COLLECTING", "counts": {"paired_positions": 0},
            "gates": {name: False for name in FROZEN_MINIMUMS},
            "membership_sha256": "unused-while-closed",
        }
    rows = rows or records()
    return shadow_coverage_gate([{key: row[key] for key in (
            "position_key", "symbol", "side", "terminal_time_utc", "candidate_activated",
        )} for row in rows])


def test_exact_protocol_is_admitted_without_exposing_metrics():
    rows = records()
    result = admit_aggregate_request(coverage(rows), rows, protocol=AGGREGATE_PROTOCOL)
    assert result["eligible"] is True
    assert result["metrics_exposed"] is False
    assert result["protocol"]["bootstrap_resamples"] == 10_000


def test_closed_coverage_gate_never_admits_economics():
    result = admit_aggregate_request(coverage(ready=False), [record()], protocol=AGGREGATE_PROTOCOL)
    assert result == {"eligible": False, "reason": "minimum coverage gate is closed"}


def test_post_registration_protocol_change_fails_closed():
    changed = deepcopy(AGGREGATE_PROTOCOL)
    changed["bootstrap_seed"] += 1
    rows = records()
    result = admit_aggregate_request(coverage(rows), rows, protocol=changed)
    assert result["eligible"] is False


def test_record_count_schema_and_identity_must_be_exact():
    rows = records()
    assert admit_aggregate_request(coverage(rows), rows[:-1], protocol=AGGREGATE_PROTOCOL)["eligible"] is False
    drifted = deepcopy(rows)
    drifted[0]["regime"] = "TREND"
    assert admit_aggregate_request(coverage(rows), drifted, protocol=AGGREGATE_PROTOCOL)["eligible"] is False
    duplicated = deepcopy(rows)
    duplicated[-1]["position_key"] = duplicated[0]["position_key"]
    assert admit_aggregate_request(
        coverage(rows), duplicated, protocol=AGGREGATE_PROTOCOL
    )["eligible"] is False


def test_economic_membership_must_match_coverage_hash():
    rows = records()
    evidence = coverage(rows)
    changed = deepcopy(rows)
    changed[0]["symbol"] = "OTHERUSDT"
    result = admit_aggregate_request(evidence, changed, protocol=AGGREGATE_PROTOCOL)
    assert result["reason"] == "aggregate membership differs from coverage evidence"
