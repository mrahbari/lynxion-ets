"""E11 — every watcher re-tested after the logic review, each against ITS OWN job.

Pre-registered before running (2026-11-23):
  Windows: FRESH 2026-03-01..2026-06-30 (never used for any watcher test), DEV 2026-07-01..08-31 and
  OLD-VAL 2026-09-01..10-31 (both already seen in E8b/E8d; reported for continuity only).
  Feed: closed 1m Binance USDT-M bars, payload shapes as live (flat + candle with close_time; funding as
  published). Observation -> live EngineService rule -> BUY/SELL/0.
  Directional watchers (trend_mtf, historical_candle, market_pulse, anomaly_ml, funding_rate):
    * ONSET events: first bar of a new non-zero engine side; per symbol, events closer than the horizon to
      the previous counted event are skipped (non-overlapping). Forward log return close(t)->close(t+h),
      signed, gross. Horizons 15m / 1h / 4h.
    * Stand-alone edge: FRESH mean > 10 bp (round-trip cost) with t >= 2 at a horizon whose DEV mean is
      also > 0. Input-quality edge (useful inside Fusion): FRESH gross mean > 0 with t >= 2 and DEV > 0.
  volatility (REGIME, no side): does the 1h/24h realized-vol state predict the NEXT hour's realized vol?
    Reported: mean next-60m realized vol / trailing 24h baseline per state; useful if expansion > normal >
    compression on FRESH (vol clustering) — a filter, not a direction.
Not testable offline: liquidity (order book history), cmc_screener (CMC snapshots), orderflow_ws (operator:
untouched).

Usage: python research/v2/experiments/e11_watcher_role_retest.py
"""
from __future__ import annotations

import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e8_watcher_isolation as e8  # noqa: E402

OUT = e8.ROOT / "docs" / "v2" / "reports"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT"]
DIRECTIONAL = ["trend_mtf", "historical_candle", "market_pulse", "anomaly_ml", "funding_rate"]
MS = lambda y, m, d: int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)  # noqa: E731
FILES = [(MS(2026, 3, 1), MS(2026, 7, 1)), (MS(2026, 7, 1), MS(2026, 11, 1))]
WINDOWS = {"fresh": (MS(2026, 3, 1), MS(2026, 7, 1)), "dev": (MS(2026, 7, 1), MS(2026, 9, 1)),
           "old_val": (MS(2026, 9, 1), MS(2026, 11, 1))}
HORIZONS = {"15m": 15, "1h": 60, "4h": 240}


class _NullSink:
    def __getattr__(self, name):
        return lambda *a, **k: None


def _run(args):
    kind, sym, start, end = args
    logging.disable(logging.WARNING)
    from domain.value_objects import Symbol
    from infrastructure.engines.engine_service import EngineService
    engine = EngineService()
    df = e8.klines(sym, start, end)
    fund = e8.funding(sym, start, end)
    w = e8.make_watcher(kind, sym)
    if hasattr(w, "forensic_sink"):
        w.forensic_sink = _NullSink()
    s = Symbol(sym)
    sig = np.zeros(len(df))
    ratio = np.full(len(df), np.nan)
    ft, fr = fund.fundingTime.values, fund.fundingRate.values
    last_j = -1
    for i, row in enumerate(df.itertuples(index=False)):
        fund_now = None
        if kind == "funding_rate":
            j = np.searchsorted(ft, row.ct, side="right") - 1
            if j < 0 or j == last_j:
                if j >= 0 and i:
                    sig[i] = sig[i - 1]
                continue
            last_j, fund_now = j, fr[j]
        p = e8.payload(kind, row, fund_now)
        if p is None:
            continue
        try:
            w.update_data(p)
            obs = w.analyze(s)
        except Exception:
            continue
        if obs is None:
            continue
        if kind == "volatility":
            ratio[i] = (obs.metadata or {}).get("vol_ratio", np.nan)
            continue
        obs.metadata = {**(obs.metadata or {}), "watcher_name": kind}
        it = engine.process_observation(obs)
        st = getattr(getattr(it, "signal_type", None), "name", "") if it is not None else ""
        sig[i] = 1.0 if st == "BUY" else -1.0 if st == "SELL" else 0.0
    return kind, sym, start, sig, ratio


