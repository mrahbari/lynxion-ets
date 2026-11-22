"""E5 stop-loss distance check on the DEVELOPMENT period only (2020-2024).

Weekly XS-COMBO-V1 books; per-name price stop at distance s from entry, using daily high/low
(row D covers [D-1d, D); entry is exec(D)=01:00 so the first day includes 1h before entry -> conservative).
Stopped name: return -s, funding only while held, extra 30 bp round-trip cost. Weekly PnL, SR = mean/sd*sqrt(52).
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
stops = [9.99, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50, 0.75]
res = {s: [] for s in stops}; dates = []; nstop = {s: 0 for s in stops}
for t0 in range(start, len(idx) - 7, 7):
    wt = np.nan_to_num(W[t0]); names = np.nonzero(wt)[0]
    if len(names) == 0:
        continue
    dates.append(idx[t0])
    e = px[t0, names]
    for s in stops:
        pnl = 0.0
        for j, c in enumerate(names):
            ww = wt[c]; sign = np.sign(ww); exit_ret = None; held = 7
            if s < 9 and np.isfinite(e[j]):
                for k in range(1, 8):
                    adverse = (lo[t0 + k, c] / e[j] - 1) if sign > 0 else -(hi[t0 + k, c] / e[j] - 1)
                    if np.isfinite(adverse) and adverse <= -s:
                        exit_ret = -s * sign; held = k; nstop[s] += 1; break
            if exit_ret is None:
                end = px[t0 + 7, c]
                if not np.isfinite(end):  # delisted: last available close
                    col = px[t0:t0 + 8, c]; col = col[np.isfinite(col)]; end = col[-1] if len(col) else np.nan
                r = end / e[j] - 1 if np.isfinite(e[j]) and np.isfinite(end) else 0.0
                pnl += ww * r
            else:
                pnl += abs(ww) * exit_ret * sign - abs(ww) * 0.003
            pnl -= ww * np.nansum(fu[t0:t0 + held, c])
        res[s].append(pnl)
df = pd.DataFrame(res, index=dates)
out = []
for s in stops:
    x = df[s]; eq = (1 + x).cumprod()
    out.append({"stop": s, "SR": round(x.mean() / x.std() * np.sqrt(52), 2), "ann": round(x.mean() * 52, 3),
                "maxDD": round((eq / eq.cummax() - 1).min(), 3), "worst_week": round(x.min(), 3),
                "stops_hit": nstop[s],
                "SR_2022_24": round(x["2022":].mean() / x["2022":].std() * np.sqrt(52), 2)})
r = pd.DataFrame(out); print(r.to_string(index=False))
Path("../../docs/v2/reports").mkdir(parents=True, exist_ok=True)
r.to_csv("../../docs/v2/reports/E5_stop_check_dev.csv", index=False)
