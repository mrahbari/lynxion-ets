"""Cost-aware cross-sectional portfolio backtester (daily).

Contract
--------
weights.loc[D] = target portfolio weights (fraction of equity, signed) decided with info <= D and
traded at exec(D). The position earns fwd_ret.loc[D] (exec(D) -> exec(D+1)) and pays/receives
funding_fwd.loc[D]. Costs are charged on traded notional at exec(D):

  cost_i = |Δw_i| * (fee + half_spread(ADV_i) + impact_i)
  impact_i = Y * σ_i * sqrt(|Δw_i| * capital / ADV_i)          (square-root law)

Between rebalances weights drift with returns (no free rebalancing).
All inputs on row D must be known at D (ADV / vol use trailing windows ending at D).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class CostModel:
    fee: float = 0.0005            # 5 bp per side (BingX/Binance taker)
    impact_y: float = 0.7
    capital: float = 100_000.0     # USD notional base for impact
    cost_mult: float = 1.0         # 2.0 for stress
    # half-spread by ADV (USD/day) bucket
    spread_buckets: tuple = ((1e9, 0.00005), (2e8, 0.0001), (5e7, 0.0002), (1e7, 0.0004), (0, 0.0008))

    def half_spread(self, adv: np.ndarray) -> np.ndarray:
        out = np.full(adv.shape, self.spread_buckets[-1][1])
        for thr, hs in reversed(self.spread_buckets):
            out = np.where(adv >= thr, hs, out)
        return out


@dataclass
class Result:
    net: pd.Series
    gross: pd.Series
    cost: pd.Series
    funding: pd.Series
    turnover: pd.Series
    gross_exposure: pd.Series
    sym_pnl: pd.Series = field(default=None)


def run(weights: pd.DataFrame, fwd_ret: pd.DataFrame, p: dict[str, pd.DataFrame],
        cost: CostModel | None = None, rebalance_every: int = 1) -> Result:
    cost = cost or CostModel()
    cols = weights.columns
    idx = weights.index
    W = weights.reindex(index=idx, columns=cols).fillna(0.0).values
    R = fwd_ret.reindex(index=idx, columns=cols).values
    F = p["funding_fwd"].reindex(index=idx, columns=cols).fillna(0.0).values
    adv = p["quote_volume"].rolling(30, min_periods=10).median().reindex(index=idx, columns=cols).values
    lr = np.log(p["close"]).diff()
    vol = lr.rolling(30, min_periods=10).std().reindex(index=idx, columns=cols).values

    n, m = W.shape
    net = np.zeros(n); gross = np.zeros(n); cst = np.zeros(n); fnd = np.zeros(n)
    turn = np.zeros(n); gexp = np.zeros(n); sym = np.zeros(m)
    held = np.zeros(m)
    for t in range(n):
        target = W[t] if (t % rebalance_every == 0) else held
        # positions in symbols without a forward return (no price) must be closed
        r = R[t]
        bad = ~np.isfinite(r)
        target = np.where(bad, 0.0, target)
        dw = np.abs(target - held)
        a = np.where(np.isfinite(adv[t]) & (adv[t] > 0), adv[t], 1e6)
        s = np.where(np.isfinite(vol[t]), vol[t], 0.05)
        unit = cost.fee + cost.half_spread(a) + cost.impact_y * s * np.sqrt(dw * cost.capital / a)
        c = float(np.sum(dw * unit)) * cost.cost_mult
        r0 = np.where(bad, 0.0, r)
        g = float(np.sum(target * r0))
        f = -float(np.sum(target * F[t]))
        pnl_i = target * r0 - target * F[t] - dw * unit * cost.cost_mult
        sym += pnl_i
        net[t] = g + f - c; gross[t] = g; cst[t] = c; fnd[t] = f
        turn[t] = float(dw.sum()); gexp[t] = float(np.abs(target).sum())
        # drift
        denom = 1.0 + g + f - c
        held = target * (1.0 + r0) / denom if denom > 0 else np.zeros(m)
    S = lambda a_: pd.Series(a_, index=idx)  # noqa: E731
    return Result(S(net), S(gross), S(cst), S(fnd), S(turn), S(gexp), pd.Series(sym, index=cols))


# ---------- signal -> weights helpers ----------

def rank_long_short(signal: pd.DataFrame, mask: pd.DataFrame, frac: float = 0.2,
                    gross: float = 1.0, min_names: int = 10) -> pd.DataFrame:
    """Dollar-neutral: long top `frac`, short bottom `frac` of eligible names, equal weight."""
    s = signal.where(mask)
    rk = s.rank(axis=1, pct=True)
    n = s.notna().sum(axis=1)
    long = (rk > 1 - frac).astype(float)
    short = (rk <= frac).astype(float)
    nl = long.sum(axis=1).replace(0, np.nan)
    ns = short.sum(axis=1).replace(0, np.nan)
    w = long.div(nl, axis=0) * (gross / 2) - short.div(ns, axis=0) * (gross / 2)
    w[n < min_names] = 0.0
    return w.fillna(0.0)


def zscore_weights(signal: pd.DataFrame, mask: pd.DataFrame, gross: float = 1.0,
                   clip: float = 3.0, min_names: int = 10) -> pd.DataFrame:
    """Dollar-neutral weights proportional to cross-sectional z-score."""
    s = signal.where(mask)
    z = s.sub(s.mean(axis=1), axis=0).div(s.std(axis=1), axis=0).clip(-clip, clip)
    w = z.div(z.abs().sum(axis=1), axis=0) * gross
    w[s.notna().sum(axis=1) < min_names] = 0.0
    return w.fillna(0.0)
