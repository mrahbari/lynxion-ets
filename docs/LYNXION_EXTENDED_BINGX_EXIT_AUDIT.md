# Extended BingX VST Exit Audit — 2026-09-06

## Verdict

`PERSISTENT_GIVEBACK_DIAGNOSTIC — NOT A 5% POLICY VERDICT`

The maximum official single-response order history reconstructed 98 completed
positions, two short of the preregistered N=100 target. Profit giveback appears in
both non-overlapping 49-position temporal blocks and therefore is not confined to the
latest 50 trades. The sample still cannot establish that a 5% floor is optimal or
executable.

## Frozen-sample results

- Coverage: 98 completed BingX VST positions from 2026-08-30 through 2026-09-06.
- Realized account result: +6.001067 VST/USDT-equivalent total; +0.061235 per position;
  realized-profit PF 1.6088; 74/98 net-positive.
- Exit orders: 89 `STOP_MARKET`, seven `TAKE_PROFIT_MARKET`, and two `MARKET`.
- Ten-times sensitivity: median estimated MFE +11.61% ROE, median net exit +2.29%,
  and median MFE-to-exit giveback 10.19 percentage points.
- 56/98 reached estimated MFE >=10%; 47/98 reached >=12%; 27/98 reached >=10%
  but exited below +5%. Thirty-one exits finished between +2% and +5%.

## Temporal persistence

| Block | Net positive | MFE >=10% | MFE >=10%, exit <5% | Net PnL | PF |
|---|---:|---:|---:|---:|---:|
| Newest 49 | 38 | 27 | 12 | +5.440475 | 2.1264 |
| Older 49 | 36 | 29 | 15 | +0.560592 | 1.1115 |

Median giveback was nearly unchanged: 10.10 points in the newest block and 10.26 in
the older block. This strengthens the diagnosis that profit surrender is persistent,
while the much weaker older-block economics warn against extrapolating the latest
block's apparent profitability.

## Attribution signals

- LONG: 51 positions, +6.831217 aggregate net PnL, 13 giveback cases.
- SHORT: 47 positions, -0.830150 aggregate net PnL, 14 giveback cases.
- The result is not broad enough to claim strategy edge: several symbols were negative,
  and PROM/ZEC contributed materially to the positive aggregate.

## Hard limits

- Historical leverage is absent for all 98 positions. Every 10x ROE statistic is a
  normalized sensitivity view, not authoritative realized account ROE.
- MFE/MAE use public one-minute candle extremes. They do not prove that the manager
  observed the extreme, that a replacement reached the exchange, or that the stop
  could fill at the proposed level.
- This recent, overlapping operational sample has no independent policy holdout.
  Selecting +5% from it would be post-result tuning.

## Decision

Prioritize the already diagnosed mutation-latency/stale-snapshot correction, preserve
the active forward lifecycle cohort, and evaluate any 5% net floor only as a frozen
prospective competing policy after execution observability is reliable.

Evidence artifact SHA-256:
`488680c53e431526e7b1bc46b9b55ebe004c988371b07ed8ff9e2bfed6c93a72`.
