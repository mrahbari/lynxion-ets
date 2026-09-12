from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.verify_exit_shadow_fee_snapshot import verify


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data/research/exit_shadow/bingx_perpetual_fee_snapshot-20260912T164438Z.json"


def payload():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_real_public_bingx_snapshot_is_hash_bound_and_conservative():
    result = verify(payload())
    assert result["expected_exit_fee_price_pct"] == 0.05
    assert result["account_tier"] == "STANDARD_PUBLIC_BASE"
    assert result["authorizes_broker_access"] is False
    assert result["authorizes_runtime"] is False


def test_rate_or_hash_drift_fails_closed():
    changed = deepcopy(payload())
    changed["snapshot"]["taker_fee_rate"] = "0.0004"
    with pytest.raises(ValueError, match="hash mismatch"):
        verify(changed)


def test_post_capture_boundary_and_scope_are_required():
    early = deepcopy(payload())
    early["activation_not_before_utc"] = "2026-09-12T16:44:37Z"
    with pytest.raises(ValueError, match="post-activation"):
        verify(early)
    wrong_scope = deepcopy(payload())
    wrong_scope["snapshot"]["source_scope"] = "VIP_DISCOUNT"
    with pytest.raises(ValueError, match="not conservative"):
        verify(wrong_scope)
