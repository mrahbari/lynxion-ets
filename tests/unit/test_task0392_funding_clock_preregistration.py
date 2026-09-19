from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_protocol_freezes_actual_timestamps_controls_and_nonproduction_boundary():
    text = (ROOT / "docs/FUNDING_SETTLEMENT_MARKET_QUALITY_PREREGISTRATION.md").read_text()

    assert "Never hardcode eight hours" in text
    assert "exact midpoint" in text
    assert "cluster bootstrap by settlement timestamp" in text
    assert "LOW_INFORMATION_VALUE — DO_NOT_BUILD" in text
    assert "does not modify the frozen Rescue" in text
