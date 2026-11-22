"""R22 (operator idea): cross-sectional extreme movers with participation + pullback setup.

DEVELOPMENT PERIOD ONLY (2020-01-01 .. 2024-12-31). Daily point-in-time panel (row D = bars in
[D-1d, D), known at D; entry at exec(D) = 01:00 UTC close).

LONG  setup at D: 7d return in top `frac` of eligible names, participation (3d avg quote volume /
      prior 30d median >= vr), close pulled back pb_min..pb_max below the 7d high, and close > prior
      close (first up day = resumption).
SHORT mirror: bottom `frac`, participation, bounce pb_min..pb_max above 7d low, close < prior close.
Exit: initial stop k_sl*ATR14, trailing stop k_tr*ATR from best close, time exit after H days.
Stops use daily high/low (stop priority); costs 30 bp round trip; funding paid/received while held.
Portfolio: each trade gets `size` of equity notional, PnL booked daily; Sharpe on daily series.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import panel as pn, stats as st  # noqa: E402

DEV_START, DEV_END = "2020-01-01", "2024-12-31"
COST_RT = 0.003
SIZE = 0.05

p = pn.load_daily(1, "2019-09-01", DEV_END)
m = pn.universe_mask(p)
close, high, low, px, qv, fu = (p[k] for k in ("close", "high", "low", "exec_px", "quote_volume", "funding_fwd"))
r7 = close / close.shift(7) - 1
rk = r7.where(m).rank(axis=1, pct=True)
vr = qv.rolling(3).mean() / qv.rolling(30).median().shift(3)
hi7 = high.rolling(7).max(); lo7 = low.rolling(7).min()
tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()]).groupby(level=0).max()
tr = np.maximum(np.maximum((high - low).values, (high - close.shift()).abs().values), (low - close.shift()).abs().values)
atr = pd.DataFrame(tr, index=close.index, columns=close.columns).rolling(14).mean()
up_day = close > close.shift()
ew = (px.shift(-1) / px - 1).where(m).mean(axis=1)            # equal-weight universe, exec-to-exec

idx = close.index; cols = close.columns
dev = (idx >= pd.Timestamp(DEV_START, tz="UTC")) & (idx <= pd.Timestamp(DEV_END, tz="UTC"))
A = {k: v.values for k, v in dict(px=px, hi=high, lo=low, cl=close, fu=fu, atr=atr).items()}


def simulate(frac, vrmin, pb, k_sl, k_tr, H, sides=("L", "S")):
    pb_min, pb_max = pb
    sig = {}
    if "L" in sides:
        dd = close / hi7 - 1
        sig["L"] = (rk >= 1 - frac) & (vr >= vrmin) & (dd <= -pb_min) & (dd >= -pb_max) & up_day & m
    if "S" in sides:
        bu = close / lo7 - 1
        sig["S"] = (rk <= frac) & (vr >= vrmin) & (bu >= pb_min) & (bu <= pb_max) & ~up_day & m
    daily = np.zeros(len(idx)); trades = []
    busy_until = np.full(len(cols), -1)
    for side, S in sig.items():
        sg = 1.0 if side == "L" else -1.0
        rows, cs = np.nonzero(S.values & dev[:, None])
        for t0, c in sorted(zip(rows, cs)):
            if t0 <= busy_until[c] or not np.isfinite(A["px"][t0, c]) or not np.isfinite(A["atr"][t0, c]):
                continue
            e = A["px"][t0, c]; a = A["atr"][t0, c]
            stop = e - sg * k_sl * a; best = e; exit_px = None; t = t0
            prev = e
            for t in range(t0 + 1, min(t0 + H, len(idx) - 1) + 1):
                lo_, hi_, cl_ = A["lo"][t, c], A["hi"][t, c], A["px"][t, c]
                if not np.isfinite(cl_):                       # delisted: exit at last close
                    exit_px = prev; break
                if (sg > 0 and lo_ <= stop) or (sg < 0 and hi_ >= stop):
                    exit_px = stop; break
                best = max(best, cl_) if sg > 0 else min(best, cl_)
                stop = max(stop, best - k_tr * a) if sg > 0 else min(stop, best + k_tr * a)
                daily[t] += SIZE * sg * (cl_ / prev - 1) - SIZE * sg * np.nan_to_num(A["fu"][t - 1, c])
                prev = cl_
            if exit_px is None:
                exit_px = prev
            else:
                daily[t] += SIZE * sg * (exit_px / prev - 1) - SIZE * sg * np.nan_to_num(A["fu"][t - 1, c])
            daily[t] -= SIZE * COST_RT
            busy_until[c] = t
            gross = sg * (exit_px / e - 1)
            trades.append({"date": idx[t0], "sym": cols[c], "side": side, "days": t - t0,
                           "ret": gross - COST_RT})
    s = pd.Series(daily, index=idx)[dev]
    return s, pd.DataFrame(trades)


def pf(x):
    g = x[x > 0].sum(); l = -x[x < 0].sum()
    return round(g / l, 2) if l > 0 else np.nan


grid = list(itertools.product([0.1], [1.5], [(0.03, 0.15)], [1.5, 2.5], [3.0], [10, 20]))
rows = []
ewd = ew[dev].fillna(0)
for frac, vrmin, pb, k_sl, k_tr, H in grid:
    for sides in (("L", "S"), ("L",), ("S",)):
        s, T = simulate(frac, vrmin, pb, k_sl, k_tr, H, sides)
        if T.empty:
            continue
        beta = np.cov(s, ewd)[0, 1] / ewd.var()
        alpha = (s - beta * ewd)
        summ = st.summary(s) if hasattr(st, "summary") else {}
        name = f"r22_{''.join(sides)}_sl{k_sl}_H{H}"
        st.log_trial("R22", name, {"frac": frac, "vr": vrmin, "pb": pb, "k_sl": k_sl, "k_tr": k_tr, "H": H,
                                   "sides": sides}, {"sharpe": float(s.mean() / s.std() * np.sqrt(365))}, s)
        yrs = {str(y): round(g.mean() / g.std() * np.sqrt(365), 2) for y, g in s.groupby(s.index.year)}
        rows.append({"name": name, "trades": len(T), "win%": round((T.ret > 0).mean() * 100, 1),
                     "avg_ret%": round(T.ret.mean() * 100, 2), "PF": pf(T.ret),
                     "SR": round(s.mean() / s.std() * np.sqrt(365), 2), "ann%": round(s.mean() * 365 * 100, 1),
                     "beta": round(beta, 2), "alpha_SR": round(alpha.mean() / alpha.std() * np.sqrt(365), 2),
                     "maxDD%": round(((1 + s).cumprod() / (1 + s).cumprod().cummax() - 1).min() * 100, 1),
                     "SR_by_year": json.dumps(yrs)})
r = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120)
print(r.to_string(index=False))
out = Path(__file__).resolve().parents[3] / "docs" / "v2" / "reports" / "R22_extreme_movers_dev.csv"
r.to_csv(out, index=False)