def onsets(sig: np.ndarray, h: int) -> np.ndarray:
    prev = np.concatenate([[0.0], sig[:-1]])
    idx = np.flatnonzero((sig != 0) & (sig != prev))
    keep, last = [], -10**9
    for i in idx:
        if i - last >= h:
            keep.append(i)
            last = i
    return np.asarray(keep, dtype=int)


def main() -> None:
    for s in SYMBOLS:
        for a, b in FILES:
            e8.klines(s, a, b)
            e8.funding(s, a, b)
    jobs = [(k, s, a, b) for k in DIRECTIONAL + ["volatility"] for s in SYMBOLS for a, b in FILES]
    with ProcessPoolExecutor(8) as ex:
        results = list(ex.map(_run, jobs))
    data = {(s, a): e8.klines(s, a, b) for s in SYMBOLS for a, b in FILES}
    rows, vrows = [], []
    for kind in DIRECTIONAL:
        for hname, h in HORIZONS.items():
            ev = []
            for k, sym, start, sig, _ in results:
                if k != kind:
                    continue
                df = data[(sym, start)]
                c, t = df.c.values, df.t.values
                idx = onsets(sig, h)
                idx = idx[idx + h < len(c)]
                r = np.log(c[idx + h] / c[idx]) * 1e4
                ev.append(pd.DataFrame({"sym": sym, "t": t[idx], "sr": sig[idx] * r, "long": sig[idx] > 0}))
            ev = pd.concat(ev)
            for wname, (a, b) in WINDOWS.items():
                g = ev[(ev.t >= a) & (ev.t < b)]
                if len(g) < 2:
                    rows.append({"watcher": kind, "horizon": hname, "window": wname, "events": len(g)})
                    continue
                se = g.sr.std(ddof=1) / np.sqrt(len(g))
                per = g.groupby("sym").sr.mean()
                rows.append({"watcher": kind, "horizon": hname, "window": wname, "events": len(g),
                             "events_per_sym_day": round(len(g) / len(SYMBOLS) / ((b - a) / 864e5), 2),
                             "long_share": round(g.long.mean(), 2), "mean_bps": round(g.sr.mean(), 2),
                             "t_stat": round(g.sr.mean() / se, 2) if se > 0 else None,
                             "hit_rate": round((g.sr > 0).mean(), 3),
                             "symbols_positive": f"{int((per > 0).sum())}/{len(per)}"})
    for k, sym, start, _, ratio in results:
        if k != "volatility":
            continue
        df = data[(sym, start)]
        lr = np.diff(np.log(df.c.values), prepend=np.nan)
        s = pd.Series(lr)
        nxt = s[::-1].rolling(60).std()[::-1].shift(-1)            # realized vol of the next 60 bars
        base = s.rolling(1440).std()                                 # trailing 24h baseline (causal)
        state = np.where(ratio >= 1.5, "expansion", np.where(ratio <= 0.67, "compression",
                                                             np.where(np.isnan(ratio), "", "normal")))
        vrows.append(pd.DataFrame({"t": df.t.values, "state": state, "ratio": ratio,
                                   "next_over_base": (nxt / base).values}))
    v = pd.concat(vrows).dropna()
    v = v[v.state != ""]
    for wname, (a, b) in WINDOWS.items():
        g = v[(v.t >= a) & (v.t < b)].iloc[::60]                      # hourly samples
        for st, gg in g.groupby("state"):
            rows.append({"watcher": "volatility", "horizon": "next_1h_vol", "window": wname, "events": len(gg),
                         "state": st, "next_vol_over_24h_base": round(gg.next_over_base.mean(), 3)})
        if len(g) > 10:
            rows.append({"watcher": "volatility", "horizon": "next_1h_vol", "window": wname, "events": len(g),
                         "state": "spearman(ratio,next)",
                         "next_vol_over_24h_base": round(g.ratio.corr(g.next_over_base, method="spearman"), 3)})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "E11_watcher_role_retest.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(r.to_string(index=False))


if __name__ == "__main__":
    main()
