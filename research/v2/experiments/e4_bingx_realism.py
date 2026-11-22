"""E4-3: frozen XS-COMBO-V1 on the holdout, tradable-on-BingX only, earning BingX funding."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn, stats as st
from strategies import xs_combo_v1 as S

LAKE = pn.LAKE.parent / "bingx" / "funding"
DAY, HOUR = 86_400_000, 3_600_000
p = pn.load_daily(start="2024-08-01", end="2026-10-31")
mask = pn.universe_mask(p)
fr = pn.forward_returns(p)
idx = p["close"].index; days = (idx.view("int64") // 10**6)
bxf = pd.DataFrame(np.nan, index=idx, columns=p["close"].columns)
listed = pd.DataFrame(False, index=idx, columns=p["close"].columns)
corr = []
for f in LAKE.glob("*.parquet"):
    s = f.stem
    if s not in bxf.columns: continue
    d = pd.read_parquet(f)
    lab = ((d.calc_time.values - HOUR - 1) // DAY) * DAY           # same (exec(D), exec(D+1)] rule as panel
    ser = pd.Series(d.funding_rate.values).groupby(lab).sum()
    v = ser.reindex(days).values
    first = d.calc_time.min()
    listed[s] = days >= first
    bxf[s] = np.where(listed[s].values, np.nan_to_num(v), np.nan)
    a = p["funding_fwd"][s]; b = bxf[s]
    ok = listed[s] & a.notna() & (idx >= "2025-01-01")
    if ok.sum() > 60: corr.append((s, float(np.corrcoef(a[ok], b[ok])[0, 1]), float(a[ok].mean()*365), float(b[ok].mean()*365)))
c = pd.DataFrame(corr, columns=["sym", "corr", "binance_ann", "bingx_ann"])
print("daily funding corr Binance vs BingX: median", round(c["corr"].median(), 3), " mean ann funding Binance", round(c.binance_ann.mean(), 3), "BingX", round(c.bingx_ann.mean(), 3))

m2 = mask & listed
w = bt.rank_long_short(S.signal(p, mask), m2, frac=0.2, min_names=30)   # signal from Binance data, trade only BingX names
w = w[w.index >= "2025-01-01"]
out = {}
for tag, fund in (("binance_funding", p["funding_fwd"]), ("bingx_funding", bxf.fillna(0.0))):
    q = dict(p); q["funding_fwd"] = fund
    for mult in (1.0, 2.0):
        r = bt.run(w, fr.reindex(w.index), q, bt.CostModel(cost_mult=mult), rebalance_every=7)
        y = r.net.iloc[:-1]
        out[f"{tag}|{mult}x"] = {"sharpe": round(st.sharpe(y), 2), "ann": round(float(y.mean()*365), 3),
                                 "price": round(float(r.gross.iloc[:-1].mean()*365), 3), "funding": round(float(r.funding.iloc[:-1].mean()*365), 3),
                                 "cost": round(float(-r.cost.iloc[:-1].mean()*365), 3), "mdd": round(st.max_dd(y), 3),
                                 "by_year": st.summary(y)["sharpe_by_year"]}
print(json.dumps(out, indent=1))
Path(__file__).resolve().parents[3].joinpath("docs/v2/reports/E4_bingx_realism.json").write_text(json.dumps({"funding_corr": c.describe().to_dict(), "results": out}, indent=1, default=str))
