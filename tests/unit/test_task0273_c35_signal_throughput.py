from scripts.check_c35_signal_throughput import throughput


def _decisions(count):
    return {index * 3600: {} for index in range(count)}


def test_zero_signal_rate_has_no_false_projection():
    result = throughput(_decisions(35), [])
    assert result["signals_per_day"] == 0
    assert result["projected_days_to_240_at_observed_rate"] is None
    assert not result["first_rate_checkpoint_due"]


def test_projection_uses_verified_hourly_decisions_not_wall_clock():
    events = [{"kind": "SIGNAL"}, {"kind": "SIGNAL"}]
    result = throughput(_decisions(48), events)
    assert result["signals_per_day"] == 1
    assert result["projected_days_to_240_at_observed_rate"] == 240


def test_first_rate_checkpoint_is_one_week_of_decisions():
    result = throughput(_decisions(168), [])
    assert result["first_rate_checkpoint_due"]
    assert result["next_rate_checkpoint_decisions"] is None
    assert result["aggregate_economics"] == "SEALED"
