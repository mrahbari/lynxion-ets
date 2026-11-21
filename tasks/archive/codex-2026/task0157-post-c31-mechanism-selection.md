# TASK-0157 — Post-C31 Mechanism Selection

**Status:** COMPLETE

## Objective

Apply the frozen sequential-research policy after C-31 without relaxing an opened result or
creating another correlated directional-price variant.

## Decision

C-31 closes the available same-asset Spot-to-perpetual underreaction specification. The existing
historical panels have also opened momentum, reversal, funding, OI, depth, taker-flow, basis,
cross-symbol lead/lag, volatility-sweep, and positioning mechanisms. Recombining those opened
features or changing their thresholds, symbols, directions, or horizons would be candidate churn,
not independent evidence.

The next admissible mechanism is **prospective cross-venue perpetual price dislocation**. It tests
temporary disagreement between independently executable perpetual markets and is structurally
different from Spot/perpetual basis convergence and directional prediction. Its economic claim is
market-neutral convergence after observed executable spreads exceed round-trip fees, bid/ask
spread, funding, and slippage on both legs.

## Next Unit

TASK-0158 must preregister a read-only feasibility collector before recording any conditional
outcome. It must freeze:

- venue and symbol eligibility from public, unauthenticated market-data endpoints only;
- synchronized exchange timestamps, bid/ask prices, depth/size requirements, and stale-quote rules;
- a prospective UTC boundary and append-only raw observations with source/provenance hashes;
- two-leg entry/exit pricing, fees, funding, latency allowance, slippage, and failure-to-fill costs;
- a no-lookahead convergence outcome, overlap rule, minimum sample, venue/symbol/time breadth,
  clustered uncertainty, concentration, drawdown, and stress-cost gates;
- fail-closed handling for missing, crossed, stale, malformed, or non-comparable contracts.

TASK-0158 may not authenticate, place real or paper orders, call broker execution paths, mutate the
running system, import pre-boundary observations, or calculate a candidate verdict. If comparable
public quotes cannot be collected reproducibly, the mechanism is data-blocked rather than retuned.

## Result

One genuinely distinct prospective mechanism is admitted for **data-feasibility preregistration
only**. No edge is claimed and no production setting changes.
