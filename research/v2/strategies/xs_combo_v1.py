"""XS-COMBO-V1 — frozen cross-sectional strategy (frozen 2026-11-22, before any holdout data was evaluated).

Universe : Binance USDT-M perps; age >= 30d; 30d median quote volume >= $10M; stablecoins/gold excluded.
Signal   : equal-weight sum of cross-sectional (pct-rank - mean) of
             carry   = -(sum of funding rates over past 21 days)      (short crowded longs)
             illiq   = mean(|daily log return| / quote volume, 30d)    (Amihud illiquidity)
             taker   = mean(taker_buy_quote/quote_volume - 0.5, 7d)    (aggressive buying)
Portfolio: long top 20%, short bottom 20%, equal weight, gross 1.0 (0.5/0.5), dollar-neutral.
Rebalance: every 7 days; decision at 00:00 UTC on completed daily data; execution at 01:00 close.
Costs    : fee 5 bp/side + ADV-bucket half-spread + sqrt impact (Y=0.7, capital $100k); stress 2x.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PARAMS = {"funding_window": 21, "illiq_window": 30, "taker_window": 7, "frac": 0.2,
          "rebalance_every": 7, "min_adv_usd": 10e6, "min_age_days": 30, "min_names": 30, "gross": 1.0}


def _rk(x: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    r = x.where(m).rank(axis=1, pct=True)
    return r.sub(r.mean(1), axis=0)


def signal(p: dict[str, pd.DataFrame], mask: pd.DataFrame) -> pd.DataFrame:
    lr = np.log(p["close"]).diff()
    qv = p["quote_volume"]
    carry = -p["funding_past"].rolling(PARAMS["funding_window"], min_periods=1).sum()
    illiq = (lr.abs() / qv).rolling(PARAMS["illiq_window"], min_periods=20).mean()
    taker = (p["taker_buy_quote"] / qv - 0.5).rolling(PARAMS["taker_window"], min_periods=4).mean()
    return _rk(carry, mask) + _rk(illiq, mask) + _rk(taker, mask)
