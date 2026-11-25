import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live import scanner as SC  # noqa: E402

DAY, H4 = 86_400_000, 4 * 3_600_000


def _kl(closes, step, t0=0, qv=2e7):
    return [[t0 + i * step, c, c * 1.01, c * 0.99, c, 0, t0 + (i + 1) * step - 1, qv] for i, c in enumerate(closes)]


def _feat(trend):
    d = _kl(list(100 * np.exp(np.cumsum(np.full(60, trend) + np.random.default_rng(0).normal(0, 0.01, 60)))), DAY)
    h = _kl(list(100 * np.exp(np.cumsum(np.full(60, trend / 6)))), H4)
    return SC.features(d, h)


def test_closed_filter_drops_open_bar():
    rows = _kl([1, 2, 3], H4)
    assert len(SC.closed(rows, H4, 3 * H4 - 1)) == 2 and len(SC.closed(rows, H4, 3 * H4)) == 3


def test_features_signs_follow_trend():
    up, dn = _feat(0.02), _feat(-0.02)
    assert up["momentum"] > 0 and up["strength"] > 0 and up["short_term"] > 0
    assert dn["momentum"] < 0 and dn["strength"] < 0 and dn["short_term"] < 0
    assert SC.features(_kl([1.0] * 10, DAY), _kl([1.0] * 50, H4)) is None      # too short


def test_pick_requires_all_components_to_agree():
    feat = {"UPUSDT": _feat(0.02), "DNUSDT": _feat(-0.02), "MIXUSDT": {**_feat(0.02), "short_term": -1.0}}
    longs, shorts = SC.pick(SC.rank_table(feat))
    assert list(longs.index) == ["UPUSDT"] and list(shorts.index) == ["DNUSDT"]


def test_limit_levels_long_and_short():
    r = {"atr_4h": 2.0, "close": 100.0, "ema20_4h": 99.0}
    assert SC.limit_levels(r, "LONG", 2) == (99.0, 96.0)            # EMA closer than 1 ATR
    r = {"atr_4h": 2.0, "close": 100.0, "ema20_4h": 90.0}
    assert SC.limit_levels(r, "LONG", 2) == (98.0, 95.0)            # 1 ATR pullback
    r = {"atr_4h": 2.0, "close": 100.0, "ema20_4h": 103.0}
    assert SC.limit_levels(r, "SHORT", 2) == (102.0, 105.0)


def test_market_view_labels():
    df = pd.DataFrame({"above_ema50d": [True, True, True, False], "ret28": [0.1] * 4, "close": [1.0] * 4,
                       "score": [80.0, 70, 60, 20], "momentum": [1.0, 1, 1, -1], "strength": [1.0, 1, -1, -1],
                       "short_term": [1.0, 1, 1, -1], "vol24h": [3.0] * 4, "adv30": [2.0] * 4},
                      index=["BTCUSDT", "A", "B", "C"])
    mv = SC.market_view(df, {})
    assert mv["label"] == "TRENDING UP" and mv["sentiment"] == "Bullish" and mv["energy"] == "High"
    assert abs(mv["confidence"] - 5.0) < 1e-9                       # 2 of 4 coins agree on all three
    df["above_ema50d"] = [False, False, False, True]
    assert SC.market_view(df, {})["label"] == "TRENDING DOWN"


def test_render_flags_and_disclaimer():
    feat = {"UPUSDT": _feat(0.02), "DNUSDT": _feat(-0.02), "BTCUSDT": _feat(0.01)}
    df = SC.rank_table(feat)
    longs, shorts = SC.pick(df)
    text, rows = SC.render(longs, shorts, SC.market_view(df, {}), {"UPUSDT": 0.001}, {}, "t")
    assert "💸" in text and "Entry" in text and "Stop loss" in text
    for x in rows:                                   # targets on the profit side of the limit, stop on the loss side
        sgn = 1 if x["side"] == "LONG" else -1
        assert sgn * (x["target2"] - x["target1"]) > 0 and sgn * (x["target1"] - x["limit"]) > 0 > sgn * (x["stop"] - x["limit"]) and {r["side"] for r in rows} == {"LONG", "SHORT"}
