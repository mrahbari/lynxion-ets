"""R31 evaluation — outcomes of the logged unlock-short shadow entries under the PRE-REGISTERED rule (2026-11-26).

Rule (docs/v2/reports/R31_unlock_shadow_prereg_2026-11-26.md): short the token at the close of T-30, hedged long
50 % BTC + 50 % ETH; stop when a daily high reaches entry x 1.20 (exit at the stop price); else exit at the close of
T+14. Net = -token return + hedge return - 4 x 7 bp + funding received on the short - funding paid on the hedge.
Decision only at >= 40 closed events or on/after 2027-06-30; before that only counts are printed (no peeking).
Usage: cd research/v2 && python experiments/r31_unlock_shadow_eval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from live import binance_live_panel as lp  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "data" / "v2_live" / "unlock_shadow.jsonl"
STOP, COST, N_DECIDE = 0.20, 4 * (0.0005 + 0.0002), 40
DECIDE_DATE = pd.Timestamp("2027-06-30", tz="UTC")
DAY = 86_400_000


def bars(sym, start, end):
    k = lp._get(f"/fapi/v1/klines?symbol={sym}&interval=1d&startTime={int(start.timestamp()*1000)}"
                f"&endTime={int(end.timestamp()*1000)}&limit=60")
    return pd.DataFrame([{"t": pd.Timestamp(int(r[0]), unit="ms", tz="UTC"), "high": float(r[2]), "close": float(r[4])}
                         for r in k]).set_index("t")


def funding(sym, start, end):
    d = lp._get(f"/fapi/v1/fundingRate?symbol={sym}&startTime={int(start.timestamp()*1000)}"
                f"&endTime={int(end.timestamp()*1000)}&limit=1000")
    return float(sum(float(x["fundingRate"]) for x in d))


def outcome(e: dict) -> dict | None:
    T = pd.Timestamp(e["T"], tz="UTC")
    entry_day = pd.Timestamp(e["entry_day"], tz="UTC")
    exit_day = T + pd.Timedelta(days=14)
    if pd.Timestamp.now(tz="UTC") < exit_day + pd.Timedelta(days=1):
        return None
    tok = bars(e["sym"], entry_day + pd.Timedelta(days=1), exit_day)
    stop_px = e["entry"] * (1 + STOP)
    hit = tok[tok.high >= stop_px]
    end_day = hit.index[0] if len(hit) else exit_day
    tok_exit = stop_px if len(hit) else float(tok.close.loc[exit_day])
    hedge = []
    for s, p0 in (("BTCUSDT", e["btc"]), ("ETHUSDT", e["eth"])):
        hedge.append(float(bars(s, end_day, end_day).close.iloc[-1]) / p0 - 1)
    t0, t1 = entry_day + pd.Timedelta(days=1), end_day + pd.Timedelta(days=1)
    f_tok = funding(e["sym"], t0, t1)
    f_hedge = 0.5 * (funding("BTCUSDT", t0, t1) + funding("ETHUSDT", t0, t1))
    net = -(tok_exit / e["entry"] - 1) + float(np.mean(hedge)) - COST + f_tok - f_hedge
    return {**e, "stopped": bool(len(hit)), "exit_day": str(end_day.date()), "net": net}


def main():
    ev = [json.loads(x) for x in LOG.read_text().splitlines() if x.strip()] if LOG.exists() else []
    closed = [o for o in (outcome(e) for e in ev) if o is not None]
    print(f"logged {len(ev)}, closed {len(closed)}")
    if len(closed) < N_DECIDE and pd.Timestamp.now(tz="UTC") < DECIDE_DATE:
        print("interim: counts only (pre-registered; no performance shown before the decision point)")
        return
    d = pd.DataFrame(closed)
    d["week"] = pd.to_datetime(d["T"]).dt.to_period("W")
    wk = d.groupby("week").net.mean()
    t = wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk))) if len(wk) > 1 else np.nan
    ok = d.net.mean() >= 0.02 and t >= 2 and (d.net > 0).mean() >= 0.55
    print({"n": len(d), "mean_net": round(d.net.mean(), 4), "median": round(d.net.median(), 4), "t_week": round(float(t), 2),
           "pos": round(float((d.net > 0).mean()), 3), "stopped": round(float(d.stopped.mean()), 3)})
    print("R31", "PASS (candidate for operator)" if ok else "FAIL")
    d.to_csv(ROOT / "docs/v2/reports/R31_unlock_shadow_outcomes.csv", index=False)


if __name__ == "__main__":
    main()
