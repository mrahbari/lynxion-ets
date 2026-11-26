"""E50 — H2 cross-venue funding dispersion, Binance vs Bybit (PRE-REGISTERED 2026-11-26).

Mechanism: leverage demand is segmented across venues; the same coin can pay different funding on Binance and Bybit
for days. Long the perp on the venue with LOWER funding and short it on the venue with HIGHER funding: price exposure
cancels (up to the venue price basis) and the funding spread is collected.
Data: Binance funding + 1h klines (lake), Bybit funding + 1h klines (data/lake/bybit_linear, free API), the top 60
Binance perps by 2025-26 volume that Bybit lists.
Rule (fixed): each UTC day D (00:00), spread = annualised difference of the funding SUMS over the previous 3 days
(Bybit - Binance) x 365/3. If |spread| >= 20 %/yr: open the pair at D (short the higher-funding venue, long the lower),
hold exactly 7 days, one open pair per symbol.
P&L per trade (fraction of one leg's notional): funding received on the short leg - funding paid on the long leg over
(D, D+7d] (each venue's real settlements) + price legs (long venue close ratio - short venue close ratio, 1h closes at
D and D+7d) - 4 x (5 bp fee + 2 bp slippage).
Capital: both legs margined at 1x -> capital = 2 x notional. Annual yield while invested = mean net x (365/7) / 2.
Windows: DEV 2022-01-01..2024-12-31; TEST 2025-01-01..2026-10-24 (read once). t clustered by trade start week.
Also reported: spread autocorrelation (lag 1 and 7 days), trades per year, share of time with >= 1 open pair,
worst price-basis loss on one trade.
PASS: mean net per trade >= +0.31 % (= 8 %/yr on 2x notional over 7 days) in BOTH windows, t >= 2 in both,
lag-1 spread autocorrelation >= 0.5 (persistence), worst single-trade basis loss > -3 %.
Decision: PASS -> prospective shadow with live funding from both venues (operator decision about a Bybit account).
Usage: cd research/v2 && python experiments/e50_cross_venue_funding.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BYB = ROOT / "data" / "lake" / "bybit_linear"
DAY = 86_400_000
D0, SPLIT, D1 = pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-10-24", tz="UTC")
COST, THR, HOLD, LOOK = 4 * (0.0005 + 0.0002), 0.20, 7, 3


def daily_funding(path):
    f = pd.read_parquet(path)
    s = pd.Series(f.funding_rate.to_numpy(), index=pd.to_datetime(f.calc_time, unit="ms", utc=True))
    return s


def closes(path):
    k = pd.read_parquet(path, columns=["open_time", "close"]).drop_duplicates("open_time")
    return pd.Series(k.close.to_numpy(), index=pd.to_datetime(k.open_time, unit="ms", utc=True)).sort_index()


def per_symbol(sym):
    paths = [pn.LAKE / "funding" / f"{sym}.parquet", pn.LAKE / "klines_1h" / f"{sym}.parquet",
             BYB / "funding" / f"{sym}.parquet", BYB / "klines_1h" / f"{sym}.parquet"]
    if not all(p.exists() for p in paths):
        return None, None
    fbn, pbn, fby, pby = daily_funding(paths[0]), closes(paths[1]), daily_funding(paths[2]), closes(paths[3])
    days = pd.date_range(max(D0, fby.index.min().ceil("D"), fbn.index.min().ceil("D")), D1, freq="D", tz="UTC")
    if len(days) < 60:
        return None, None
    cb = fbn.groupby(fbn.index.ceil("D")).sum()                         # settlements in (D-1, D]
    cy = fby.groupby(fby.index.ceil("D")).sum()
    look = (cy.reindex(days, fill_value=0).rolling(LOOK).sum() - cb.reindex(days, fill_value=0).rolling(LOOK).sum())
    spread = look * 365 / LOOK
    trades, busy = [], None
    for D in days:
        if busy is not None and D < busy:
            continue
        sp = spread.get(D, np.nan)
        if not np.isfinite(sp) or abs(sp) < THR:
            continue
        E = D + pd.Timedelta(days=HOLD)
        if E > D1 or D not in pbn.index or D not in pby.index or E not in pbn.index or E not in pby.index:
            continue
        # short the higher-funding venue
        short_by = sp > 0
        f_by = float(fby[(fby.index > D) & (fby.index <= E)].sum())
        f_bn = float(fbn[(fbn.index > D) & (fbn.index <= E)].sum())
        fund = (f_by - f_bn) if short_by else (f_bn - f_by)
        r_by, r_bn = pby[E] / pby[D] - 1, pbn[E] / pbn[D] - 1
        price = (r_bn - r_by) if short_by else (r_by - r_bn)
        trades.append({"sym": sym, "D": D, "spread": sp, "funding": fund, "price": price, "net": fund + price - COST})
        busy = E
    return pd.DataFrame(trades), spread.dropna()


def main():
    syms = sorted(p.stem for p in (BYB / "funding").glob("*.parquet"))
    tr, sp = [], {}
    for s in syms:
        t, spread = per_symbol(s)
        if t is not None:
            tr.append(t); sp[s] = spread
    ev = pd.concat(tr, ignore_index=True)
    ev.to_csv(ROOT / "data/research_cache/E50_cross_venue_trades.csv", index=False)
    ac1 = np.nanmedian([x.autocorr(1) for x in sp.values()])
    ac7 = np.nanmedian([x.autocorr(7) for x in sp.values()])
    print(f"symbols {len(sp)} | spread autocorr median lag1 {ac1:.2f} lag7 {ac7:.2f}")
    res = {}
    for win, m in (("DEV", ev.D < SPLIT), ("TEST", ev.D >= SPLIT)):
        x = ev[m]
        wk = x.groupby(x.D.dt.to_period("W")).net.mean()
        t = wk.mean() / (wk.std(ddof=1) / np.sqrt(len(wk))) if len(wk) > 2 else np.nan
        yrs = (min(D1, SPLIT if win == "DEV" else D1) - (D0 if win == "DEV" else SPLIT)).days / 365
        res[win] = {"trades": len(x), "per_year": round(len(x) / yrs, 1), "mean_net_pct": round(x.net.mean() * 100, 3),
                    "median_net_pct": round(x.net.median() * 100, 3), "funding_pct": round(x.funding.mean() * 100, 3),
                    "price_pct": round(x.price.mean() * 100, 3), "t_week": round(float(t), 2),
                    "worst_price_pct": round(x.price.min() * 100, 2), "win": round((x.net > 0).mean(), 3),
                    "yield_on_capital": round(x.net.mean() * 365 / HOLD / 2, 4)}
        print(win, res[win])
    ok = all(res[w]["mean_net_pct"] >= 0.31 and res[w]["t_week"] >= 2 and res[w]["worst_price_pct"] > -3 for w in res) and ac1 >= 0.5
    print("E50", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
