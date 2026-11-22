"""E7 — exit-policy replay on the platform's real entries.

Question: which stop-management policy (static / current APM breakeven+0.5% trail / R-based
breakeven+trail) gives the best net expectancy on the entries the platform actually took?

Method (no lookahead):
  * Entries: data/trade_journal.csv (Aug–Nov 2026), de-duplicated per symbol within 10 minutes.
  * Path: Binance USDT-M 1m klines for 24h after entry (time exit at 24h close).
  * Initial risk R = 2% of entry (the platform's sanitize default; strategy levels were
    unreliable — see the stale-buffer P0), TP per policy.
  * Within a bar the stop is checked before TP (SL priority); a stop moved because of a bar's
    high/low only becomes active from the NEXT bar.
  * Costs: 0.05% taker per side + 0.02% slippage on stop exits.

Usage: python research/v2/experiments/e7_exit_policy_replay.py [max_trades]
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
CACHE = ROOT / "data" / "research_cache" / "e7_klines"
OUT = ROOT / "docs" / "v2" / "reports"
FEE = 0.0005
SLIP = 0.0002
R = 0.02
HOLD_BARS = 1440


def klines(symbol: str, start_ms: int):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{symbol}_{start_ms}.json"
    if f.exists():
        return json.loads(f.read_text())
    url = (f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m"
           f"&startTime={start_ms}&limit={HOLD_BARS}")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read())
    except Exception:
        data = []
    f.write_text(json.dumps(data))
    time.sleep(0.25)
    return data


def simulate(path: np.ndarray, entry: float, is_long: bool, policy: dict) -> tuple[float, str]:
    """Return (net return as fraction of entry, exit reason)."""
    sgn = 1.0 if is_long else -1.0
    stop = entry * (1 - sgn * R)
    tp = entry * (1 + sgn * policy["tp_r"] * R) if policy.get("tp_r") else None
    peak = entry
    be_done = False
    for hi, lo, cl in path:
        # 1) exits on this bar with the stop that was active at bar open (SL first)
        adverse = lo if is_long else hi
        favour = hi if is_long else lo
        if (adverse <= stop) if is_long else (adverse >= stop):
            gross = sgn * (stop - entry) / entry
            return gross - 2 * FEE - SLIP, "SL" if not be_done else "TRAIL/BE"
        if tp is not None and ((favour >= tp) if is_long else (favour <= tp)):
            return sgn * (tp - entry) / entry - 2 * FEE, "TP"
        # 2) update management state from the completed bar (effective next bar)
        peak = max(peak, favour) if is_long else min(peak, favour)
        mfe = sgn * (peak - entry) / entry
        new_stop = stop
        if policy["kind"] == "apm":
            if mfe >= policy["be_trigger"]:
                be = entry * (1 + sgn * policy["be_buffer"])
                be_done = True
                new_stop = max(new_stop, be) if is_long else min(new_stop, be)
            if mfe >= policy["trail_trigger"]:
                cand = peak * (1 - sgn * policy["trail_dist"])
                cand = min(cand, cl * 0.997) if is_long else max(cand, cl * 1.003)
                locked = sgn * (cand - entry) / entry
                if locked >= policy["be_buffer"]:
                    new_stop = max(new_stop, cand) if is_long else min(new_stop, cand)
        elif policy["kind"] == "r":
            if policy.get("be_r") is not None and mfe >= policy["be_r"] * R:
                be = entry * (1 + sgn * policy["be_buffer"])
                be_done = True
                new_stop = max(new_stop, be) if is_long else min(new_stop, be)
            if policy.get("trail_after_r") is not None and mfe >= policy["trail_after_r"] * R:
                cand = peak * (1 - sgn * policy["trail_r"] * R)
                be_done = True
                new_stop = max(new_stop, cand) if is_long else min(new_stop, cand)
        stop = new_stop
    last = path[-1][2]
    return sgn * (last - entry) / entry - 2 * FEE, "TIME"


POLICIES = {
    "static_sl1R_tp1.75R": {"kind": "static", "tp_r": 1.75},
    "static_sl1R_tp3R": {"kind": "static", "tp_r": 3.0},
    # current platform (10x): BE at +0.7% price (7% ROE) to entry+0.35%, trail 0.5% after +1.0%
    "current_apm_tp1.75R": {"kind": "apm", "tp_r": 1.75, "be_trigger": 0.007, "be_buffer": 0.0035,
                            "trail_trigger": 0.010, "trail_dist": 0.005},
    "r_be1R_tp1.75R": {"kind": "r", "tp_r": 1.75, "be_r": 1.0, "be_buffer": 0.0015},
    "r_be1R_trail1R@1.5R_tp3R": {"kind": "r", "tp_r": 3.0, "be_r": 1.0, "be_buffer": 0.0015,
                                 "trail_after_r": 1.5, "trail_r": 1.0},
    "r_be1R_trail1R@1.5R_noTP": {"kind": "r", "tp_r": None, "be_r": 1.0, "be_buffer": 0.0015,
                                 "trail_after_r": 1.5, "trail_r": 1.0},
    "r_be0.5R_trail0.75R@1R_tp3R": {"kind": "r", "tp_r": 3.0, "be_r": 0.5, "be_buffer": 0.0015,
                                    "trail_after_r": 1.0, "trail_r": 0.75},
    "r_noBE_trail1R@1.5R_tp3R": {"kind": "r", "tp_r": 3.0, "be_r": None, "be_buffer": 0.0015,
                                 "trail_after_r": 1.5, "trail_r": 1.0},
    "r_be1.5R_trail1.5R@2R_tp1.75R": {"kind": "r", "tp_r": 1.75, "be_r": 1.5, "be_buffer": 0.0015,
                                      "trail_after_r": 2.0, "trail_r": 1.5},
    "r_be1.5R_trail1.5R@2R_tp2.75R": {"kind": "r", "tp_r": 2.75, "be_r": 1.5, "be_buffer": 0.0015,
                                      "trail_after_r": 2.0, "trail_r": 1.5},
    "r_be1.5R_trail1.5R@2R_tp4R": {"kind": "r", "tp_r": 4.0, "be_r": 1.5, "be_buffer": 0.0015,
                                   "trail_after_r": 2.0, "trail_r": 1.5},
}


def main(max_trades: int = 700) -> None:
    j = pd.read_csv(ROOT / "data" / "trade_journal.csv")
    j["ts"] = pd.to_datetime(j.entry_timestamp, utc=True, errors="coerce")
    j = j[(j.ts >= "2026-08-01") & j.entry_price.notna()].sort_values("ts")
    j = j[j.symbol.str.endswith("USDT")]
    j["gap"] = j.groupby("symbol").ts.diff().dt.total_seconds()
    j = j[(j.gap.isna()) | (j.gap > 600)]
    j = j.tail(max_trades)
    rows = []
    for t in j.itertuples():
        start = int(t.ts.timestamp() * 1000) // 60000 * 60000 + 60000  # first bar after entry
        k = klines(t.symbol, start)
        if len(k) < 60:
            continue
        path = np.array([[float(b[2]), float(b[3]), float(b[4])] for b in k])
        entry = float(k[0][1])  # next-bar open: realistic market entry
        is_long = str(t.side).upper() in ("BUY", "LONG")
        rec = {"symbol": t.symbol, "ts": t.ts.isoformat(), "long": is_long, "month": t.ts.strftime("%Y-%m")}
        for name, pol in POLICIES.items():
            ret, why = simulate(path, entry, is_long, pol)
            rec[name] = ret
            rec[name + "_why"] = why
        rows.append(rec)
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "E7_exit_policy_replay_trades.csv", index=False)
    summary = []
    for name in POLICIES:
        r = df[name] / R  # in R units
        wins, losses = r[r > 0].sum(), -r[r < 0].sum()
        mid = len(df) // 2  # rows are in entry-time order
        halves = [df[name].iloc[:mid].mean() / R, df[name].iloc[mid:].mean() / R]
        summary.append({
            "policy": name, "n": len(r), "mean_R": r.mean(), "median_R": r.median(),
            "win_rate": (r > 0).mean(), "PF": wins / losses if losses else np.inf,
            "total_R": r.sum(), "mean_R_first_half": halves[0], "mean_R_second_half": halves[1],
            "mean_R_long": (df[df.long][name] / R).mean(), "mean_R_short": (df[~df.long][name] / R).mean(),
            "exits": df[name + "_why"].value_counts().to_dict(),
        })
    s = pd.DataFrame(summary).sort_values("mean_R", ascending=False)
    s.to_csv(OUT / "E7_exit_policy_replay_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s.drop(columns=["exits"]).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    base = df["current_apm_tp1.75R"] / R
    print("\npaired vs current_apm (mean diff R, SE):")
    for name in POLICIES:
        d = df[name] / R - base
        print(f"  {name:32s} {d.mean():+.3f}  SE {d.std(ddof=1) / np.sqrt(len(d)):.3f}")
    for row in s.itertuples():
        print(row.policy, row.exits)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 700)
