"""E4-2: single holdout evaluation of frozen XS-COMBO-V1 (2025-01-01..2026-10-31)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import backtest as bt, panel as pn, stats as st
from strategies import xs_combo_v1 as S

H0, H1 = "2025-01-01", "2026-10-31"
P = S.PARAMS
p = pn.load_daily(start="2024-08-01", end=H1)            # warm-up only for signal history
mask = pn.universe_mask(p, min_adv_usd=P["min_adv_usd"], min_age_days=P["min_age_days"])
fr = pn.forward_returns(p)
sig = S.signal(p, mask)
w = bt.rank_long_short(sig, mask, frac=P["frac"], gross=P["gross"], min_names=P["min_names"])
w = w[w.index >= H0]                                     # no positions before holdout start
res = {}
for mult in (1.0, 2.0):
    r = bt.run(w, fr.reindex(w.index), p, bt.CostModel(cost_mult=mult), rebalance_every=P["rebalance_every"])
    res[mult] = r
r = res[1.0]
y = r.net.dropna(); y = y.iloc[:-1]  # last day has no next exec price
s = st.summary(y, r.gross.loc[y.index], r.turnover.loc[y.index])
mkt = fr.where(mask).mean(1).reindex(y.index); btc = fr["BTCUSDT"].reindex(y.index)
m = sm.OLS(y, sm.add_constant(pd.DataFrame({"mkt": mkt, "btc": btc})), missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": 7})
seg = {str(k): {"sharpe": st.sharpe(g), "ret": float(g.sum())} for k, g in y.groupby(y.index.year)}
sp = r.sym_pnl; share = float(sp.abs().max() / sp.abs().sum())
y2 = res[2.0].net.loc[y.index]
out = {**s, "sharpe_2x": st.sharpe(y2), "segments": seg, "alpha_ann": float(m.params["const"] * 365),
       "alpha_t": float(m.tvalues["const"]), "beta_mkt": float(m.params["mkt"]), "beta_btc": float(m.params["btc"]),
       "top_symbol": sp.abs().idxmax(), "top_symbol_share": share,
       "ann_price": float(r.gross.loc[y.index].mean() * 365), "ann_funding": float(r.funding.loc[y.index].mean() * 365),
       "ann_cost": float(-r.cost.loc[y.index].mean() * 365), "median_universe": int(mask.loc[y.index].sum(1).median()),
       "best5": sp.sort_values().tail(5).round(4).to_dict(), "worst5": sp.sort_values().head(5).round(4).to_dict(),
       "monthly": {str(k.date()): round(float(v), 4) for k, v in y.resample("M").sum().items()}}
PASS = (out["sharpe"] >= 0.75 and out["sharpe_2x"] > 0 and all(v["ret"] > 0 for v in seg.values()) and share <= 0.15)
out["verdict"] = ("STRONG PASS" if PASS and out["sharpe"] >= 1.5 else "PASS") if PASS else "FAIL"
st.log_trial("E4_holdout", "xs_combo_v1", P, {k: v for k, v in out.items() if k not in ("monthly",)}, y)
Path(__file__).resolve().parents[3].joinpath("docs/v2/reports/E4_holdout_xs_combo_v1.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps(out, indent=2, default=str))
