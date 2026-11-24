"""E16-U10: live session-VWAP setup reproduces the E21 research design (VR1) signal for signal."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from domain.value_objects import Symbol
from infrastructure.strategies.vwap_session import session_vwap_setup, closed_bars

ROOT = Path(__file__).resolve().parents[2]


def bars(n=700, seed=3):
    rng = np.random.default_rng(seed)
    t0 = int(datetime(2026, 3, 1, tzinfo=timezone.utc).timestamp())
    px, out = 100.0, []
    for i in range(n):
        o = px
        px = max(1.0, px * (1 + rng.normal(0, 0.006) + (0.02 if rng.random() < 0.01 else 0) * rng.choice([-1, 1])))
        out.append({"timestamp": t0 + 900 * i, "open": o, "high": max(o, px) * (1 + abs(rng.normal(0, 0.002))),
                    "low": min(o, px) * (1 - abs(rng.normal(0, 0.002))), "close": px, "volume": float(rng.uniform(50, 150))})
    return out


def test_matches_e21_research_signals():
    sys.path.insert(0, str(ROOT / "research" / "v2" / "experiments"))
    import e21_canonical_setups as e21
    ref = e21.VWAPCanonical()
    b = bars()
    got, want = [], []
    for i, bar in enumerate(b):
        ref.update_with_market_data({**bar, "timestamp": datetime.fromtimestamp(bar["timestamp"], tz=timezone.utc).replace(tzinfo=None)})
        r = ref.generate_signal(None)
        want.append(None if r is None else (r.signal_type.name, round(float(r.metadata["setup"].stop_loss_level), 8),
                                            round(float(r.metadata["setup"].take_profit_level), 8)))
        s = session_vwap_setup(b[max(0, i - 399):i + 1], Symbol("BTCUSDT"), now_s=bar["timestamp"] + 900)
        got.append(None if s is None else (s.direction, round(float(s.stop_loss_level), 8), round(float(s.take_profit_level), 8)))
    assert sum(x is not None for x in want) >= 5
    assert got == want


def test_forming_bar_is_ignored():
    b = bars(60)
    assert len(closed_bars(b, now_s=b[-1]["timestamp"] + 899)) == 59
    assert len(closed_bars(b, now_s=b[-1]["timestamp"] + 900)) == 60
