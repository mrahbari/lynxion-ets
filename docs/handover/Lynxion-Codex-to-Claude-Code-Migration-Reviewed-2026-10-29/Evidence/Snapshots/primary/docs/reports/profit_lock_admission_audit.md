# Forward Profit-Lock Admission Audit

## Decision

Do not change the trailing trigger or profit floor from the latest 50-position diagnostic. First
collect causal forward events that distinguish manager intent from exchange execution.

## Why the Proposed Rule Is Not Yet Distinct

For a long position, the intended trailing floor after a peak is:

`locked_roe = ((peak_price * (1 - 0.005) - entry_price) / entry_price) * leverage`

At 10x and a +10% ROE peak, `peak_price / entry_price = 1.01`, so the intended stop locks about
`(1.01 * 0.995 - 1) * 10 = 4.95%` ROE before friction. This is already the operator's proposed
`+4% to +5%` floor. A +12% peak implies about +6.94% at 10x; +10% ROE at 5x implies about +7.45%.

The diagnostic giveback therefore does not prove that a different threshold is required. It may
instead reflect missed evaluations, untrusted leverage, broker rejection, stop invisibility,
restart hydration, slippage, or fill behavior. One-minute candle extremes cannot identify which.

## Frozen Next Step

Connect the append-only exit event ledger to the manager and stop lifecycle without changing exit
behavior. Require forward-only coverage and the existing minimum data gate before evaluating any
preregistered alternative. Historical events cannot be imported.
