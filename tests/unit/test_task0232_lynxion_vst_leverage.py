from pathlib import Path


def test_tracked_lynxion_launcher_pins_both_leverage_ceilings_to_ten():
    launcher = (Path(__file__).resolve().parents[2] / "lynxion").read_text(encoding="utf-8")
    assert "RISK_MAX_LEVERAGE=10" in launcher
    assert "MAX_LEVERAGE=10" in launcher
    assert launcher.index("RISK_MAX_LEVERAGE=10") < launcher.index("python run_trading_system.py")
    assert launcher.index("MAX_LEVERAGE=10") < launcher.index("python run_trading_system.py")
