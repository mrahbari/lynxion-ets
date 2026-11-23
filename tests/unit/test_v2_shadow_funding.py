"""XS-COMBO shadow funding ledger: VST settles no funding, so it is booked from real rates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research" / "v2"))
from live import tracking  # noqa: E402


def test_long_pays_positive_funding_short_receives(monkeypatch, tmp_path):
    monkeypatch.setattr(tracking, "bingx_funding", lambda s, a, b: [0.001, 0.001])
    monkeypatch.setattr(tracking, "binance_funding", lambda s, a, b: [0.0005])
    monkeypatch.setattr(tracking.time, "sleep", lambda *_: None)
    pos = [{"symbol": "AAA-USDT", "positionAmt": "10", "positionSide": "LONG", "markPrice": "100",
            "unrealizedProfit": "1", "positionValue": "1000"},
           {"symbol": "BBB-USDT", "positionAmt": "5", "positionSide": "SHORT", "markPrice": "100",
            "unrealizedProfit": "-2", "positionValue": "500"}]
    sf = tracking.shadow_funding(pos, 0, 10)
    assert sf["per_position"] == {"AAA-USDT:LONG": -2.0, "BBB-USDT:SHORT": 1.0}
    assert sf["bingx"] == -1.0 and sf["binance"] == -0.25
    state = {"tracking_start_ms": 0}
    row = tracking.track(pos, state, tmp_path / "t.csv", now_ms=3_600_000)
    assert state["tracking_until"] == 3_600_000 and state["shadow_funding_cum"] == -1.0
    assert row["unrealized_plus_shadow_funding"] == -2.0
    row2 = tracking.track(pos, state, tmp_path / "t.csv", now_ms=7_200_000)
    assert row2["shadow_funding_cum"] == -2.0 and row2["window_hours"] == 1.0
    assert len((tmp_path / "t.csv").read_text().splitlines()) == 3
