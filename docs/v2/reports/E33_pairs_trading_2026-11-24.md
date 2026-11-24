# E33 — daily pairs trading on liquid perps (2026-11-24)

Source: operator link github.com/orangepineapple/mean_reversion_strategies (after E. P. Chan, "Algorithmic
Trading", 2013). Pre-registered and committed before the run (research/v2/experiments/e33_pairs_trading.py):
45 pairs of 10 liquid perps, rolling 60-day OLS hedge ratio, 20-day spread z-score, entry |z| >= 2, exit
|z| <= 0.5, stop |z| >= 4, max 20 days, 10 bp per leg turnover, real funding.

| window | net Sharpe | gross Sharpe (diagnostic) | net / yr | max DD | trades |
|---|---|---|---|---|---|
| DEV 2020-24 | -1.62 | -1.37 | -50.9 % | -94.1 % | 2,749 |
| HOLDOUT 2025-26 | -0.18 | +0.41 | -2.7 % | -22.9 % | 1,382 |

**FAIL**, and not because of costs: the signal is negative before costs on DEV. Spreads between crypto perps
trend after a 2-sigma divergence (regime and narrative shifts) instead of reverting; the divergence stop is hit
too often. Not built.

Other operator link reviewed: github.com/moss-site/moss-trade-bot-skills — LLM-assembled composite of five
indicator families on 15m Hyperliquid perps with parameters evolved in-sample; no published results, no
out-of-sample test, no stated costs. Same family as our failed intraday setups (E9-E28) and indicator combination
(E14); its "ambush" OI-surge trigger is close to Codex C-16 (rejected). Not tested.
