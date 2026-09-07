from infrastructure.research.exit_shadow_aggregate_evaluator import evaluate_shadow_aggregates
from infrastructure.research.exit_shadow_coverage_gate import shadow_coverage_gate


def records(delta=1.0):
    rows = []
    for index in range(100):
        baseline = 1.0
        rows.append({
            "position_key": f"p{index}", "symbol": f"S{index % 5}USDT",
            "side": "LONG" if index < 50 else "SHORT",
            "terminal_time_utc": f"2026-{1 + index // 48:02d}-{1 + (index % 24):02d}T00:00:00+00:00",
            "candidate_activated": index < 30,
            "baseline_primary_net_roe_pct": baseline,
            "candidate_primary_net_roe_pct": baseline + delta,
            "baseline_stress_net_roe_pct": baseline - 1.0,
            "candidate_stress_net_roe_pct": baseline - 1.0 + delta,
        })
    return rows


def metadata(rows):
    return [{key: row[key] for key in (
        "position_key", "symbol", "side", "terminal_time_utc", "candidate_activated"
    )} for row in rows]


def test_all_synthetic_frozen_gates_keep_candidate_for_separate_review():
    rows = records()
    result = evaluate_shadow_aggregates(shadow_coverage_gate(metadata(rows)), rows)
    assert result["verdict"] == "KEEP_FOR_SEPARATE_DEPLOYMENT_REVIEW"
    assert result["metrics"]["paired_mean_delta"] == 1.0
    assert result["metrics"]["bootstrap_ci_lower"] == 1.0


def test_failed_economic_gate_rejects_without_retuning():
    rows = records(delta=-1.0)
    result = evaluate_shadow_aggregates(shadow_coverage_gate(metadata(rows)), rows)
    assert result["verdict"] == "REJECT"
    assert result["gates"]["paired_mean_improvement"] is False


def test_closed_coverage_returns_collecting_before_economic_access():
    rows = records()[:99]
    for row in rows:
        row["candidate_primary_net_roe_pct"] = object()
    result = evaluate_shadow_aggregates(shadow_coverage_gate(metadata(rows)), rows)
    assert result == {
        "verdict": "COLLECTING", "reason": "minimum coverage gate is closed", "metrics": None,
    }
