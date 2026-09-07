from copy import deepcopy

from infrastructure.observability.fee_schedule_snapshot import admit_exit_fee_schedule


def snapshot(**updates):
    value = {
        "exchange": "BINGX",
        "market": "PERPETUAL",
        "account_tier": "STANDARD",
        "source": "BROKER_ACCOUNT_FEE_SCHEDULE",
        "captured_at_utc": "2026-09-07T00:00:00+00:00",
        "effective_at_utc": "2026-09-01T00:00:00+00:00",
        "taker_fee_rate": "0.0005",
    }
    value.update(updates)
    return value


def admit(value):
    return admit_exit_fee_schedule(
        value,
        activation_utc="2026-09-07T00:01:00+00:00",
        exchange="bingx",
        market="perpetual",
    )


def test_pre_activation_schedule_admits_taker_exit_cost_and_hash():
    result = admit(snapshot())
    assert result["eligible"] is True
    assert result["expected_exit_fee_price_pct"] == 0.05
    assert len(result["snapshot_sha256"]) == 64


def test_hash_is_canonical_across_key_order():
    original = snapshot()
    reordered = dict(reversed(list(deepcopy(original).items())))
    assert admit(original)["snapshot_sha256"] == admit(reordered)["snapshot_sha256"]


def test_post_activation_or_wrong_market_fails_closed():
    assert admit(snapshot(captured_at_utc="2026-09-07T00:02:00+00:00"))["eligible"] is False
    assert admit(snapshot(market="SPOT"))["exclusion_reason"] == "market mismatch"


def test_missing_provenance_or_invalid_rate_fails_closed():
    assert admit(snapshot(source=""))["exclusion_reason"] == "schedule provenance incomplete"
    assert admit(snapshot(taker_fee_rate=-0.1))["eligible"] is False
    assert admit(snapshot(taker_fee_rate=None))["eligible"] is False


def test_non_utc_or_future_effective_schedule_fails_closed():
    assert admit(snapshot(captured_at_utc="2026-09-07T00:00:00"))["eligible"] is False
    assert admit(snapshot(effective_at_utc="2026-09-07T00:02:00+00:00"))["eligible"] is False
