from dataclasses import replace

import pytest

from infrastructure.research.paired_exit_evaluator import evaluate_linked_shadow_pair
from tests.unit.test_task0200_paired_exit_outcome import linked


def funding(**updates):
    value = {
        "exchange": "BINGX", "market": "PERPETUAL", "symbol": "BTCUSDT",
        "source": "BINGX_FUNDING_SETTLEMENT_HISTORY",
        "coverage_start_utc": "2026-09-06T23:00:00+00:00",
        "coverage_end_utc": "2026-09-07T01:00:00+00:00",
        "settlements": [{
            "settlement_id": "f1", "timestamp_utc": "2026-09-07T00:01:30+00:00",
            "funding_rate": 0.001,
        }],
    }
    value.update(updates)
    return value


def test_candidate_fill_sequence_selects_its_own_funding_window():
    item = linked()
    activate = replace(
        item.position.observations[0], sequence=0, event_time_utc="2026-09-07T00:01:00+00:00",
        mark_price=101.2, roe_pct=12.0, reviewed_stop_price=None,
    )
    cross = replace(
        activate, sequence=1, event_id="e1", event_time_utc="2026-09-07T00:01:20+00:00",
        mark_price=100.69, roe_pct=6.9,
    )
    item = replace(item, position=replace(item.position, observations=(activate, cross)))
    result = evaluate_linked_shadow_pair(
        item, funding_snapshot=funding(), primary_slippage_price_pct=0.10,
        stress_slippage_price_pct=0.20,
    )
    assert result.candidate.exit_price == pytest.approx(100.69)
    assert result.candidate.funding_return == 0.0
    assert result.baseline.funding_return == pytest.approx(-0.001)


def test_no_candidate_fill_shares_terminal_and_funding():
    item = linked()
    result = evaluate_linked_shadow_pair(
        item, funding_snapshot=funding(), primary_slippage_price_pct=0.10,
        stress_slippage_price_pct=0.20,
    )
    assert result.candidate.exit_price == result.baseline.exit_price
    assert result.candidate.funding_return == result.baseline.funding_return


def test_incomplete_candidate_funding_window_fails_closed():
    with pytest.raises(ValueError, match="funding evidence"):
        evaluate_linked_shadow_pair(
            linked(), funding_snapshot=funding(coverage_start_utc="2026-09-07T00:00:30+00:00"),
            primary_slippage_price_pct=0.10, stress_slippage_price_pct=0.20,
        )
