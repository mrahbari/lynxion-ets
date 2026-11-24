"""E16-U10: live Donchian-20 + EMA trend setup reproduces the E21 research design (TF1) signal for signal."""
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from domain.value_objects import Symbol
from infrastructure.strategies.trend_donchian import donchian_trend_setup

ROOT = Path(__file__).resolve().parents[2]


def bars(n=900, seed=5):
    rng = np.random.default_rng(seed)
    t0 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    px, drift, out = 100.0, 0.0, []
    for i in range(n):
        if i % 150 == 0:
            drift = rng.choice([-0.002, 0.002])
        o = px
        px = max(1.0, px * (1 + drift + rng.normal(0, 0.006)))
        out.append({"timestamp": t0 + 3600 * i, "open": o, "high": max(o, px) * (1 + abs(rng.normal(0, 0.002))),
                    "low": min(o, px) * (1 - abs(rng.normal(0, 0.002))), "close": px, "volume": 100.0})
    return out


def test_matches_e21_research_signals():
    sys.path.insert(0, str(ROOT / "research" / "v2" / "experiments"))
    import e21_canonical_setups as e21
    ref = e21.TrendCanonical()
    b = bars()
    got, want = [], []
    for i, bar in enumerate(b):
        ref.update_with_market_data({**bar, "timestamp": datetime.fromtimestamp(bar["timestamp"], tz=timezone.utc).replace(tzinfo=None)})
        r = ref.generate_signal(None)
        want.append(None if r is None else (r.signal_type.name, round(float(r.metadata["setup"].stop_loss_level), 8)))
        s = donchian_trend_setup(b[:i + 1], Symbol("BTCUSDT"), now_s=bar["timestamp"] + 3600)
        got.append(None if s is None else (s.direction, round(float(s.stop_loss_level), 8)))
    assert sum(x is not None for x in want) >= 10
    assert got == want


def test_adapter_requests_400_hourly_bars():
    from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
    assert TrendFollowStrategyAdapter({}).config["history_period"] == "18d"
