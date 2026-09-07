import pytest

from infrastructure.research.shadow_friction_inputs import (
    admit_funding_window,
    frozen_slippage_contract,
)


def funding_snapshot(**updates):
    value = {
        "exchange": "BINGX", "market": "PERPETUAL", "symbol": "BTCUSDT",
        "source": "BINGX_FUNDING_SETTLEMENT_HISTORY",
        "coverage_start_utc": "2026-09-06T23:00:00+00:00",
        "coverage_end_utc": "2026-09-07T03:00:00+00:00",
        "settlements": [
            {"settlement_id": "f0", "timestamp_utc": "2026-09-07T00:00:00+00:00", "funding_rate": 0.01},
            {"settlement_id": "f1", "timestamp_utc": "2026-09-07T02:00:00+00:00", "funding_rate": 0.002},
        ],
    }
    value.update(updates)
    return value


def admit(snapshot, is_long=True):
    return admit_funding_window(
        snapshot, symbol="BTCUSDT", is_long=is_long,
        entry_time_utc="2026-09-07T00:00:00+00:00",
        exit_time_utc="2026-09-07T03:00:00+00:00",
    )


def test_only_strictly_between_settlements_receive_correct_side_sign():
    assert admit(funding_snapshot())["funding_price_return"] == -0.002
    assert admit(funding_snapshot(), is_long=False)["funding_price_return"] == 0.002
    assert admit(funding_snapshot())["settlement_count"] == 1


def test_incomplete_coverage_or_wrong_symbol_fails_closed():
    assert admit(funding_snapshot(coverage_end_utc="2026-09-07T02:59:00+00:00"))["eligible"] is False
    assert admit(funding_snapshot(symbol="ETHUSDT"))["eligible"] is False


def test_duplicate_or_malformed_settlement_fails_closed():
    duplicate = funding_snapshot()["settlements"] * 2
    assert admit(funding_snapshot(settlements=duplicate))["eligible"] is False
    assert admit(funding_snapshot(settlements=[{"settlement_id": "x", "timestamp_utc": "bad", "funding_rate": 0.1}]))["eligible"] is False


def test_exact_preregistered_slippage_contract_is_admitted():
    assert frozen_slippage_contract(
        primary_round_trip_price_pct=0.10,
        stress_round_trip_price_pct=0.20,
        candidate_remaining_exit_price_pct=0.10,
    )["stress_round_trip_price_pct"] == 0.20


def test_slippage_variant_is_rejected():
    with pytest.raises(ValueError, match="preregistration"):
        frozen_slippage_contract(
            primary_round_trip_price_pct=0.05,
            stress_round_trip_price_pct=0.20,
            candidate_remaining_exit_price_pct=0.10,
        )
