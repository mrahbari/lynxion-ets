"""Diagnostics for wave-1 survivors: PnL decomposition, legs, concentration, correlation, null DSR."""
import sys, math
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn, stats as st
from experiments.e2_factor_wave1 import signals, DEV_START, DEV_END

CANDS = ["premium_7d|1", "premium_3d|1", "carry_funding_7d|1", "carry_funding_3d|7", "carry_funding_21d|7",
         "taker_imb_1d|7", "taker_imb_7d|1", "amihud_illiq_30d|7"]
p = pn.load_daily(start=DEV_START, end=DEV_END); mask = pn.universe_mask(p)
fr = pn.forward_returns(p); fr.iloc[-1] = np.nan
S = signals(p)
nets = {}
for c in CANDS:
    name, reb = c.split("|"); reb = int(reb)
    w = bt.rank_long_short(S[name], mask, frac=0.2, min_names=30)
    r = bt.run(w, fr, p, rebalance_every=reb)
    wl, ws = w.clip(lower=0), w.clip(upper=0)
    rl = bt.run(wl, fr, p, rebalance_every=reb); rs = bt.run(ws, fr, p, rebalance_every=reb)
    sp = r.sym_pnl.sort_values()
    live = r.net[r.gross_exposure > 0]
    nets[c] = live
    print(f"\n== {c}  days={len(live)}  netSR={st.sharpe(live):.2f}  annRet={live.mean()*365:.1%}  maxDD={st.max_dd(live):.1%}")
    print(f"   ann: price={r.gross[r.gross_exposure>0].mean()*365:.1%} funding={r.funding[r.gross_exposure>0].mean()*365:.1%} cost={-r.cost[r.gross_exposure>0].mean()*365:.1%}")
    print(f"   long leg netSR={st.sharpe(rl.net[r.gross_exposure>0]):.2f} ann={rl.net[r.gross_exposure>0].mean()*365:.1%} | short leg netSR={st.sharpe(rs.net[r.gross_exposure>0]):.2f} ann={rs.net[r.gross_exposure>0].mean()*365:.1%}")
    print(f"   by year: {st.summary(live)['sharpe_by_year']}")
    tot = r.sym_pnl.sum()
    print(f"   total sym pnl={tot:.2f}; best5 {dict(sp.tail(5).round(3))}; worst5 {dict(sp.head(5).round(3))}")
    print(f"   PnL ex-top5 symbols = {(tot - sp.tail(5).sum()):.2f}")
df = pd.DataFrame(nets).dropna()
print("\ncorrelation of daily net returns:\n", df.corr().round(2).to_string())
T = len(df); null_var_ann = 365.0 / T
for n_eff in (10, 20, 60, 120):
    thr = st.expected_max_sr(n_eff, null_var_ann)
    print(f"null DSR threshold (n_eff={n_eff}, T={T}): SR*={thr:.2f}  ->  " +
          ", ".join(f"{c}:{st.dsr(df[c], n_eff, null_var_ann):.3f}" for c in CANDS))
