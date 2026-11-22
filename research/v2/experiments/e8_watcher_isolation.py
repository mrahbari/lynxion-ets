"""E8 — each platform watcher tested in isolation, through the real Engine interpretation.

Question: does a single watcher's direction (as the live EngineService interprets it) predict the
next 15m / 1h / 4h return? One watcher at a time, no fusion, no strategy.

Method (causal):
  * Data: Binance USDT-M 1m klines (live watchers are refreshed every ~30s, so 1m bars are the
    closest offline cadence), funding history from /fapi/v1/fundingRate.
  * Each watcher instance gets exactly the payload shape its update_data() reads, only from bars
    already closed (and the latest funding already published) at decision time t.
  * Observation -> EngineService.process_observation -> signal_type BUY=+1 / SELL=-1 / else 0.
  * Forward return from close(t) to close(t+h). Non-overlapping samples (every h bars) for the
    t-statistics. Costs are NOT deducted; the 10 bp round-trip taker cost is shown for reference.
  * Universe: 10 liquid perps (survivorship caveat: chosen today).
Not testable offline: liquidity (needs order-book history), cmc_screener (CMC snapshots),
orderflow_ws (left untouched by operator decision).

Usage: python research/v2/experiments/e8_watcher_isolation.py [days]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "data" / "research_cache" / "e8"
OUT = ROOT / "docs" / "v2" / "reports"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT",
           "LINKUSDT", "SUIUSDT", "AAVEUSDT"]
HORIZONS = {"15m": 15, "1h": 60, "4h": 240}
WARMUP = 300


def _get(url: str):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2 + attempt * 3)
    raise RuntimeError(url)


def klines(sym: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{sym}_1m_{start_ms}_{end_ms}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t = [], start_ms
    while t < end_ms:
        batch = _get(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=1m&startTime={t}&limit=1500")
        if not batch:
            break
        rows += batch
        t = batch[-1][0] + 60_000
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns=list("tohlcv") + ["ct", "qv", "n", "tb", "tq", "x"])[list("tohlcv") + ["ct"]]
    df = df.astype({"o": float, "h": float, "l": float, "c": float, "v": float})
    df = df[df.t < end_ms].drop_duplicates("t").reset_index(drop=True)
    df.to_parquet(f)
    return df


def funding(sym: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    f = CACHE / f"{sym}_funding_{start_ms}_{end_ms}.json"
    if not f.exists():
        f.write_text(json.dumps(_get(
            f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&startTime={start_ms - 3 * 86_400_000}"
            f"&endTime={end_ms}&limit=1000")))
    d = pd.DataFrame(json.loads(f.read_text()))
    d["fundingTime"] = d.fundingTime.astype(np.int64)
    d["fundingRate"] = d.fundingRate.astype(float)
    return d.sort_values("fundingTime")


def make_watcher(kind: str, sym: str):
    from infrastructure.watchers.adapters.trend_mtf import TrendMTFWatcher
    from infrastructure.watchers.adapters.volatility import VolatilityWatcher
    from infrastructure.watchers.adapters.anomaly_ml import AnomalyMLWatcher
    from infrastructure.watchers.adapters.market_pulse import MarketPulseWatcher
    from infrastructure.watchers.adapters.funding_rate import FundingRateWatcher
    from infrastructure.watchers.adapters.historical_candle import HistoricalCandleWatcherAdapter
    if kind == "historical_candle":
        from bootstrap.settings.loaders import load_settings
        w = HistoricalCandleWatcherAdapter(load_settings(), "historical_candle", sym)
    else:
        cls = {"trend_mtf": TrendMTFWatcher, "volatility": VolatilityWatcher, "anomaly_ml": AnomalyMLWatcher,
               "market_pulse": MarketPulseWatcher, "funding_rate": FundingRateWatcher}[kind]
        w = cls(kind, sym)
    w.enabled = True
    return w


def payload(kind: str, row, fund_now):
    if kind in ("trend_mtf", "volatility", "anomaly_ml"):
        return {"close": row.c, "open": row.o, "high": row.h, "low": row.l, "volume": row.v}
    if kind in ("market_pulse", "historical_candle"):
        return {"candle": {"open": row.o, "high": row.h, "low": row.l, "close": row.c, "volume": row.v,
                           "close_time": pd.Timestamp(row.ct, unit="ms", tz="UTC").to_pydatetime(),
                           "timestamp": pd.Timestamp(row.t, unit="ms", tz="UTC").to_pydatetime()}}
    if kind == "funding_rate":
        return {"funding_rate": fund_now} if fund_now is not None else None
    raise KeyError(kind)


def fusion_side(obs_type: str) -> float:
    """HierarchicalFusion direction rule (conflict_resolution._resolve_direction_conflicts)."""
    t = obs_type.lower()
    if any(k in t for k in ("buy", "positive", "bullish", "up", "trend_positive")):
        return 1.0
    if any(k in t for k in ("sell", "negative", "bearish", "down", "trend_negative")):
        return -1.0
    return 0.0


def run_watcher(kind: str, sym: str, df: pd.DataFrame, fund: pd.DataFrame, engine):
    from domain.value_objects import Symbol
    w = make_watcher(kind, sym)
    s = Symbol(sym)
    sig = np.zeros(len(df))
    fsig = np.zeros(len(df))
    ft, fr = fund.fundingTime.values, fund.fundingRate.values
    last_fund_idx = -1
    for i, row in enumerate(df.itertuples(index=False)):
        fund_now = None
        if kind == "funding_rate":
            j = np.searchsorted(ft, row.ct, side="right") - 1      # latest funding published <= bar close
            if j < 0 or j == last_fund_idx:
                if i >= WARMUP and j >= 0:
                    sig[i], fsig[i] = sig[i - 1], fsig[i - 1]      # funding unchanged: keep last reading
                continue
            last_fund_idx, fund_now = j, fr[j]
        p = payload(kind, row, fund_now)
        if p is None:
            continue
        try:
            w.update_data(p)
            if i < WARMUP:
                continue
            obs = w.analyze(s)
        except Exception:
            continue
        if obs is None:
            continue
        fsig[i] = fusion_side(obs.observation_type)
        if obs.metadata is None:
            obs.metadata = {}
        obs.metadata.setdefault("watcher_name", kind)
        it = engine.process_observation(obs)
        if it is None:
            continue
        st = getattr(it.signal_type, "name", str(it.signal_type))
        sig[i] = 1.0 if st == "BUY" else -1.0 if st == "SELL" else 0.0
    return sig, fsig


def evaluate(kind: str, frames: dict) -> list:
    out = []
    for hname, h in HORIZONS.items():
        per_sym, pooled = [], []
        for sym, (df, sig) in frames.items():
            c = df.c.values
            fwd = np.full(len(c), np.nan)
            fwd[:-h] = np.log(c[h:] / c[:-h]) * 1e4  # bps
            idx = np.arange(WARMUP, len(c) - h, h)     # non-overlapping
            s, r = sig[idx], fwd[idx]
            m = s != 0
            if m.sum() < 5:
                continue
            sr = s[m] * r[m]
            pooled.append(pd.DataFrame({"sym": sym, "t": idx[m], "sr": sr, "hit": sr > 0, "long": s[m] > 0}))
            per_sym.append(sr.mean())
        if not pooled:
            out.append({"watcher": kind, "horizon": hname, "n": 0})
            continue
        p = pd.concat(pooled).sort_values("t")
        half = len(p) // 2
        se = p.sr.std(ddof=1) / np.sqrt(len(p))
        out.append({
            "watcher": kind, "horizon": hname, "n": len(p),
            "coverage": round(len(p) / sum(len(np.arange(WARMUP, len(df) - h, h)) for df, _ in frames.values()), 3),
            "long_share": round(p.long.mean(), 3),
            "mean_signed_bps": round(p.sr.mean(), 2), "t_stat": round(p.sr.mean() / se, 2) if se else None,
            "hit_rate": round(p.hit.mean(), 3),
            "first_half_bps": round(p.sr.iloc[:half].mean(), 2), "second_half_bps": round(p.sr.iloc[half:].mean(), 2),
            "symbols_positive": f"{sum(x > 0 for x in per_sym)}/{len(per_sym)}",
            "beats_10bp_cost": bool(p.sr.mean() > 10),
        })
    return out


def main(days: int = 14) -> None:
    from infrastructure.engines.engine_service import EngineService
    import logging
    logging.disable(logging.WARNING)
    engine = EngineService()
    end_ms = (int(time.time() * 1000) // 3_600_000) * 3_600_000
    start_ms = end_ms - days * 86_400_000
    data = {s: (klines(s, start_ms, end_ms), funding(s, start_ms, end_ms)) for s in SYMBOLS}
    rows = []
    for kind in ["trend_mtf", "volatility", "anomaly_ml", "market_pulse", "historical_candle", "funding_rate"]:
        t0 = time.time()
        sigs = {s: run_watcher(kind, s, df, fund, engine) for s, (df, fund) in data.items()}
        for rule, k in (("engine", 0), ("fusion", 1)):
            res = evaluate(kind, {s: (data[s][0], sigs[s][k]) for s in data})
            for row in res:
                row["rule"] = rule
            rows += res
        print(f"{kind}: {time.time() - t0:.0f}s", flush=True)
    r = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    r.to_csv(OUT / "E8_watcher_isolation.csv", index=False)
    pd.set_option("display.width", 250)
    print(r.to_string(index=False))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
