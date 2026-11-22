"""E8b — re-test each watcher AFTER the feeding/interpretation fixes, on a fresh period.

Dev window 2026-07-01..2026-08-31 (used for any judgement), validation 2026-09-01..2026-10-31
(read once). Neither window was used in E8 (which used the last 21 days). Same causal method as
E8: each watcher gets only closed 1m bars (and the latest published funding), its observation is
mapped by the live Engine rule and by the live Fusion keyword rule, scored against forward
15m/1h/4h returns on non-overlapping samples. Gross of costs (round trip ~10 bp shown).

Usage: python research/v2/experiments/e8b_watcher_retest.py
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

ROOT = e8.ROOT
OUT = ROOT / "docs" / "v2" / "reports"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT"]
WATCHERS = ["trend_mtf", "volatility", "anomaly_ml", "market_pulse", "historical_candle", "funding_rate"]
START = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)
SPLIT = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
END = int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)


class _NullSink:
    def __getattr__(self, name):
        return lambda *a, **k: None


def _job(args):
    kind, sym = args
    logging.disable(logging.WARNING)
    from infrastructure.engines.engine_service import EngineService
    orig = e8.make_watcher

    def make(k, s):
        w = orig(k, s)
        if hasattr(w, "forensic_sink"):
            w.forensic_sink = _NullSink()
        return w

    e8.make_watcher = make
    df = e8.klines(sym, START, END)
    fund = e8.funding(sym, START, END)
    sig, fsig = e8.run_watcher(kind, sym, df, fund, EngineService())
    return kind, sym, sig, fsig


def score(frames: dict, window: str) -> list:
    out = []
    for hname, h in e8.HORIZONS.items():
        pooled = []
        for sym, (df, sig) in frames.items():
            c, t = df.c.values, df.t.values
            idx = np.arange(e8.WARMUP, len(c) - h, h)
            idx = idx[(t[idx] < SPLIT) if window == "dev" else (t[idx] >= SPLIT)]
            r = np.log(c[idx + h] / c[idx]) * 1e4
            s = sig[idx]
            m = s != 0
            if m.sum():
                pooled.append(pd.DataFrame({"sym": sym, "t": t[idx][m], "sr": s[m] * r[m],
                                            "rd": s[m] * (r[m] - r.mean()), "long": s[m] > 0}))
        if not pooled:
            out.append({"horizon": hname, "window": window, "n": 0})
            continue
        p = pd.concat(pooled)
        se = p.sr.std(ddof=1) / np.sqrt(len(p)) if len(p) > 1 else np.nan
        per_sym = p.groupby("sym").sr.mean()
        out.append({"horizon": hname, "window": window, "n": len(p), "long_share": round(p.long.mean(), 3),
                    "mean_bps": round(p.sr.mean(), 2), "demeaned_bps": round(p.rd.mean(), 2),
                    "t_stat": round(p.sr.mean() / se, 2) if se else None,
                    "hit_rate": round((p.sr > 0).mean(), 3),
                    "symbols_positive": f"{int((per_sym > 0).sum())}/{len(per_sym)}"})
    return out


def main() -> None:
    for s in SYMBOLS:  # download serially (rate limits), compute in parallel
        e8.klines(s, START, END)
        e8.funding(s, START, END)
    jobs = [(k, s) for k in WATCHERS for s in SYMBOLS]
    with ProcessPoolExecutor() as ex:
        results = list(ex.map(_job, jobs))
    data = {s: e8.klines(s, START, END) for s in SYMBOLS}
    rows = []
    for kind in WATCHERS:
        for rule, k in (("engine", 2), ("fusion", 3)):
            frames = {r[1]: (data[r[1]], r[k]) for r in results if r[0] == kind}
            for window in ("dev", "validation"):
                for row in score(frames, window):
                    rows.append({"watcher": kind, "rule": rule, **row})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "E8b_watcher_retest.csv", index=False)
    pd.set_option("display.width", 250)
    print(r[r.n > 0].to_string(index=False))


if __name__ == "__main__":
    main()
