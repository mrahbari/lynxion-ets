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


def _k(closes, step, rng=0.01):
    return [[i * step, c, c * (1 + rng), c * (1 - rng), c, 0, (i + 1) * step - 1, 1e7] for i, c in enumerate(closes)]


def test_trade_levels_long_short_geometry_and_caps():
    up = list(np.linspace(90, 100, 60))
    lv = SC.trade_levels("LONG", 100.0, 5.0, _k(up, 3_600_000), _k(up[-60:], 900_000, 0.002))
    d = lv["limit"] - lv["sl"]
    assert lv["limit"] <= 100 and lv["sl"] < lv["limit"] < lv["tp1"] < lv["tp2"]
    assert abs((lv["tp1"] - lv["limit"]) - 1.5 * d) < 1e-9 and abs((lv["tp2"] - lv["limit"]) - 3 * d) < 1e-9
    assert lv["atr_1h"] - 1e-9 <= d <= 5.0 + 1e-9                     # between 1 ATR(1h) and 1 ATR(4h)
    dn = up[::-1]
    sv = SC.trade_levels("SHORT", 90.0, 0.5, _k(dn, 3_600_000), _k(dn, 900_000, 0.002))
    assert sv["tp2"] < sv["tp1"] < sv["limit"] < sv["sl"] and abs((sv["sl"] - sv["limit"]) - 0.5) < 1e-9   # 4h cap
    assert SC.trade_levels("LONG", 1.0, 1.0, _k([1.0] * 10, 3_600_000), _k([1.0] * 10, 900_000)) is None


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
    lvl = lambda side, px: SC.trade_levels(side, px, 5.0, _k(list(np.linspace(px * 0.9, px, 60)) if side == "LONG" else  # noqa: E731
                                                            list(np.linspace(px * 1.1, px, 60)), 3_600_000),
                                           _k([px] * 30, 900_000, 0.002))
    longs = longs.assign(levels=[lvl("LONG", float(longs.loc[x, "close"])) for x in longs.index])
    shorts = shorts.assign(levels=[lvl("SHORT", float(shorts.loc[x, "close"])) for x in shorts.index])
    text, rows = SC.render(longs, shorts, SC.market_view(df, {}), {"UPUSDT": 0.001}, {}, "t")
    assert "💸" in text and "Entry" in text and "TP1" in text and "SL" in text
    for x in rows:                                   # targets on the profit side of the limit, stop on the loss side
        sgn = 1 if x["side"] == "LONG" else -1
        assert sgn * (x["target2"] - x["target1"]) > 0 and sgn * (x["target1"] - x["limit"]) > 0 > sgn * (x["stop"] - x["limit"]) and {r["side"] for r in rows} == {"LONG", "SHORT"}


def test_b_trigger_breakout_and_compression_expansion():
    n = 60
    c = np.full(n, 100.0); o = c.copy(); h = c + 1; l = c - 1; v = np.full(n, 10.0)
    c2, l2, o2 = c.copy(), l.copy(), o.copy()
    c2[-1], l2[-1], o2[-1] = 95.0, 94.0, 100.0          # close below the 20-bar low ...
    assert SC.b_trigger(o2, h, l2, c2, np.r_[v[:-1], 20.0]) == -1      # ... with 2x volume
    assert SC.b_trigger(o2, h, l2, c2, v) == 0           # no volume and no prior compression -> no trigger
    h3, l3 = h.copy(), l2.copy()
    h3[-6:-1], l3[-6:-1] = 100.1, 99.9                    # five quiet bars (ATR5/ATR50 < 0.7) ...
    assert SC.b_trigger(o2, h3, l3, c2, v) == -1         # ... then a wide bearish bar: compression -> expansion
    assert SC.b_trigger(o, h, l, c, v) == 0


def test_b_short_list_needs_bearish_trigger():
    df = pd.DataFrame({"mom7": [-1.0, -1.0, 1.0], "accel": [-0.1, -0.2, 0.1], "strength": [-0.5, -0.4, 0.5],
                       "short_term": [-1.0, -1.5, 1.0], "trig": [-1, 0, -1]}, index=["AUSDT", "BUSDT", "CUSDT"])
    assert SC.b_short_list(df) == ["AUSDT"]


def test_log_shadow_marks_new_entries(tmp_path):
    p = tmp_path / "b.jsonl"
    r = {"ts": "t1", "universe": 1, "market": {}, "shadow_b_short": [{"symbol": "AUSDT"}]}
    SC.log_shadow(r, p)
    SC.log_shadow({**r, "ts": "t2", "shadow_b_short": [{"symbol": "AUSDT"}, {"symbol": "BUSDT"}]}, p)
    import json
    last = json.loads(p.read_text().splitlines()[-1])["picks"]
    assert [(x["symbol"], x["new"]) for x in last] == [("AUSDT", False), ("BUSDT", True)]


def test_h4_view_requires_all_three_and_ranks():
    df = pd.DataFrame({"rsi4": [10.0, 5.0, -5.0, -10.0, 3.0], "macd4": [0.5, 0.2, -0.3, -0.6, -0.1],
                       "short_term": [1.0, 0.5, -0.5, -1.2, 0.4]}, index=["A", "B", "C", "D", "E"])
    l4, s4 = SC.h4_view(df, n=5)
    assert list(l4.index) == ["A", "B"] and list(s4.index) == ["D", "C"]      # E: MACD disagrees -> excluded
