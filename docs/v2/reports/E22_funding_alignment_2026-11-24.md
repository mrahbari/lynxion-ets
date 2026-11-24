# E22 — funding-carry alignment as a filter for the platform setups (2026-11-24)

Rule pre-registered and committed before the run (research/v2/experiments/e22_funding_alignment.py).
E9 trades (8 setups, live-equivalent execution, costs) split by the side of the last settled Binance funding
rate at entry: aligned = the side that receives funding.

| pooled | n aligned / against | net R aligned | net R against | diff |
|---|---|---|---|---|
| DEV | 13,775 / 13,683 | -0.054 | -0.149 | +0.095 |
| HOLDOUT | 6,052 / 6,298 | -0.140 | -0.058 | **-0.082** |

**FAIL.** The DEV separation reverses on HOLDOUT (as XS-rank in E15): no stable information for these
setups. Even the DEV "good" side is net negative. Per strategy: only oi_footprint keeps the sign on HOLDOUT
(+0.085) and stays net negative.

**Strategy-layer conclusion.** Single-asset intraday technical setups have no net edge and no tested filter
(meta-label E14, XS-rank E15, CVD E17, MTF E19, OI E20, canonical rebuild E21, funding E22) rescues them.
The only validated edge in the project is the funding-carry XS-COMBO sleeve (holdout SR 1.39, return ~all
funding). Platform setups stay live on VST as the execution/behaviour testbed (operator decision 11-24).
