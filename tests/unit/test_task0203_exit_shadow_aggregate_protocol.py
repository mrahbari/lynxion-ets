from copy import deepcopy

from infrastructure.research.exit_shadow_aggregate_protocol import (
    AGGREGATE_PROTOCOL,
    admit_aggregate_request,
)
from infrastructure.research.exit_shadow_coverage_gate import FROZEN_MINIMUMS


def coverage(ready=True, count=1):
    return {
        "status": "READY_TO_OPEN_AGGREGATES" if ready else "COLLECTING",
        "counts": {"paired_positions": count},
        "gates": {name: ready for name in FROZEN_MINIMUMS},
    }


def record(key="p1"):
    return {
        "position_key": key, "symbol": "BTCUSDT", "side": "LONG",
        "terminal_time_utc": "2026-09-07T00:00:00+00:00",
        "candidate_activated": True,
        "baseline_primary_net_roe_pct": 1.0, "candidate_primary_net_roe_pct": 2.0,
        "baseline_stress_net_roe_pct": 0.0, "candidate_stress_net_roe_pct": 1.0,
    }


def test_exact_protocol_is_admitted_without_exposing_metrics():
    result = admit_aggregate_request(coverage(), [record()], protocol=AGGREGATE_PROTOCOL)
    assert result["eligible"] is True
    assert result["metrics_exposed"] is False
    assert result["protocol"]["bootstrap_resamples"] == 10_000


def test_closed_coverage_gate_never_admits_economics():
    result = admit_aggregate_request(coverage(False), [record()], protocol=AGGREGATE_PROTOCOL)
    assert result == {"eligible": False, "reason": "minimum coverage gate is closed"}


def test_post_registration_protocol_change_fails_closed():
    changed = deepcopy(AGGREGATE_PROTOCOL)
    changed["bootstrap_seed"] += 1
    result = admit_aggregate_request(coverage(), [record()], protocol=changed)
    assert result["eligible"] is False


def test_record_count_schema_and_identity_must_be_exact():
    assert admit_aggregate_request(coverage(count=2), [record()], protocol=AGGREGATE_PROTOCOL)["eligible"] is False
    drifted = record()
    drifted["regime"] = "TREND"
    assert admit_aggregate_request(coverage(), [drifted], protocol=AGGREGATE_PROTOCOL)["eligible"] is False
    assert admit_aggregate_request(
        coverage(count=2), [record(), record()], protocol=AGGREGATE_PROTOCOL
    )["eligible"] is False
