import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_economic_holdout_is_frozen_against_existing_sources():
    frozen = json.loads(
        (ROOT / "data/research/lead_b/economic_holdout_manifest.json").read_text()
    )
    source = json.loads(
        (ROOT / "data/research/btc_aggtrades/manifest.json").read_text()
    )
    selected = sorted(
        day for day in source["days"] if frozen["holdout_start"] <= day <= frozen["holdout_end"]
    )

    assert frozen["created_without_lead_b_2026_outcome_access"] is True
    assert frozen["status"] == "FROZEN_BEFORE_OUTCOMES"
    assert selected[0] == "2026-01-01"
    assert selected[-1] == "2026-08-28"
    assert len(selected) == frozen["expected_days"] == 240
    assert frozen["expected_nominal_trades"] == 2 * len(selected)
    assert frozen["decision_times_utc"] == ["00:00:00", "12:00:00"]
    assert frozen["execution_cost_primary"] == 0.003
    assert frozen["execution_cost_stress"] == 0.005
    assert _sha256(ROOT / "data/research/btc_aggtrades/manifest.json") == frozen[
        "raw_manifest_sha256"
    ]
    assert _sha256(ROOT / "data/research/c16/funding/BTCUSDT.csv") == frozen[
        "funding_sha256"
    ]
