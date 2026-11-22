"""E3-1: robustness plateau of wave-1 survivors + equal-weight (unfitted) combination. Dev period only."""
import sys, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn, stats as st
from experiments.e2_factor_wave1 import signals, DEV_START, DEV_END

p = pn.load_daily(start=DEV_START, end=DEV_END)
fr = pn.forward_returns(p); fr.iloc[-1] = np.nan
S = signals(p)
BASE = {"carry21": S["carry_funding_21d"], "illiq": S["amihud_illiq_30d"], "taker7": S["taker_imb_7d"]}

def zs(x, m):
    x = x.where(m)
    r = x.rank(axis=1, pct=True)          # rank-normalise -> robust to outliers
    return r.sub(r.mean(1), axis=0)

def evaluate(tag, sig, mask, frac, reb, cap):
    w = bt.rank_long_short(sig, mask, frac=frac, min_names=30)
    r = bt.run(w, fr, p, bt.CostModel(capital=cap), rebalance_every=reb)
    r2 = bt.run(w, fr, p, bt.CostModel(capital=cap, cost_mult=2), rebalance_every=reb)
    live = r.gross_exposure > 0
    y = r.net[live]; late = y[y.index >= "2022-01-01"]
    s = st.summary(y, r.gross[live], r.turnover[live])
    out = {"tag": tag, "frac": frac, "reb": reb, "cap": cap, "SR": s["sharpe"], "SR_2x": st.sharpe(r2.net[live]),
           "SR_22_24": st.sharpe(late), "ann": s["ann_ret"], "mdd": s["max_dd"], "turn": s["avg_daily_turnover"],
           **{f"y{k}": v for k, v in s["sharpe_by_year"].items()}}
    st.log_trial("E3_robust", f"{tag}|f{frac}|r{reb}|c{cap}", {"frac": frac, "reb": reb, "cap": cap}, s, y)
    return out, y

rows = []
masks = {adv: pn.universe_mask(p, min_adv_usd=adv) for adv in (5e6, 10e6, 25e6, 50e6)}
for adv, m in masks.items():
    combo = sum(zs(v, m) for v in (BASE["carry21"], BASE["illiq"]))
    combo3 = sum(zs(v, m) for v in BASE.values())
    sigs = {**BASE, "combo_c+i": combo, "combo_c+i+t": combo3}
    for (name, sig), frac, reb in itertools.product(sigs.items(), (0.1, 0.2, 0.3), (3, 7, 14)):
        o, _ = evaluate(f"{name}|adv{int(adv/1e6)}M", sig, m, frac, reb, 1e5)
        rows.append(o)
df = pd.DataFrame(rows)
df.to_csv(Path(__file__).resolve().parents[3] / "docs/v2/reports/E3_robustness_grid.csv", index=False)
g = df.assign(sig=df.tag.str.split("|").str[0])
print(g.groupby("sig")[["SR", "SR_2x", "SR_22_24"]].agg(["median", "min", "max"]).round(2).to_string())
print()
print(g.groupby(["sig", g.tag.str.split("|").str[1]])[["SR", "SR_2x", "SR_22_24"]].median().round(2).to_string())
# capacity: combo at default settings, different capital
m = masks[10e6]
combo = sum(zs(v, m) for v in (BASE["carry21"], BASE["illiq"]))
for cap in (1e4, 1e5, 1e6, 5e6):
    o, _ = evaluate("combo_c+i|adv10M", combo, m, 0.2, 7, cap)
    print(f"capacity cap=${cap:,.0f}: SR={o['SR']:.2f} SR_2x={o['SR_2x']:.2f} ann={o['ann']:.1%} 22-24 SR={o['SR_22_24']:.2f}")
