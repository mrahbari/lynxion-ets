from scripts.evaluate_c35_aggregate import evaluate, evaluate_verified_outcomes


def _outcomes(value=0.01, stress=0.008):
    base = 1789088400
    rows = []
    for week in range(8):
        for index in range(30):
            offset = week * 7 * 86400 + index * 3600
            rows.append({
                "signal_key": f"S{index % 6}:{week}:{index}",
                "entry_open_time": base + offset,
                "exit_open_time": base + offset + 7200,
                "side": "LONG" if index < 15 else "SHORT",
                "symbol": f"S{index % 6}",
                "net_return_primary_0_30pct": value,
                "net_return_stress_0_50pct": stress,
            })
    return rows


def test_live_empty_cohort_stays_sealed_without_economics():
    result = evaluate([], [], [], [])
    assert result["aggregate_economics"] == "SEALED"
    assert "expectancy_primary" not in result


def test_all_frozen_economic_gates_can_keep():
    result = evaluate_verified_outcomes(_outcomes(), bootstrap_samples=100)
    assert result["verdict"] == "KEEP_FOR_SEPARATE_VST_REVIEW"
    assert all(result["gates"].values())


def test_any_completed_economic_failure_rejects():
    rows = _outcomes()
    for row in rows:
        if row["side"] == "SHORT":
            row["net_return_primary_0_30pct"] = -0.02
            row["net_return_stress_0_50pct"] = -0.022
    result = evaluate_verified_outcomes(rows, bootstrap_samples=100)
    assert result["verdict"] == "REJECT"
    assert not result["gates"]["both_sides_positive"]
