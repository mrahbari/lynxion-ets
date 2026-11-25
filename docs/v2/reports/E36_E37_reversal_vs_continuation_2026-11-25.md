# E36 / E37 — Reversal vs continuation: is there a conditional edge? (2026-11-25)

Brief (operator, 2026-11-25): stop rescuing mean reversion with indicators; first find the conditions under
which reversal (or continuation) follows a price event, net of costs, out-of-sample, across symbols. Reject the
hypothesis if the evidence is not there.

Scripts (pre-registered, each committed before its run):
`research/v2/experiments/e36_reversal_conditions.py` (commit 15b7523),
`research/v2/experiments/e37_event_continuation.py`. Data: Binance USDT-M 1h klines with volume and taker-buy
volume -> 4h bars; real funding; 10 liquid perps; DEV 2020-2024, HOLDOUT 2025-01..2026-10.
Costs: 5 bp fee + 2 bp slippage per side, funding over the hold. Day-clustered t, Holm correction.
Raw tables: `E36_reversal_conditions_dev.csv`, `E37_event_continuation.csv`.

## E36 — event study, 8 event families x 6 conditions = 48 DEV tests, 24 h hold

Families: F1 band stretch (the E35 base), F2 wick rejection, F3 band re-entry, F4 liquidity sweep + reclaim,
F5 failed breakout, F6 absorption (high volume, small body, one-sided taker flow), F7 CVD divergence,
F8 capitulation (range >= 3 ATR, volume >= 3x; liquidation-cascade proxy).
Conditions: ADX < 20 (range), low efficiency ratio, with the ~50-day trend, volatility contraction, first event.

**Result: 0 of 48 cells pass on DEV. HOLDOUT was not read (nothing to confirm).**

| Family (C0 ALL) | n | net bp/trade | excess over drift | symbols + |
|---|---|---|---|---|
| F1 stretch | 4576 | -38.1 | -23.2 | 3/10 |
| F2 wick | 7265 | -10.0 | +3.4 | 3/10 |
| F3 re-entry | 4361 | -15.4 | -0.8 | 4/10 |
| F4 sweep + reclaim | 5575 | -15.9 | 0.0 | 2/10 |
| F5 failed breakout | 1939 | -9.8 | +7.4 | 5/10 |
| F6 absorption | 202 | +2.3 | +15.9 | 6/10 |
| F7 CVD divergence | 3363 | -68.3 | -27.6 | 1/10 |
| F8 capitulation | 947 | -89.6 | -75.1 | 2/10 |

Best cells (none significant; the largest |t| after Holm is far from 0.05): "with the 50-day trend" was positive in
7/8 families (+12 to +29 bp), but it is not significant, the 2023-24 half is negative in most families, and
it is a pullback-in-trend (time-series momentum) effect, which E29 already showed does not survive HOLDOUT.

### Diagnosis of the four questions (H1-H4)

| Question | Evidence | Answer |
|---|---|---|
| H1 wrong regime? | F1 in ADX < 20: -15.5 bp; F2 in range: -21.8 bp; low-ER: -9.5 bp | Range regime reduces the loss but does not create an edge |
| H2 wrong timing? | Waiting for confirmation (wick -10, re-entry -15) beats entering on the stretch (-38) | Timing matters, but confirmed entries are still negative |
| H3 wrong signal? | Unconditional stretch: excess -23 bp; the 72 h gross keeps going the other way (-80 bp) | Yes: the deviation carries no reversal information on 4h-72h |
| H4 wrong exit? | F1: SMA touched within 24 h only 23 %; median MAE 1.29 ATR > MFE 1.08 ATR | No: price moves against the entry more than for it; exits are not the cause |

Order flow (F6, F7) and liquidity events (F4, F5, F8) did not add predictive power for reversal.
F6 absorption is too rare (202 events in 5 years, 10 symbols) to test.

## E37 — follow-up: continuation after the same events, 72 h

DEV showed the opposite of reversal (continuation) after F1, F7, F8. That was found on DEV, so HOLDOUT
(never read in E36) is the test. 3 tests, Holm.

| Family | DEV net bp (source) | HOLDOUT net bp (test) | HOLDOUT t (day) | symbols + |
|---|---|---|---|---|
| F1 stretch | +24.1 | -51.0 | -2.44 | 1/10 |
| F7 CVD divergence | +98.4 | -48.5 | -2.55 | 3/10 |
| F8 capitulation | +57.6 | -83.8 | -1.35 | 2/10 |

**E37 FAIL.** The sign flipped: 2020-2024 continued, 2025-2026 reverted.

## Conclusion

- The response to single-symbol price and flow events on 4h-72h has **no stable sign**. It follows the market
  era (trending 2020-21 vs choppy 2025-26), which cannot be known in advance from these features.
- No conditional mean-reversion edge exists in this data. Tested: regime (ADX, efficiency, volatility),
  timing (first touch, wick, re-entry), liquidity (sweep, failed breakout), order flow (absorption, CVD),
  and liquidation proxies. The continuation mirror fails as well.
- Combined with E9-E35, the evidence says single-symbol directional prediction from price, volume, taker flow,
  OI and funding does not survive costs out-of-sample here. The only validated source remains cross-sectional
  funding carry (XS-COMBO-V1).
- The hypothesis is rejected. MeanReversion stays off the live allowlist. Research moves to the XS-COMBO sleeve:
  R5 (carry decay monitor) and R6b (reversal-timed rebalancing).

## Limits

- No historical liquidation or order-book data (Binance liquidation snapshots discontinued; OBI is live only).
  F6-F8 are proxies. A real liquidation/OBI study would need live collection over months before any test.
- 4h bars only; intraday was already rejected (E9-E28, R3).
