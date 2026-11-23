"""E18 — watcher validity harness (roadmap E16-W0): grade each watcher on its OWN claim.

Replays historical closed 1m bars through the live watcher classes exactly as MonitoringAnalysisService
feeds them (payload with 'candle' incl. open/close time), asks for an observation every STEP minutes,
and scores what the watcher claims to describe or predict (not trade PnL).

Pre-registered claims and pass rules (fixed before any run, 2026-11-23). Forward windows start at the
bar AFTER the observation (no overlap with inputs). DEV 2025-11-01..2026-06-30, HOLDOUT 2026-07-01..10-31.
  volatility  expansion/compression describe the coming hour: fwd_vol = std(next 60 1m returns) /
              std(previous 1440). PASS: mean fwd_vol(expansion) >= 1.2 x normal AND
              mean fwd_vol(compression) <= 0.85 x normal.
  trend_mtf   an aligned trend continues: signed fwd return over the next 4 h (sign of the label).
              PASS: mean signed fwd > 0 with t >= 2, hit rate >= 52 %, n >= 100.
  market_pulse strong momentum continues over the next 15 min (signed fwd return of *_strong labels).
              PASS: mean > 0 with t >= 2, n >= 100. (caution labels reported, no rule)
  anomaly_ml  an anomalous bar marks abnormal activity in the next 15 min: fwd_vol15 = std(next 15
              returns) / std(previous 240). PASS: mean fwd_vol15(anomaly) >= 1.3 x normal.
  historical_candle a reversal pattern reverses: signed fwd return over the next 1 h in the pattern
              direction. PASS: mean > 0 with t >= 2, n >= 100.
  Null calibration (all): share of non-neutral labels on simulated random walks, reported (<= ~10 %).
Grade per watcher: PASS on DEV and HOLDOUT -> validated claim; otherwise the claim is not supported.

Usage: python research/v2/experiments/e18_watcher_validity.py [watcher ...] [--symbols BTCUSDT,ETHUSDT]
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import e9_strategy_backtest as e9  # noqa: E402

OUT = e9.OUT
DEV0 = int(datetime(2025, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)
HOLD0 = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1000)
M = 60_000
STEP = 15                      # analyse every 15 closed 1m bars
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]


def make(name: str, sym: str):
    if name == "volatility":
        from infrastructure.watchers.adapters.volatility import VolatilityWatcher
        return VolatilityWatcher("volatility", sym)
    if name == "trend_mtf":
        from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher

        class _Sink:
            def log_watcher_observation(self, **_k):
                pass
        return TrendMTFWatcher("trend_mtf", sym, forensic_sink=_Sink())
    if name == "market_pulse":
        from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
        return MarketPulseWatcher("market_pulse", sym)
    if name == "anomaly_ml":
        from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
        return AnomalyMLWatcher("anomaly_ml", sym)
    if name == "historical_candle":
        from bootstrap.settings.loaders import load_settings
        from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
        return HistoricalCandleWatcherAdapter(load_settings(), "historical_candle", sym)
    raise ValueError(name)


def payload(row) -> dict:
    t = int(row.t)
    o, h, l, c, v = float(row.o), float(row.h), float(row.l), float(row.c), float(row.v)
    opened = datetime.fromtimestamp(t / 1000)
    return {"open": o, "high": h, "low": l, "close": c, "volume": v, "price": c, "timestamp": t,
            "candle": {"open": o, "high": h, "low": l, "close": c, "volume": v, "timestamp": opened,
                       "close_time": datetime.fromtimestamp(t / 1000 + 60)}}


def replay(name: str, sym: str) -> pd.DataFrame:
    k = e9.klines(sym, "1m").sort_values("t").reset_index(drop=True)
    w = make(name, sym)
    rows = []
    for i, row in enumerate(k.itertuples(index=False)):
        w.update_data(payload(row))
        if i % STEP == STEP - 1 and int(row.t) >= DEV0 - M:
            try:
                obs = w.analyze(w.symbol)
            except Exception:  # noqa: BLE001
                obs = None
            if obs is not None:
                rows.append((i, int(row.t), obs.observation_type, float(obs.observation_value),
                             float(obs.confidence.value)))
    obs = pd.DataFrame(rows, columns=["i", "t", "label", "value", "conf"])
    lr = np.log(k.c.to_numpy())
    r = np.diff(lr, prepend=lr[0])
    s = pd.Series(r)
    obs["fwd_ret_15"] = [lr[min(i + 15, len(lr) - 1)] - lr[i] for i in obs.i]
    obs["fwd_ret_60"] = [lr[min(i + 60, len(lr) - 1)] - lr[i] for i in obs.i]
    obs["fwd_ret_240"] = [lr[min(i + 240, len(lr) - 1)] - lr[i] for i in obs.i]
    fwd60 = s[::-1].rolling(60).std()[::-1].shift(-1)
    fwd15 = s[::-1].rolling(15).std()[::-1].shift(-1)
    base1440 = s.rolling(1440).std()
    base240 = s.rolling(240).std()
    obs["fwd_vol"] = (fwd60 / base1440).to_numpy()[obs.i]
    obs["fwd_vol15"] = (fwd15 / base240).to_numpy()[obs.i]
    obs["symbol"] = sym
    return obs


def tstat(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std(ddof=1) > 0 else 0.0


def sign_of(label: str) -> int:
    lab = label.lower()
    if any(k in lab for k in ("positive", "bullish", "upward")):
        return 1
    if any(k in lab for k in ("negative", "bearish", "downward")):
        return -1
    return 0


def score(name: str, d: pd.DataFrame) -> dict:
    out = {"n_obs": len(d), "labels": d.label.value_counts().to_dict()}
    if name == "volatility":
        g = d.groupby("label").fwd_vol.mean()
        nrm = g.get("volatility_normal", np.nan)
        out.update(fwd_vol=g.round(3).to_dict(),
                   passed=bool(g.get("volatility_expansion", 0) >= 1.2 * nrm and
                               g.get("volatility_compression", 9) <= 0.85 * nrm))
    elif name == "anomaly_ml":
        an = d[d.label.str.startswith("anomaly_") & (d.label != "anomaly_normal")].fwd_vol15
        nm = d[d.label == "anomaly_normal"].fwd_vol15
        out.update(n_anomaly=len(an), fwd_vol15_anomaly=round(float(an.mean()), 3),
                   fwd_vol15_normal=round(float(nm.mean()), 3),
                   passed=bool(len(an) > 0 and an.mean() >= 1.3 * nm.mean()))
    else:
        col, sel = {"trend_mtf": ("fwd_ret_240", lambda x: x.label.isin(["trend_positive", "trend_negative"])),
                    "market_pulse": ("fwd_ret_15", lambda x: x.label.str.endswith("_strong")),
                    "historical_candle": ("fwd_ret_60", lambda x: x.label.str.startswith("candle_reversal"))}[name]
        e = d[sel(d)]
        signed = e[col] * e.label.map(sign_of)
        out.update(n_events=len(e), mean_signed_bp=round(float(signed.mean() * 1e4), 2) if len(e) else None,
                   t=round(tstat(signed), 2), hit=round(float((signed > 0).mean()), 3) if len(e) else None)
        ok = len(e) >= 100 and signed.mean() > 0 and tstat(signed) >= 2
        if name == "trend_mtf":
            ok = ok and (signed > 0).mean() >= 0.52
        out["passed"] = bool(ok)
        if name == "market_pulse":
            c = d[d.label.str.contains("caution")]
            cs = c.fwd_ret_15 * c.label.map(sign_of)
            out.update(caution_n=len(c), caution_mean_signed_bp=round(float(cs.mean() * 1e4), 2) if len(c) else None,
                       caution_t=round(tstat(cs), 2))
    return out


def main() -> None:
    logging.disable(logging.CRITICAL)
    ap = argparse.ArgumentParser()
    ap.add_argument("watchers", nargs="*", default=["volatility", "trend_mtf", "market_pulse", "anomaly_ml",
                                                    "historical_candle"])
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    a = ap.parse_args()
    results = []
    for name in a.watchers:
        d = pd.concat([replay(name, s) for s in a.symbols.split(",")])
        d.to_parquet(e9.CACHE / f"E18_{name}_obs.parquet")
        for period, part in (("DEV", d[(d.t >= DEV0) & (d.t < HOLD0)]), ("HOLDOUT", d[d.t >= HOLD0])):
            res = {"watcher": name, "period": period, **score(name, part)}
            results.append(res)
            print(res, flush=True)
    pd.DataFrame(results).to_csv(OUT / "E18_watcher_validity.csv", index=False)


if __name__ == "__main__":
    main()
