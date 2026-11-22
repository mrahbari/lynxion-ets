import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn
from strategies import xs_combo_v1 as S
from live import binance_live_panel as lp
D = pd.Timestamp("2026-10-31", tz="UTC")
pl = pn.load_daily(start="2026-08-01", end="2026-10-31")
ml = pn.universe_mask(pl)
np_syms = set(json.load(open(pn.LAKE / 'non_perpetual_symbols.json')))
ml.loc[:, [c for c in ml.columns if c in np_syms]] = False
wl = bt.rank_long_short(S.signal(pl, ml), ml, frac=0.2, min_names=30).loc[D]
syms = lp.universe_symbols()["symbol"].tolist()
pr = lp.build(D, days=60, symbols=syms)
mr = pn.universe_mask(pr)
wr = bt.rank_long_short(S.signal(pr, mr), mr, frac=0.2, min_names=30).loc[D]
common = sorted(set(wl.index) & set(wr.index))
a, b = wl.reindex(common).fillna(0), wr.reindex(common).fillna(0)
print("lake eligible", int(ml.loc[D].sum()), "rest eligible", int(mr.loc[D].sum()))
print("weight corr", round(float(np.corrcoef(a, b)[0, 1]), 4))
print("same sign share among held:", round(float(((np.sign(a) == np.sign(b)) | ((a == 0) & (b == 0)))[(a != 0) | (b != 0)].mean()), 4))
for f in ("close", "quote_volume", "taker_buy_quote", "funding_past"):
    x = pl[f].loc[pd.Timestamp("2026-10-01", tz="UTC"):D]; y = pr[f].reindex(index=x.index, columns=x.columns)
    ok = x.notna() & y.notna()
    print(f, "max rel diff", float(((x - y).abs() / x.abs().clip(lower=1e-12))[ok].max().max()))
