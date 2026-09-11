import hashlib

import pytest

from scripts.verify_c35_funding_activation import UNIVERSE, verify


def _manifest(root):
    result = {
        "candidate": "C-35", "boundary_epoch": 1789087244, "universe": UNIVERSE,
        "network_contract": "PUBLIC_UNAUTHENTICATED_BINANCE_USDM_FUNDING_ONLY",
    }
    for role in ("protocol", "collector", "resolver"):
        path = root / role
        path.write_text(role)
        result[f"{role}_path"] = role
        result[f"{role}_sha256"] = hashlib.sha256(role.encode()).hexdigest()
    return result


def test_accepts_exact_funding_contract(tmp_path):
    assert verify(_manifest(tmp_path), tmp_path, check_git=False)["funding_integrity"] == "PASS"


def test_rejects_funding_collector_drift(tmp_path):
    manifest = _manifest(tmp_path)
    (tmp_path / "collector").write_text("changed")
    with pytest.raises(ValueError, match="collector hash mismatch"):
        verify(manifest, tmp_path, check_git=False)


def test_rejects_authenticated_network_contract(tmp_path):
    manifest = _manifest(tmp_path)
    manifest["network_contract"] = "AUTHENTICATED"
    with pytest.raises(ValueError, match="network contract"):
        verify(manifest, tmp_path, check_git=False)
