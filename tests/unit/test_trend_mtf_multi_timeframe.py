"""TrendMTF real multi-timeframe mode: 1m candles are downsampled into closed 15m/1h/4h bars."""
from datetime import datetime, timedelta, timezone

import numpy as np

from domain.value_objects import Symbol
from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher


class _Sink:
    def log_watcher_observation(self, **_):
        pass


T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _feed(w, closes):
    for i, c in enumerate(closes):
        ts = T0 + timedelta(minutes=i)
        w.update_data({"close": c, "candle": {"close": c, "timestamp": ts, "close_time": ts + timedelta(minutes=1)}})


def _watcher():
    return TrendMTFWatcher("trend_mtf", "BTCUSDT", forensic_sink=_Sink())


def test_no_observation_until_every_timeframe_has_closed_bars():
    w = _watcher()
    _feed(w, 100 + np.arange(240 * 19) * 0.01)       # 19 closed 4h bars only
    assert w.analyze(Symbol("BTCUSDT")) is None


def test_aligned_uptrend_and_downtrend():
    rng = np.random.default_rng(1)
    n = 240 * 21
    up = 100 * np.exp(np.cumsum(0.0002 + rng.normal(0, 0.0005, n)))
    w = _watcher()
    _feed(w, up)
    obs = w.analyze(Symbol("BTCUSDT"))
    assert obs.observation_type == "trend_positive" and obs.metadata["mode"] == "mtf"
    w2 = _watcher()
    _feed(w2, up[::-1].copy())
    assert w2.analyze(Symbol("BTCUSDT")).observation_type == "trend_negative"


def test_random_walk_is_mostly_neutral():
    rng = np.random.default_rng(7)
    w = _watcher()
    _feed(w, 100 * np.exp(np.cumsum(rng.normal(0, 0.001, 240 * 21))))
    assert w.analyze(Symbol("BTCUSDT")).observation_type == "trend_neutral"


def test_only_closed_higher_tf_bars_are_used():
    w = _watcher()
    _feed(w, [100.0] * 14)                            # 14 minutes: the first 15m bar is still forming
    assert w._htf[900]["closes"] == []
    _feed(w, [100.0] * 15)                            # re-feed restarts at T0 (out-of-order ignored)
    assert len(w._htf[900]["closes"]) == 1


def test_close_only_feed_keeps_legacy_behaviour():
    w = _watcher()
    w.update_data({"close": 100.0})
    w.update_data({"close": 101.0})
    obs = w.analyze(Symbol("BTCUSDT"))
    assert obs is not None and "mode" not in obs.metadata


def _htf_bars(tf_s, n, start, drift):
    return [{"timestamp": start + k * tf_s, "close": 100 * (1 + drift) ** k} for k in range(n)]


def test_seeded_history_gives_immediate_observation_without_double_counting():
    now = 1_800_000_000 // 14400 * 14400            # aligned to a 4h boundary
    w = _watcher()
    bars = {tf: _htf_bars(tf, 30, now - 30 * tf, 0.002 + 0.0001 * (k % 2))
            for tf in (900, 3600, 14400) for k in range(1)}
    bars[14400].append({"timestamp": now, "close": 1.0})   # still forming -> must be ignored
    assert w.seed_higher_timeframes(bars, now=now + 60) == 3
    assert len(w._htf[14400]["closes"]) == 30 and w._htf[14400]["closes"][-1] != 1.0
    # 1m bars of an already seeded bucket are skipped; the new bucket's bars are used
    ts = datetime.fromtimestamp(now - 120, tz=timezone.utc)
    w.update_data({"close": 1.0, "candle": {"close": 1.0, "timestamp": ts, "close_time": ts + timedelta(minutes=1)}})
    assert len(w._htf[900]["closes"]) == 30
    obs = w.analyze(Symbol("BTCUSDT"))
    assert obs is not None and obs.metadata["mode"] == "mtf"
    assert obs.observation_type == "trend_positive"
