"""E8c — does a watcher's reported confidence carry information? (layer-2 calibration input)

For the watchers the Fusion confidence filter gates (market_pulse, historical_candle, trend_mtf,
volatility, anomaly_ml): distribution of reported confidence, and Fusion-rule signed forward return
by confidence quintile, DEV window only (2026-07..08). Same data/causality as E8b.
"""
from __future__ import annotations

import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e8_watcher_isolation as e8  # noqa: E402
import e8b_watcher_retest as b  # noqa: E402

WATCHERS = ["market_pulse", "historical_candle", "trend_mtf", "volatility", "anomaly_ml"]


def _job(args):
    kind, sym = args
    logging.disable(logging.WARNING)
    e8.RETURN_CONF = True
    from infrastructure.engines.engine_service import EngineService
    orig = e8.make_watcher

    def make(k, s):
        w = orig(k, s)
        if hasattr(w, "forensic_sink"):
            w.forensic_sink = b._NullSink()
        return w

    e8.make_watcher = make
    df = e8.klines(sym, b.START, b.END)
    sig, fsig, conf = e8.run_watcher(kind, sym, df, e8.funding(sym, b.START, b.END), EngineService())
    return kind, sym, fsig, conf


def main():
    jobs = [(k, s) for k in WATCHERS for s in b.SYMBOLS]
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(_job, jobs))
    rows = []
    for kind in WATCHERS:
        parts = []
        for k, sym, fsig, conf in res:
            if k != kind:
                continue
            df = e8.klines(sym, b.START, b.END)
            c, t = df.c.values, df.t.values
            h = 240
            idx = np.arange(e8.WARMUP, len(c) - h, 60)       # hourly samples, 4h forward
            idx = idx[t[idx] < b.SPLIT]                       # DEV only
            r = np.log(c[idx + h] / c[idx]) * 1e4
            parts.append(pd.DataFrame({"conf": conf[idx], "side": fsig[idx], "r": r}))
        d = pd.concat(parts).dropna()
        thr = {"market_pulse": .6, "historical_candle": .6, "trend_mtf": .55, "volatility": .55, "anomaly_ml": .7}[kind]
        rows.append({"watcher": kind, "q": "all", "conf_lo": d.conf.min(), "conf_hi": d.conf.max(),
                     "share_above_live_threshold": round((d.conf >= thr).mean(), 3)})
        sd = d[d.side != 0].copy()
        if len(sd) > 50:
            sd["q"] = pd.qcut(sd.conf.rank(method="first"), 5, labels=False)
            for q, g in sd.groupby("q"):
                rows.append({"watcher": kind, "q": int(q), "conf_lo": round(g.conf.min(), 3), "conf_hi": round(g.conf.max(), 3),
                             "n": len(g), "signed_4h_bps": round((g.side * g.r).mean(), 2)})
    out = pd.DataFrame(rows)
    out.to_csv(b.OUT / "E8c_confidence_calibration.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
