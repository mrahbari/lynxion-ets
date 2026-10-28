# TASK-0193 — Shadow fee-provenance contract audit

## Scope

Determine whether the existing prospective lifecycle schema can supply the frozen
entry-fee and expected-exit-fee inputs required by Exit Policy Register v1. Do not call
the broker, infer fees, or open outcomes.

## Facts

- `MANAGER_EVALUATED` observations contain entry price, quantity, mark, authoritative
  leverage, and stop state, but no entry fill ID, entry commission, or fee rate.
- Position identities may carry exchange position/order IDs, but the BingX `Position`
  hydration path currently drops these source identifiers; active records can therefore
  contain null IDs.
- `EXIT_FILL_OBSERVED` extracts commission from the terminal order only. It does not
  establish entry commission or the fee schedule known at candidate activation.
- The historical 98-position audit could sum entry and exit commissions because it
  reconstructed both orders by `positionID`; that historical source is explicitly
  excluded from the new prospective policy cohort.

## Verdict

`DATA_CONTRACT_BLOCKED — ENTRY_FEE_PROVENANCE MISSING`.

Running the shadow evaluator with a guessed zero, a retrospective aggregate average,
or a hard-coded taker fee would violate the preregistered net-floor definition and
could falsely label a gross +5% stop as a net +5% floor.

## Minimal resolution boundary

1. Preserve an authoritative exchange position/entry-order linkage during BingX
   hydration when the endpoint supplies it; never synthesize an ID.
2. Add disconnected admission of a filled entry order only when symbol, side,
   position identity, quantity, and time order all match.
3. Capture signed entry commission and the expected exit fee rate/source known before
   the first +12% activation observation.
4. Missing, ambiguous, duplicate, post-activation, or cross-position evidence makes
   that position ineligible rather than substituting a default.
5. Keep fee capture observational; it must not add an execution call or change orders.

## Next

TASK-0194: map the exact existing BingX order-history and position-hydration fields and
implement a pure disconnected entry-fee evidence extractor with adversarial tests.
Runtime wiring remains combined with the already pending controlled reload gate.
