# Recent BingX VST Exit Audit — 2026-09-01

## Outcome

The operator's concern is supported as a remediation hypothesis. It is not yet evidence that moving
the stop specifically at +10% or +12% to +4% or +5% is optimal.

## Evidence

- Latest 50 completed positions reconstructed from filled BingX entry and reduce-only exit orders.
- 38/50 net-positive under the fee-adjusted calculation.
- 48/50 exits were `STOP_MARKET`; 2/50 were `TAKE_PROFIT_MARKET`.
- Under a 10x sensitivity calculation: 23/50 reached estimated MFE >=10% ROE; 19/50 reached >=12%;
  14/50 reached >=10% but exited below +5% net ROE; nine of those finished at +2% to +5%.
- Median estimated MFE was +9.84% ROE, median net exit was +2.25%, and median giveback was 9.11
  percentage points under the same 10x view.

## Interpretation limits

- `allOrders` did not populate historical leverage. The 10x view is supported by all three currently
  open VST positions reporting 10x and the manager's default 10x calculation, but remains an inference
  for closed positions.
- MFE/MAE use public one-minute high/low candles. They do not prove that the polling manager observed
  an intraminute extreme, that a replacement stop was accepted, or that mark price crossed it.
- Net ROE uses recorded realized profit plus signed entry/exit commissions against estimated margin.
- This selected recent sample is diagnostic. It cannot safely choose new trailing parameters.

## Confirmed code/configuration concerns to investigate

1. Loaded risk configuration caps leverage at 5x, while current exchange positions report 10x.
2. `ActivePositionManager` estimates ROE with a fixed default 10x rather than authoritative per-position
   leverage.
3. Documentation/comments disagree on the breakeven trigger (5%, 6%, and a stage comment saying 8%).
4. Candle MFE is not correlated with actual manager ticks, stop cancel/replace acknowledgements,
   exchange-visible stop history, mark-price trigger time, or execution slippage.
5. Restart hydration restores the visible stop but historical evidence does not yet prove that peak
   price/peak ROE survives restart, which could weaken the monotonic trail.

## Professional follow-up standard

1. Build a timestamped lifecycle for each audited position: entry fill, manager ticks, BE decision,
   trail decisions, cancel/replace requests, acknowledgements, exchange-visible stops, trigger, fill.
2. Reconcile exchange leverage against the local cap before every entry and fail closed on mismatch.
3. Calculate ROE from authoritative position leverage, not a fixed multiplier.
4. Add restart and API-failure tests proving the stop never moves backward and retry remains eligible.
5. Preregister competing exit policies on a new forward/OOS cohort, including the operator's proposed
   +10/+12% activation and +4/+5% minimum lock, with fees/slippage and no post-result tuning.
6. Keep edge discovery primary: exit management may preserve an edge, but cannot manufacture weak
   entry expectancy.
