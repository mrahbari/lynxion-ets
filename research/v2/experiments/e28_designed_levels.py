"""E28 — the same setups with their DESIGNED stop/target instead of the global clamp (2026-11-24).

Finding (E27 review): every platform order passes `shared.utils.sanitize_sltp_levels`, which forces the stop into
1.2 %..3.0 % of entry, caps the target at 5.5 % and pushes it to >= 1.5 x the stop distance. So every test
(E9, E21, E25, E26, E27) and live trading measured the setups with distorted levels: E27 stops median exactly
1.2 % (design: just beyond the retest), VWAP 75 % of stops at 1.2 %, 4h trend stops almost all at 3 %, and
mean-reversion targets (VWAP, SMA5) pushed beyond their level by the 1.5 x rule.

Pre-registered (2026-11-24, committed before any run). Designs and code unchanged from E21 / E25 / E27:
  TF1 (live TrendFollow), VR1 (live VWAPReversal), MR1, BO1, LQ1, BRK_RETEST.
  Only change: the level sanitiser keeps safety only — stop and target on the correct side of entry, stop
  distance <= 15 %, target distance <= 30 %; otherwise the trade is skipped (no default levels, no 1.5 x rule).
  Same E9 engine, universe, windows, costs, break-even / trail.
  Reference = each design's published clamped result (E21, E25, E27).
  Per design: ADOPT_LEVELS if mean net R better than its clamped result on DEV AND on HOLDOUT.
              EDGE if mean net R >= +0.05 with n >= 100 on DEV and > 0 on HOLDOUT.
  R is in units of the designed stop (risk per trade in USDT varies with the stop distance at a fixed notional;
  live adoption therefore needs risk-based sizing — decided separately).
Usage: python research/v2/experiments/e28_designed_levels.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e9_strategy_backtest as e9  # noqa: E402
import shared.utils as su  # noqa: E402

CLAMPED = {"TF1_trend_canonical": (-0.027, -0.010), "VR1_vwap_canonical": (-0.017, -0.062),
           "MR1": (-0.034, -0.146), "BO1": (-0.137, -0.174), "LQ1": (-0.138, -0.090),
           "BRK_RETEST": (-0.147, 0.026)}
DESIGNS = {"TF1_trend_canonical": ("e21_canonical_setups", "TrendCanonical", "1h"),
           "VR1_vwap_canonical": ("e21_canonical_setups", "VWAPCanonical", "15m"),
           "MR1": ("e25_canonical_rest", "MR1", "1h"), "BO1": ("e25_canonical_rest", "BO1", "15m"),
           "LQ1": ("e25_canonical_rest", "LQ1", "15m"),
           "BRK_RETEST": ("e27_breakout_retest", "BreakoutRetest", "1h")}


def safety_only(entry_price, side, stop_loss=None, take_profit=None, **_):
    e = float(entry_price or 0)
    sl, tp = float(stop_loss or 0), float(take_profit or 0)
    s = str(getattr(side, "name", side)).upper()
    sgn = 1 if s in ("BUY", "LONG") else -1
    if not (math.isfinite(e) and math.isfinite(sl) and math.isfinite(tp)) or e <= 0 or sl <= 0 or tp <= 0:
        return 0.0, 0.0
    if sgn * (e - sl) <= 0 or sgn * (tp - e) <= 0:
        return 0.0, 0.0
    if abs(e - sl) / e > 0.15 or abs(tp - e) / e > 0.30:
        return 0.0, 0.0
    return sl, tp


def main():
    su.sanitize_sltp_levels = safety_only          # e9.run imports it from shared.utils at call time
    for name, spec in DESIGNS.items():
        e9.STRATEGIES[name] = spec
    tr = pd.DataFrame([t for name in DESIGNS for s in e9.SYMBOLS for t in e9.run((name, s))])
    tr.to_csv(e9.OUT / "E28_designed_levels_trades.csv", index=False)
    s = e9.summarize(tr)
    s.to_csv(e9.OUT / "E28_designed_levels_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(s[["strategy", "window", "trades", "win_rate", "PF", "mean_R", "mean_ret_bps", "first_half_R",
             "second_half_R", "symbols_positive", "median_sl_pct"]].to_string(index=False))
    for name in DESIGNS:
        d = s[(s.strategy == name) & (s.window == "dev")].iloc[0]
        h = s[(s.strategy == name) & (s.window == "holdout")].iloc[0]
        edge = d.trades >= 100 and d.mean_R >= 0.05 and h.mean_R > 0
        adopt = d.mean_R > CLAMPED[name][0] and h.mean_R > CLAMPED[name][1]
        print(f"{name}: clamped {CLAMPED[name]} -> designed ({d.mean_R:+.3f}, {h.mean_R:+.3f}) |",
              "EDGE" if edge else "NO EDGE", "|", "ADOPT_LEVELS" if adopt else "KEEP CLAMP")


if __name__ == "__main__":
    main()
