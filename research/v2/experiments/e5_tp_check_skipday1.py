"""Robustness of e5_tp_check: TP may only trigger from day 2 (day-1 bar includes 1h before entry).

Same weekly simulation as e5_stop_check.py with the live 50% disaster stop, plus a per-name
take profit at +tp from entry (daily high/low; stop has priority if both hit the same day).
Exited names go flat until the next weekly rebalance (funding stops), extra 30 bp round trip.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn, backtest as bt
from strategies import xs_combo_v1 as S

p = pn.load_daily(1, "2019-10-01", "2024-12-31")
m = pn.universe_mask(p)
w = bt.rank_long_short(S.signal(p, m), m, frac=0.2, gross=1.0, min_names=30)
idx = p["close"].index
start = idx.get_indexer([pd.Timestamp("2020-01-01", tz="UTC")])[0]
px, hi, lo, fu = (p[k].values for k in ("exec_px", "high", "low", "funding_fwd"))
W = w.values
SL = 0.50
tps = [9.99, 0.20, 0.25, 0.30, 0.40]
res = {t: [] for t in tps}; hits = {t: 0 for t in tps}; dates = []
for t0 in range(start, len(idx) - 7, 7):
    wt = np.nan_to_num(W[t0]); names = np.nonzero(wt)[0]
    if len(names) == 0:
        continue
    dates.append(idx[t0]); e = px[t0, names]
    for tp in tps:
        pnl = 0.0
        for j, c in enumerate(names):
            ww = wt[c]; sg = np.sign(ww); ex = None; held = 7
            if np.isfinite(e[j]):
                for k in range(1, 8):
                    up, dn = hi[t0 + k, c] / e[j] - 1, lo[t0 + k, c] / e[j] - 1
                    adverse = dn if sg > 0 else -up
                    favour = up if sg > 0 else -dn
                    if np.isfinite(adverse) and adverse <= -SL:
                        ex = -SL; held = k; break
                    if tp < 9 and k >= 2 and np.isfinite(favour) and favour >= tp:
                        ex = tp; held = k; hits[tp] += 1; break
            if ex is None:
                end = px[t0 + 7, c]
                if not np.isfinite(end):
                    col = px[t0:t0 + 8, c]; col = col[np.isfinite(col)]; end = col[-1] if len(col) else np.nan
                r = end / e[j] - 1 if np.isfinite(e[j]) and np.isfinite(end) else 0.0
                pnl += ww * r
            else:
                pnl += abs(ww) * ex - abs(ww) * 0.003
            pnl -= ww * np.nansum(fu[t0:t0 + held, c])
        res[tp].append(pnl)
df = pd.DataFrame(res, index=dates)
out = []
for tp in tps:
    x = df[tp]; eq = (1 + x).cumprod(); y = x[x.index >= pd.Timestamp("2022-01-01", tz="UTC")]
    out.append({"take_profit": "none" if tp > 9 else tp, "SR": round(x.mean() / x.std() * np.sqrt(52), 2),
                "ann": round(x.mean() * 52, 3), "maxDD": round((eq / eq.cummax() - 1).min(), 3),
                "tp_hits": hits[tp], "SR_2022_24": round(y.mean() / y.std() * np.sqrt(52), 2)})
r = pd.DataFrame(out); print(r.to_string(index=False))
r.to_csv("../../docs/v2/reports/E5_tp_check_dev_skipday1.csv", index=False)
