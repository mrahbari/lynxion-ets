"""E49 — H1 funding-settlement flow (PRE-REGISTERED 2026-11-26; proposal EDGE_DISCOVERY_PROPOSAL_2026-11-26.md).

Mechanism: funding is paid only by positions open at the settlement stamp T. With large positive funding some longs
close just before T and reopen after (and cash-and-carry desks do the mirror), pushing price down into T and back up
after; mirrored for large negative funding.
Data: Binance 1h lake klines (settlements fall on hour boundaries, so the hour bar [T-1h, T) is the "pre" window and
[T, T+1h) the "post" window) and the real settlement times/rates from the funding lake. No new download needed.
Signal (known before T): the PREVIOUS settlement's rate of the same symbol (conservative; the live predicted rate
is close to it). Universe: perps with 30-day median quote volume >= $20M on the day; deciles are formed across the
symbols that settle at the same T (>= 20 symbols required).
Hypotheses (fixed signs):
  POST: top decile (largest positive rate) rises from T to T+1h; bottom decile falls. Trade: long top / short bottom
        decile, equal weight, open at T (after the stamp, no funding paid), close at T+1h.
  PRE:  top decile falls from T-1h to T; bottom rises. Trade: short top / long bottom, close exactly at T (no funding).
Costs: 2 x (5 bp fee + 2 bp slippage) per leg round trip. Report gross and net bp per leg-trade.
Control: identical construction at T+4h (an hour without a settlement for 8h symbols) -> isolates the stamp effect.
Windows: DEV 2022-01-01..2024-12-31; TEST 2025-01-01..2026-10-31 (read once). t clustered by settlement time.
Criteria (per proposal): reject if TEST gross < 5 bp or the sign is wrong; "execution aid" if gross >= 5 bp but
net <= 0 in TEST; "prospective shadow" if net >= +3 bp with t >= 2 in BOTH windows, >= 60 % of symbols with the
predicted sign, AND the effect exceeds the control by >= 5 bp gross.
Usage: cd research/v2 && python experiments/e49_funding_settlement_flow.py
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
H, DAY = 3_600_000, 86_400_000
T0 = int(pd.Timestamp("2022-01-01", tz="UTC").timestamp() * 1000)
SPLIT = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)
T1 = int(pd.Timestamp("2026-10-31", tz="UTC").timestamp() * 1000)
COST = 2 * (0.0005 + 0.0002)
EXCLUDE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "EURUSDT", "XAUTUSDT", "PAXGUSDT"}


def per_symbol(sym):
    kp, fp = pn.LAKE / "klines_1h" / f"{sym}.parquet", pn.LAKE / "funding" / f"{sym}.parquet"
    if not kp.exists() or not fp.exists():
        return None
    k = pd.read_parquet(kp, columns=["open_time", "open", "close", "quote_volume"]).drop_duplicates("open_time")
    k = k[(k.open_time >= T0 - 40 * DAY) & (k.open_time <= T1)].set_index("open_time").sort_index()
    if len(k) < 24 * 60:
        return None
    f = pd.read_parquet(fp, columns=["calc_time", "funding_rate"]).dropna().sort_values("calc_time")
    f["T"] = (f.calc_time // H) * H                         # settlement stamps sit on hour boundaries
    f["prev_rate"] = f.funding_rate.shift(1)
    f = f[(f["T"] >= T0) & (f["T"] <= T1)].dropna(subset=["prev_rate"])
    dqv = k.quote_volume.groupby(k.index // DAY).sum()
    adv = dqv.rolling(30, min_periods=20).median().shift(1)
    o, c = k.open, k.close
    rows = []
    for T, r in zip(f["T"].to_numpy(), f.prev_rate.to_numpy()):
        for tag, t in (("stamp", T), ("control", T + 4 * H)):
            if t - H not in k.index or t not in k.index:
                continue
            a = adv.get(t // DAY, np.nan)
            if not (a >= 20e6):
                continue
            rows.append({"sym": sym, "T": int(t), "tag": tag, "rate": float(r),
                         "pre": float(c[t - H] / o[t - H] - 1), "post": float(c[t] / o[t] - 1)})
    return pd.DataFrame(rows) if rows else None


def main():
    nps = set(json.load(open(pn.LAKE / "non_perpetual_symbols.json")))
    syms = [p.stem for p in (pn.LAKE / "klines_1h").glob("*.parquet") if p.stem.endswith("USDT")
            and p.stem not in nps and p.stem not in EXCLUDE]
    with ProcessPoolExecutor(8) as ex:
        parts = [x for x in ex.map(per_symbol, syms, chunksize=8) if x is not None]
    ev = pd.concat(parts, ignore_index=True)
    out = []
    for (tag, T), g in ev.groupby(["tag", "T"]):
        if len(g) < 20:
            continue
        lo, hi = g.rate.quantile(0.1), g.rate.quantile(0.9)
        top, bot = g[g.rate >= hi], g[g.rate <= lo]
        out.append({"tag": tag, "T": T, "post_gross": (top.post.mean() - bot.post.mean()) / 2,
                    "pre_gross": (-top.pre.mean() + bot.pre.mean()) / 2,
                    "top_syms": list(top.sym), "bot_syms": list(bot.sym),
                    "top_post": list(top.post), "bot_post": list(bot.post), "top_pre": list(top.pre), "bot_pre": list(bot.pre)})
    res = pd.DataFrame(out)
    res.drop(columns=["top_syms", "bot_syms", "top_post", "bot_post", "top_pre", "bot_pre"]).to_csv(
        ROOT / "data/research_cache/E49_settlement_flow.csv", index=False)
    print("events (stamp/control):", (res.tag == "stamp").sum(), (res.tag == "control").sum())
    summary = {}
    for tag in ("stamp", "control"):
        for win, m in (("DEV", res["T"] < SPLIT), ("TEST", res["T"] >= SPLIT)):
            x = res[(res.tag == tag) & m]
            for leg in ("post", "pre"):
                v = x[f"{leg}_gross"]
                t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
                # share of symbols with the predicted sign (top side for the leg)
                if leg == "post":
                    sym_r = pd.Series([r for L in x.top_post for r in L], index=[s for L in x.top_syms for s in L]).groupby(level=0).mean()
                    sym_r2 = -pd.Series([r for L in x.bot_post for r in L], index=[s for L in x.bot_syms for s in L]).groupby(level=0).mean()
                else:
                    sym_r = -pd.Series([r for L in x.top_pre for r in L], index=[s for L in x.top_syms for s in L]).groupby(level=0).mean()
                    sym_r2 = pd.Series([r for L in x.bot_pre for r in L], index=[s for L in x.bot_syms for s in L]).groupby(level=0).mean()
                share = float(pd.concat([sym_r, sym_r2]).gt(0).mean())
                summary[(tag, win, leg)] = {"n": len(v), "gross_bp": round(v.mean() * 1e4, 2), "net_bp": round((v.mean() - COST) * 1e4, 2),
                                            "t": round(float(t), 2), "sym_share": round(share, 3)}
                print(tag, win, leg, summary[(tag, win, leg)])
    for leg in ("post", "pre"):
        d, te = summary[("stamp", "DEV", leg)], summary[("stamp", "TEST", leg)]
        cd, ct = summary[("control", "DEV", leg)], summary[("control", "TEST", leg)]
        if te["gross_bp"] < 5:
            verdict = "REJECT"
        elif te["net_bp"] <= 0:
            verdict = "EXECUTION AID ONLY"
        else:
            verdict = "EXECUTION AID ONLY"
        if (d["net_bp"] >= 3 and te["net_bp"] >= 3 and d["t"] >= 2 and te["t"] >= 2 and d["sym_share"] >= 0.6
                and te["sym_share"] >= 0.6 and d["gross_bp"] - cd["gross_bp"] >= 5 and te["gross_bp"] - ct["gross_bp"] >= 5):
            verdict = "PROSPECTIVE SHADOW"
        print(f"{leg.upper()}: {verdict}")


if __name__ == "__main__":
    main()
