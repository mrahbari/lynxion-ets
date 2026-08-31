# Post-C23 Cross-Family Evidence Synthesis

## Decision

C-23 rejects next-settlement positive-funding carry because its gross capital-normalized return
(+0.0086%) is economically far below realistic two-leg costs. Threshold or holding-period variants
on the opened carry panel are prohibited.

The next admissible mechanism is **delta-neutral spot/perpetual basis convergence**. It is distinct:

- C-20 traded the perpetual directionally from the premium-index signal; it retained market beta.
- C-23 held a spot/perpetual hedge selected by completed funding and tested funding persistence.
- The proposed C-24 selects an observed spot/perpetual price dislocation, shorts the expensive leg,
  buys the cheap leg, and tests convergence while remaining equal-notional and market-neutral.

TASK-0118 makes exact point-in-time spot/perpetual reconstruction possible for the first time.
The mechanism has a direct payoff source (basis compression), causal inputs, and measurable capacity
to clear costs only when the initial dislocation is sufficiently large. Funding remains an execution
cashflow, not the signal.

## Sequential-Policy Assessment

- New mechanism family: yes; direct two-leg basis convergence.
- Point-in-time reconstructable: yes; exact common native 15-minute timestamps only.
- Outcome unopened: yes; no C-24 conditional results have been computed.
- One primary specification: required before evaluation.
- Production implication: none; even a historical KEEP requires prospective validation.

## Rejected Next Steps

- No C-23 funding threshold, duration, symbol, or cost variant.
- No directional premium-index variant of C-20.
- No reuse of diagnostic positive cells from rejected candidates.
- No strategy, broker, risk, trailing, or order mutation.

## Next Unit

Preregister C-24's causal basis definition, dislocation threshold, leg direction, entry/exit,
funding cashflows, costs, folds, clustered bootstrap, reverse period, and all-or-nothing gates before
opening any conditional outcome.
