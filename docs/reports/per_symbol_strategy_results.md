# Per-Symbol Strategy Results (Phase C)

**Date:** 2026-06-13. BTC / ETH / SOL evaluated **independently** (never pooled). SOL does **not**
invalidate BTC/ETH findings — each symbol stands alone. Values = net forward-return expectancy per
actionable signal (% , round-trip cost 0.30% applied), at each strategy's design TF; **all-signal**
and **in-regime**; "stable" = sign agreement across the two halves; n = in-regime sample.

## BTC

| Strategy | TF | all % | in-reg % | n | stable | READY? |
|---|---|---|---|---|---|---|
| trend_following | 1h | −0.28 | −0.21 | 582 | yes(neg) | no |
| momentum | 1h | −0.28 | −0.29 | 702 | yes(neg) | no |
| mtf_trend | 15m | −0.30 | −0.31 | 9945 | yes(neg) | no |
| sweep_scalper | 1m | −0.34 | −0.33 | 128 | yes(neg) | no |
| breakout | 15m | −0.30 | −0.45 | 80 | yes(neg) | no |
| liquidity | 5m | −0.25 | −0.28 | 34 | yes(neg) | no |
| volatility_breakout | 15m | −0.22 | −0.22 | 74 | yes(neg) | no |
| oi_footprint | 1h | −0.34 | n/a | 0 | — | no |
| vwap_reversal | 5m | −0.34 | −0.34 | 5 | unjudgeable | no |
| mean_reversion | 1h | −0.18 (1 sig) | n/a | 0 | unjudgeable | no |

## ETH

| Strategy | TF | all % | in-reg % | n | stable | READY? |
|---|---|---|---|---|---|---|
| trend_following | 1h | −0.27 | −0.29 | 635 | yes(neg) | no |
| momentum | 1h | −0.30 | −0.26 | 1157 | yes(neg) | no |
| mtf_trend | 15m | −0.28 | −0.28 | 10112 | yes(neg) | no |
| sweep_scalper | 1m | −0.28 | −0.27 | 1213 | yes(neg) | no |
| breakout | 15m | −0.24 | −0.16 | 105 | **flip** | no |
| liquidity | 5m | −0.34 | −0.30 | 42 | **flip** | no |
| volatility_breakout | 15m | −0.26 | **+0.13** | 64 | **FLIP** (+0.64/−0.32) | no |
| oi_footprint | 1h | −0.21 | n/a | 0 | — | no |
| vwap_reversal | 5m | −0.40 | −0.07 | 4 | unjudgeable | no |
| mean_reversion | 1h | +0.79 (4 sig) | n/a | 0 | unjudgeable (n=4) | no |

## SOL (reported independently; does not veto BTC/ETH)

| Strategy | TF | all % | in-reg % | n | stable | READY? |
|---|---|---|---|---|---|---|
| trend_following | 1h | −0.19 | −0.16 | 714 | **flip** | no |
| momentum | 1h | −0.30 | −0.35 | 1331 | yes(neg) | no |
| mtf_trend | 15m | −0.30 | −0.31 | 11037 | yes(neg) | no |
| sweep_scalper | 1m | −0.07 | −0.21 | 40 | — | no |
| breakout | 15m | −0.28 | −0.37 | 91 | **flip** | no |
| liquidity | 5m | −0.38 | −0.36 | 51 | yes(neg) | no |
| volatility_breakout | 15m | −0.12 | **+0.34** | 38 | **FLIP** (+1.35/−0.66) | no |
| oi_footprint | 1h | −0.35 | n/a | 0 | — | no |
| vwap_reversal | 5m | −0.16 | +0.13 | 7 | unjudgeable | no |
| mean_reversion | 1h | −1.48 (9 sig) | n/a | 0 | unjudgeable | no |

## Per-symbol findings

- **No symbol rescues any strategy.** Unlike the prior pooled roll-up (where SOL's catastrophe was
  blamed for dragging down BTC/ETH), evaluating each symbol **independently** shows BTC and ETH are
  **also negative or unstable** in the intended regime for every strategy. The earlier "BTC-favourable"
  / "ETH-favourable" annotations were artifacts of *un-conditioned, wrong-TF* P&L, not a real
  per-symbol edge.
- **SOL is no longer the scapegoat.** Separating SOL confirms it is weak, but it does **not** change
  the conclusion: BTC and ETH independently fail the READY bar too. Excluding SOL would **not** produce
  any READY strategy.
- **The only positives (volatility_breakout ETH/SOL) are single-period.** They are positive in the
  first half and sharply negative in the second — the textbook signature of period-specific noise, and
  exactly why cross-period stability is a READY requirement.

**Net:** Phase C confirms there is **no per-symbol edge** to recover. Independent BTC/ETH/SOL
evaluation removes the pooling confound and still yields READY = 0 on every symbol.
