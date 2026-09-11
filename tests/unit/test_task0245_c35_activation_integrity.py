import hashlib

import pytest

from scripts.verify_c35_activation import EXPECTED_UNIVERSE, verify_manifest


def _manifest(tmp_path):
    manifest = {
        "candidate": "C-35",
        "boundary_epoch": 1789087244,
        "universe": EXPECTED_UNIVERSE,
        "network_contract": "PUBLIC_UNAUTHENTICATED_BINANCE_USDM_KLINES_ONLY",
    }
    for role in ("protocol", "collector", "evaluator"):
        path = tmp_path / f"{role}.txt"
        path.write_text(role)
        manifest[f"{role}_path"] = path.name
        manifest[f"{role}_sha256"] = hashlib.sha256(role.encode()).hexdigest()
    return manifest


def test_accepts_exact_frozen_files(tmp_path):
    assert verify_manifest(_manifest(tmp_path), tmp_path, check_git=False)["integrity"] == "PASS"


def test_rejects_hash_drift(tmp_path):
    manifest = _manifest(tmp_path)
    (tmp_path / "collector.txt").write_text("changed")
    with pytest.raises(ValueError, match="collector hash mismatch"):
        verify_manifest(manifest, tmp_path, check_git=False)


def test_rejects_boundary_drift(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["boundary_epoch"] += 1
    with pytest.raises(ValueError, match="boundary mismatch"):
        verify_manifest(manifest, tmp_path, check_git=False)
