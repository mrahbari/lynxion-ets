"""Are wave-1 survivors just hidden market beta? Regress net returns on EW-universe and BTC returns;
also build beta-neutral versions (legs scaled so ex-ante 60d beta to EW market = 0)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn, stats as st
from experiments.e2_factor_wave1 import signals, DEV_START, DEV_END
CANDS = ["premium_7d|1", "carry_funding_7d|1", "carry_funding_21d|7", "taker_imb_1d|7", "taker_imb_7d|1", "amihud_illiq_30d|7"]
p = pn.load_daily(start=DEV_START, end=DEV_END); mask = pn.universe_mask(p)
fr = pn.forward_returns(p); fr.iloc[-1] = np.nan
mkt = fr.where(mask).mean(axis=1)               # EW eligible universe, same exec timing
btc = fr["BTCUSDT"]
lr = np.log(p["close"]).diff()
mret = lr.where(mask).mean(axis=1)
beta = lr.rolling(60, min_periods=40).cov(mret).div(mret.rolling(60, min_periods=40).var(), axis=0)  # known at D
S = signals(p)

def hac(y, X):
    m = sm.OLS(y, sm.add_constant(X), missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    return m

def beta_neutral(w):
    b = beta.reindex_like(w).fillna(1.0).clip(0.2, 3.0)
    wl, ws = w.clip(lower=0), w.clip(upper=0)
    bl = (wl * b).sum(1); bs = (-ws * b).sum(1)
    # scale short leg so beta_long == beta_short, keep gross = 1
    k = (bl / bs.replace(0, np.nan)).fillna(1.0)
    ws2 = ws.mul(k, axis=0)
    g = wl.sum(1) + (-ws2).sum(1)
    return (wl + ws2).div(g.replace(0, np.nan), axis=0).fillna(0.0)

for c in CANDS:
    name, reb = c.split("|"); reb = int(reb)
    w = bt.rank_long_short(S[name], mask, frac=0.2, min_names=30)
    for tag, ww in (("raw", w), ("betaN", beta_neutral(w))):
        r = bt.run(ww, fr, p, rebalance_every=reb)
        live = r.gross_exposure > 0
        y = r.net[live]
        m = hac(y, pd.DataFrame({"mkt": mkt[live], "btc": btc[live]}))
        a_ann = m.params["const"] * 365
        late = y[y.index >= "2022-01-01"]
        ml = hac(late, pd.DataFrame({"mkt": mkt.reindex(late.index), "btc": btc.reindex(late.index)}))
        print(f"{c:22s} {tag:5s} SR={st.sharpe(y):+.2f} beta_mkt={m.params['mkt']:+.2f} beta_btc={m.params['btc']:+.2f} "
              f"alpha={a_ann:+.1%} t={m.tvalues['const']:+.2f} | 2022-24: SR={st.sharpe(late):+.2f} alpha={ml.params['const']*365:+.1%} t={ml.tvalues['const']:+.2f}  2x-cost SR={st.sharpe(bt.run(ww, fr, p, bt.CostModel(cost_mult=2), rebalance_every=reb).net[live]):+.2f}",
              flush=True)
print("EW market ann ret (dev, live days):", f"{mkt.mean()*365:.1%}", "SR", f"{st.sharpe(mkt):.2f}")
