"""E9 — each platform strategy backtested ALONE over a long period with live-equivalent execution.

Per (strategy, symbol): a fresh strategy adapter is fed closed bars of its design timeframe one by
one (update_with_market_data -> generate_signal, the strategy's own hypothesis). When flat and a
signal appears at the close of bar t:
  * entry at the OPEN of bar t+1, 2 bp adverse slippage;
  * SL/TP = sanitize_sltp_levels(entry, side, setup SL, setup TP) — exactly what live sends;
  * exits on bar high/low, SL checked before TP (same-bar ambiguity -> SL);
  * live R-mode stop management (APM defaults): breakeven +0.15% at 1.5R, trail 1.5R behind the
    best price after 2R, moved on bar close, effective from the next bar;
  * 0.05% taker fee per side, 2 bp slippage on stop exits; PnL in R and in % of notional.
One position per symbol per strategy (live duplicate prevention). No lookahead: the adapter only
ever sees bars up to t.

Windows: DEV 2025-11-01..2026-06-30, HOLDOUT 2026-07-01..2026-10-31 (reported separately; the
decision rule is pre-registered in tasks/ROADMAP_V2.md, section S2).

Difference from live: live strategies are reached through evaluate_fused_signal (+ regime gate);
here the strategy's own generate_signal is tested, i.e. the setup logic itself.

Usage: python research/v2/experiments/e9_strategy_backtest.py [strategy ...]
"""
from __future__ import annotations

import json
import logging
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "data" / "research_cache" / "e9"
OUT = ROOT / "docs" / "v2" / "reports"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT",
           "ADAUSDT", "LTCUSDT"]
START = datetime(2025, 10, 1, tzinfo=timezone.utc)      # Oct = warm-up only
DEV_START = datetime(2025, 11, 1, tzinfo=timezone.utc)
HOLDOUT_START = datetime(2026, 7, 1, tzinfo=timezone.utc)
END = datetime(2026, 11, 1, tzinfo=timezone.utc)
FEE, SLIP = 0.0005, 0.0002
BE_R, BE_BUF, TRAIL_AFTER_R, TRAIL_R = 1.5, 0.0015, 2.0, 1.5
TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}

STRATEGIES = {  # name -> (adapter import path, class, design timeframe)
    "trend_following": ("infrastructure.strategies.adapters.trend_follow_strategy_adapter", "TrendFollowStrategyAdapter", "1h"),
    "vwap_reversal": ("infrastructure.strategies.adapters.vwap_reversal_strategy_adapter", "VWAPReversalStrategyAdapter", "5m"),
    "oi_footprint": ("infrastructure.strategies.adapters.oi_footprint_strategy_adapter", "OIFootprintStrategyAdapter", "1h"),
    "mean_reversion": ("infrastructure.strategies.adapters.mean_reversion_strategy_adapter", "MeanReversionStrategyAdapter", "1h"),
    "mtf_trend": ("infrastructure.strategies.adapters.mtf_trend_strategy_adapter", "MTFTrendStrategyAdapter", "15m"),
    "breakout": ("infrastructure.strategies.adapters.breakout_strategy_adapter", "BreakoutStrategyAdapter", "15m"),
    "liquidity": ("infrastructure.strategies.adapters.liquidity_strategy_adapter", "LiquidityStrategyAdapter", "5m"),
    "volatility_breakout": ("infrastructure.strategies.strategy_adapters", "VolatilityBreakoutStrategy", "15m"),
}


def klines(sym: str, tf: str) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{sym}_{tf}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    rows, t = [], int(START.timestamp() * 1000)
    end = int(END.timestamp() * 1000)
    while t < end:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}"
                                            f"&interval={tf}&startTime={t}&limit=1500", timeout=30) as r:
                    batch = json.loads(r.read())
                break
            except Exception:
                time.sleep(3 + 3 * attempt)
        else:
            raise RuntimeError(sym)
        if not batch:
            break
        rows += batch
        t = batch[-1][0] + TF_MS[tf]
        time.sleep(0.12)
    df = pd.DataFrame(rows).iloc[:, :6]
    df.columns = ["t", "o", "h", "l", "c", "v"]
    df = df.astype({"o": float, "h": float, "l": float, "c": float, "v": float})
    df = df[df.t < end].drop_duplicates("t").reset_index(drop=True)
    df.to_parquet(f)
    return df


