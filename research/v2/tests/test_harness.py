import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt  # noqa: E402
from lib import panel as pn  # noqa: E402
from lib import stats as st  # noqa: E402


def _toy(n=5):
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    cols = ["A", "B"]
    px = pd.DataFrame({"A": [100, 110, 99, 99, 120], "B": [50, 50, 55, 50, 50]}, index=idx, dtype=float)[:n]
    p = {"exec_px": px, "close": px, "quote_volume": pd.DataFrame(1e12, index=idx, columns=cols),
         "funding_fwd": pd.DataFrame(0.0, index=idx, columns=cols)}
    return p, idx, cols


def test_forward_return_alignment():
    p, idx, cols = _toy()
    fr = pn.forward_returns(p)
    assert fr.loc[idx[0], "A"] == pytest.approx(0.10)
    assert fr.loc[idx[1], "A"] == pytest.approx(99 / 110 - 1)
    assert np.isnan(fr.loc[idx[-1], "A"])


def test_backtest_gross_fee_funding_hand_computed():
    p, idx, cols = _toy()
    p["funding_fwd"].loc[idx[0], "A"] = 0.001
    fr = pn.forward_returns(p)
    w = pd.DataFrame(0.0, index=idx, columns=cols)
    w.loc[idx[0], "A"] = 1.0
    cm = bt.CostModel(fee=0.001, impact_y=0.0, spread_buckets=((0, 0.0),))
    r = bt.run(w, fr, p, cm)
    # day0: buy 1.0 A: +10% gross, -0.1% fee, -0.1% funding
    assert r.gross.iloc[0] == pytest.approx(0.10)
    assert r.cost.iloc[0] == pytest.approx(0.001)
    assert r.funding.iloc[0] == pytest.approx(-0.001)
    # day1: target 0, held drifted weight = 1.1/1.098 -> sell all, pay fee on that
    held = 1.10 / (1 + 0.10 - 0.001 - 0.001)
    assert r.cost.iloc[1] == pytest.approx(0.001 * held)
    assert r.gross.iloc[1] == 0.0


def test_short_earns_on_drop_and_receives_funding():
    p, idx, cols = _toy()
    p["funding_fwd"].loc[idx[1], "A"] = 0.002
    fr = pn.forward_returns(p)
    w = pd.DataFrame(0.0, index=idx, columns=cols)
    w.loc[idx[1], "A"] = -1.0
    r = bt.run(w, fr, p, bt.CostModel(fee=0.0, impact_y=0.0, spread_buckets=((0, 0.0),)))
    assert r.gross.iloc[1] == pytest.approx(-(99 / 110 - 1))
    assert r.funding.iloc[1] == pytest.approx(0.002)


def test_rank_long_short_is_dollar_neutral():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    sig = pd.DataFrame(np.random.default_rng(0).normal(size=(3, 20)), index=idx)
    w = bt.rank_long_short(sig, sig.notna(), frac=0.2)
    assert np.allclose(w.sum(axis=1), 0)
    assert np.allclose(w.abs().sum(axis=1), 1)


def test_random_signal_has_no_edge_and_foresight_does():
    rng = np.random.default_rng(1)
    idx = pd.date_range("2022-01-01", periods=600, freq="1D", tz="UTC")
    cols = [f"S{i}" for i in range(40)]
    rets = pd.DataFrame(rng.normal(0, 0.03, (600, 40)), index=idx, columns=cols)
    px = (1 + rets).cumprod() * 100
    p = {"exec_px": px, "close": px, "quote_volume": pd.DataFrame(1e12, index=idx, columns=cols),
         "funding_fwd": pd.DataFrame(0.0, index=idx, columns=cols)}
    fr = pn.forward_returns(p)
    mask = px.notna()
    noise = bt.run(bt.rank_long_short(pd.DataFrame(rng.normal(size=(600, 40)), index=idx, columns=cols), mask), fr, p)
    assert abs(st.sharpe(noise.gross)) < 1.5
    cheat = bt.run(bt.rank_long_short(fr, mask), fr, p)
    assert st.sharpe(cheat.gross) > 10
    # using the *realised* (known) past return is not cheating: no foresight edge in iid data
    past = bt.run(bt.rank_long_short(fr.shift(1), mask), fr, p)
    assert abs(st.sharpe(past.gross)) < 1.5


def test_dsr_penalises_many_trials():
    rng = np.random.default_rng(2)
    x = pd.Series(rng.normal(0.001, 0.01, 1000), index=pd.date_range("2020-01-01", periods=1000, tz="UTC"))
    assert st.dsr(x, 1, 1.0) > st.dsr(x, 1000, 1.0)


@pytest.mark.skipif(not (pn.LAKE / "klines_1h" / "BTCUSDT.parquet").exists(), reason="lake not built")
def test_real_btc_daily_timing():
    d = pn._daily_for_symbol("BTCUSDT").set_index("date")
    k = pd.read_parquet(pn.LAKE / "klines_1h" / "BTCUSDT.parquet").set_index("open_time")
    day = pd.Timestamp("2024-03-10", tz="UTC")
    ms = int(day.value // 10**6)
    # row D close == close of the 23:00 bar of D-1 (last bar fully known at D)
    assert d.loc[day, "close"] == k.loc[ms - 3_600_000, "close"]
    # exec price == close of the 00:00 bar of D (known at 01:00)
    assert d.loc[day, "exec_px"] == k.loc[ms, "close"]
    f = pd.read_parquet(pn.LAKE / "funding" / "BTCUSDT.parquet")
    fwd = f[(f.calc_time > ms + 3_600_000) & (f.calc_time <= ms + 25 * 3_600_000)].funding_rate.sum()
    assert d.loc[day, "funding_fwd"] == pytest.approx(fwd)
