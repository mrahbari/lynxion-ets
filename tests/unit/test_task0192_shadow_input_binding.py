import hashlib
import json

import pytest

from infrastructure.research.exit_policy_shadow_input import bind_shadow_observations


MANIFEST = {
    "schema_version": 1, "run_id": "post-fix-run",
    "activation_boundary_utc": "2026-09-07T00:00:00+00:00",
    "commit": "abc123", "historical_import_allowed": False,
}


def event(**updates):
    base = {
        "schema_version": 1, "event_id": "e1", "event_type": "MANAGER_EVALUATED",
        "event_time_utc": "2026-09-07T00:01:00+00:00", "run_id": "post-fix-run",
        "evaluation_id": "v1", "position_key": "BTCUSDT:LONG:100", "symbol": "BTCUSDT",
        "side": "LONG", "quantity": 1.0, "entry_price": 100.0, "current_price": 101.0,
        "price_source": "MARK", "configured_leverage": None, "requested_leverage": None,
        "exchange_leverage": 10.0, "roe_pct": 10.0, "peak_price": 101.0,
        "peak_roe_pct": 10.0, "manager_state_before": {},
        "manager_state_after": {"current_sl_price": 100.35}, "error": None,
        "decision": "NO_ACTION", "manager_thresholds": {
            "breakeven_trigger_roe_pct": 6.0, "trailing_trigger_roe_pct": 10.0,
            "trailing_distance_price_pct": 0.005, "fee_buffer_price_pct": 0.0035,
        },
    }
    base.update(updates)
    return base


def encoded(item):
    return (json.dumps(item, sort_keys=True) + "\n").encode()


def bind(item, manifest=MANIFEST, expected_commit="abc123"):
    raw = encoded(item)
    return bind_shadow_observations(
        manifest, raw, expected_commit=expected_commit,
        expected_source_sha256=hashlib.sha256(raw).hexdigest(),
    )


def test_exact_post_boundary_manager_observation_binds_without_outcome():
    observations = bind(event())
    assert len(observations) == 1
    assert observations[0].leverage == 10.0
    assert observations[0].reviewed_stop_price == 100.35


def test_hash_commit_boundary_and_run_mismatch_fail_closed():
    raw = encoded(event())
    with pytest.raises(ValueError, match="hash"):
        bind_shadow_observations(
            MANIFEST, raw, expected_commit="abc123", expected_source_sha256="0" * 64
        )
    with pytest.raises(ValueError, match="commit"):
        bind(event(), expected_commit="different")
    with pytest.raises(ValueError, match="post-boundary"):
        bind(event(event_time_utc=MANIFEST["activation_boundary_utc"]))
    with pytest.raises(ValueError, match="foreign"):
        bind(event(run_id="other"))


def test_wrong_leverage_thresholds_or_price_source_fail_closed():
    with pytest.raises(ValueError, match="10x"):
        bind(event(exchange_leverage=5.0))
    wrong = dict(event()["manager_thresholds"], trailing_trigger_roe_pct=11.0)
    with pytest.raises(ValueError, match="thresholds"):
        bind(event(manager_thresholds=wrong))
    with pytest.raises(ValueError, match="mark price"):
        bind(event(price_source="LAST"))
