import hashlib
import json

import pytest

from scripts.verify_c35_aggregate_activation import verify


def _fixture(tmp_path):
    files = {}
    for role in ("protocol", "math", "evaluator", "unseal_gate"):
        path = tmp_path / f"{role}.txt"
        path.write_text(role)
        files[f"{role}_path"] = path.name
        files[f"{role}_sha256"] = hashlib.sha256(role.encode()).hexdigest()
    return {
        "candidate": "C-35", "status": "PREPARED_NOT_ACTIVATED",
        "aggregate_economics_opened": False, "prepared_against_commit": "a" * 40,
        "bootstrap_seed": 350035, "bootstrap_samples": 10000,
        "minimum_positions": 240, "minimum_positions_per_side": 80,
        "minimum_utc_weeks": 8, **files,
    }


def test_accepts_exact_frozen_aggregate_contract(tmp_path):
    assert verify(_fixture(tmp_path), tmp_path, check_git=False)["economics"] == "SEALED"


@pytest.mark.parametrize("field,value", [
    ("aggregate_economics_opened", True), ("bootstrap_seed", 1),
    ("bootstrap_samples", 9999), ("minimum_positions", 239),
])
def test_rejects_gate_or_sampling_drift(tmp_path, field, value):
    manifest = _fixture(tmp_path)
    manifest[field] = value
    with pytest.raises(ValueError, match=field):
        verify(manifest, tmp_path, check_git=False)


def test_rejects_implementation_hash_drift(tmp_path):
    manifest = _fixture(tmp_path)
    (tmp_path / manifest["math_path"]).write_text("changed")
    with pytest.raises(ValueError, match="math hash"):
        verify(manifest, tmp_path, check_git=False)