def run(args) -> list:
    name, sym = args
    logging.disable(logging.WARNING)
    import importlib
    from domain.value_objects import Symbol
    from shared.utils import sanitize_sltp_levels
    mod, cls, tf = STRATEGIES[name]
    adapter = getattr(importlib.import_module(mod), cls)({})
    df = klines(sym, tf)
    s = Symbol(sym)
    o, h, l, c, t = (df[k].values for k in ("o", "h", "l", "c", "t"))
    trades, pos, pending = [], None, None
    for i in range(len(df)):
        # 1) open a pending entry at this bar's open
        if pending is not None and pos is None:
            side = pending["side"]
            sgn = 1.0 if side == "BUY" else -1.0
            entry = o[i] * (1 + sgn * SLIP)
            sl, tp = sanitize_sltp_levels(entry_price=entry, side=side, stop_loss=pending["sl"],
                                          take_profit=pending["tp"])
            if sl > 0 and tp > 0:
                pos = {"side": side, "sgn": sgn, "entry": entry, "sl": sl, "tp": tp, "risk": abs(entry - sl),
                       "peak": entry, "t_in": int(t[i]), "be": False}
            pending = None
        # 2) manage an open position on this bar (stop active from bar open, SL first)
        if pos is not None:
            sgn = pos["sgn"]
            hit_sl = (l[i] <= pos["sl"]) if sgn > 0 else (h[i] >= pos["sl"])
            hit_tp = (h[i] >= pos["tp"]) if sgn > 0 else (l[i] <= pos["tp"])
            exit_px, why = None, None
            if hit_sl:
                gap = (o[i] < pos["sl"]) if sgn > 0 else (o[i] > pos["sl"])   # gapped through the stop
                exit_px = (o[i] if gap else pos["sl"]) * (1 - sgn * SLIP)
                why = "BE/TRAIL" if pos["be"] else "SL"
            elif hit_tp:
                exit_px, why = pos["tp"], "TP"
            if exit_px is not None:
                gross = sgn * (exit_px - pos["entry"]) / pos["entry"]
                net = gross - 2 * FEE
                trades.append({"strategy": name, "symbol": sym, "side": pos["side"], "t_in": pos["t_in"],
                               "t_out": int(t[i]), "ret": net, "R": net * pos["entry"] / pos["risk"],
                               "exit": why, "sl_pct": pos["risk"] / pos["entry"]})
                pos = None
            else:
                pos["peak"] = max(pos["peak"], h[i]) if sgn > 0 else min(pos["peak"], l[i])
                mfe = sgn * (pos["peak"] - pos["entry"])
                target = None
                if mfe >= BE_R * pos["risk"]:
                    target = pos["entry"] * (1 + sgn * BE_BUF)
                if mfe >= TRAIL_AFTER_R * pos["risk"]:
                    trail = pos["peak"] - sgn * TRAIL_R * pos["risk"]
                    target = trail if target is None or sgn * (trail - target) > 0 else target
                if target is not None:
                    target = min(target, c[i] * 0.998) if sgn > 0 else max(target, c[i] * 1.002)
                    if sgn * (target - pos["sl"]) > 0:
                        pos["sl"], pos["be"] = target, True
        # 3) the strategy sees bar i (closed) and may signal for bar i+1
        bar = {"open": o[i], "high": h[i], "low": l[i], "close": c[i], "volume": float(df.v.values[i]),
               "timestamp": datetime.fromtimestamp(t[i] / 1000, tz=timezone.utc).replace(tzinfo=None)}
        adapter.update_with_market_data(bar)
        if pos is None and t[i] >= int(DEV_START.timestamp() * 1000) - 1:
            try:
                sig = adapter.generate_signal(s)
            except Exception:
                sig = None
            if sig is not None:
                st = getattr(getattr(sig, "signal_type", None), "name", "")
                setup = (sig.metadata or {}).get("setup")
                if st in ("BUY", "SELL") and setup is not None:
                    pending = {"side": st, "sl": float(setup.stop_loss_level), "tp": float(setup.take_profit_level)}
    return trades


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows = []
    hold = int(HOLDOUT_START.timestamp() * 1000)
    for (name, window), g in tr.assign(window=np.where(tr.t_in >= hold, "holdout", "dev")).groupby(["strategy", "window"]):
        g = g.sort_values("t_in")
        wins, losses = g.ret[g.ret > 0].sum(), -g.ret[g.ret < 0].sum()
        half = len(g) // 2
        months = (g.t_in.max() - g.t_in.min()) / 2.6e9 if len(g) > 1 else 1
        rows.append({"strategy": name, "window": window, "trades": len(g),
                     "trades_per_month": round(len(g) / max(months, 1), 1),
                     "win_rate": round((g.ret > 0).mean(), 3), "PF": round(wins / losses, 2) if losses else np.inf,
                     "mean_R": round(g.R.mean(), 3), "mean_ret_bps": round(g.ret.mean() * 1e4, 1),
                     "first_half_R": round(g.R.iloc[:half].mean(), 3), "second_half_R": round(g.R.iloc[half:].mean(), 3),
                     "symbols_positive": f"{int((g.groupby('symbol').ret.sum() > 0).sum())}/{g.symbol.nunique()}",
                     "long_share": round((g.side == "BUY").mean(), 2),
                     "mean_R_long": round(g[g.side == "BUY"].R.mean(), 3), "mean_R_short": round(g[g.side == "SELL"].R.mean(), 3),
                     "median_sl_pct": round(g.sl_pct.median() * 100, 2)})
    return pd.DataFrame(rows)


def main(names) -> None:
    for name in names:
        for sym in SYMBOLS:
            klines(sym, STRATEGIES[name][2])
    jobs = [(n, s) for n in names for s in SYMBOLS]
    with ProcessPoolExecutor() as ex:
        results = list(ex.map(run, jobs))
    tr = pd.DataFrame([t for r in results for t in r])
    OUT.mkdir(parents=True, exist_ok=True)
    tr.to_csv(OUT / "E9_strategy_backtest_trades.csv", index=False)
    s = summarize(tr)
    s.to_csv(OUT / "E9_strategy_backtest_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:] or list(STRATEGIES))
