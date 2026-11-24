"""E20 — OIFootprint with REAL open interest (roadmap E16-U9).

Live OIFootprint never receives open interest, so its NGOI_SETUP always takes the volume-spike + RSI
proxy branch (E15: layer grade D). This replays the unchanged adapter through the E9 engine (1h bars,
next-bar-open entry, SL first on High/Low, fees + slippage, BE/trail) with Binance USDT-M 5-minute
open interest (data/research/oi_metrics) injected into each bar as ``open_interest``.

Causality: the OI value of a 1h bar is the last 5m snapshot whose create_time <= bar close - 5 min.
Symbols: those with both OI history and E9 klines: BTC, ETH, SOL, XRP, ADA. OI ends 2026-08-29, so
HOLDOUT = 2026-07-01..08-29.

Pre-registered (2026-11-24, before any run):
  PASS (real-OI variant): net mean R > 0 with n >= 30 on DEV AND on HOLDOUT.
  Comparison (no rule): the E9 proxy trades of oi_footprint on the same symbols / windows.
  Decision: PASS -> wire live OI into the buffer (BingX openInterest). FAIL -> retire OIFootprint
  (disabled in config, code kept), since the proxy branch has no edge either (E9).

Usage: python research/v2/experiments/e20_oi_footprint_real_oi.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402

ROOT = e9.ROOT
OI_DIR = ROOT / "data" / "research" / "oi_metrics" / "normalized"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
HOLD0 = int(e9.HOLDOUT_START.timestamp() * 1000)
OI_END = int(pd.Timestamp("2026-08-30", tz="UTC").timestamp() * 1000)


def oi_by_bar(sym: str, k: pd.DataFrame) -> dict:
    oi = pd.read_csv(OI_DIR / f"{sym}.csv.gz", usecols=["create_time", "sum_open_interest"])
    oi["ts"] = pd.to_datetime(oi.create_time, utc=True).astype("int64") // 1_000_000
    oi = oi.sort_values("ts")
    bars = pd.DataFrame({"t": k.t.astype("int64"), "avail": k.t.astype("int64") + 3_600_000 - 300_000})
    m = pd.merge_asof(bars.sort_values("avail"), oi[["ts", "sum_open_interest"]], left_on="avail",
                      right_on="ts", direction="backward")
    return dict(zip(m.t, m.sum_open_interest.astype(float).fillna(0.0)))


def main() -> None:
    from infrastructure.strategies.adapters import oi_footprint_strategy_adapter as mod
    from datetime import timezone
    cls = mod.OIFootprintStrategyAdapter
    base = cls.update_with_market_data
    rows = []
    for sym in SYMBOLS:
        k = e9.klines(sym, "1h")
        lut = oi_by_bar(sym, k)

        def patched(self, data, _lut=lut):
            if isinstance(data, dict):
                ts = int(data["timestamp"].replace(tzinfo=timezone.utc).timestamp() * 1000)
                data = {**data, "open_interest": _lut.get(ts, 0.0)}
            return base(self, data)
        cls.update_with_market_data = patched
        try:
            rows += e9.run(("oi_footprint", sym))
        finally:
            cls.update_with_market_data = base
    tr = pd.DataFrame(rows)
    tr = tr[tr.t_in < OI_END]
    tr.to_csv(e9.OUT / "E20_oi_footprint_trades.csv", index=False)
    proxy = pd.read_csv(e9.OUT / "E9_strategy_backtest_trades.csv")
    proxy = proxy[(proxy.strategy == "oi_footprint") & proxy.symbol.isin(SYMBOLS) & (proxy.t_in < OI_END)]
    out = []
    for name, d in (("real_oi", tr), ("proxy_E9", proxy)):
        for win, m in (("DEV", d.t_in < HOLD0), ("HOLDOUT", d.t_in >= HOLD0)):
            g = d[m]
            out.append({"variant": name, "window": win, "trades": len(g),
                        "mean_R": round(g.R.mean(), 3) if len(g) else None,
                        "win_rate": round((g.ret > 0).mean(), 3) if len(g) else None,
                        "mean_ret_bps": round(g.ret.mean() * 1e4, 1) if len(g) else None,
                        "long_share": round((g.side == "BUY").mean(), 2) if len(g) else None})
    r = pd.DataFrame(out)
    ok = r[r.variant == "real_oi"]
    r.attrs["passed"] = bool(((ok.trades >= 30) & (ok.mean_R > 0)).all())
    r.to_csv(e9.OUT / "E20_oi_footprint_summary.csv", index=False)
    print(r.to_string(index=False))
    print("PASS" if r.attrs["passed"] else "FAIL")


if __name__ == "__main__":
    main()
