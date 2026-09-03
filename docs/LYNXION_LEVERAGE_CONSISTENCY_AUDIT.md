# Lynxion Leverage Consistency Audit

## Verdict

**FAIL-OPEN — P0 RISK-CORRECTNESS DEFECT.** The configured leverage ceiling is not carried to the
authoritative BingX entry boundary, and an exchange position reporting leverage above the configured
ceiling does not block another otherwise admissible entry.

## Trace

- `RiskConfig.max_leverage` is loaded from `RISK_MAX_LEVERAGE` with a default of 5.0. A separate
  `max_leverage_limit` also defaults to 5.0.
- The canonical `ExecutionIntent`, `Order`, and `Position` contracts have no leverage field. The
  intended/requested leverage is therefore lost before broker admission and exchange submission.
- BingX order payload construction sends symbol, side, type, quantity, position side, and client
  order ID, but neither requests leverage nor verifies the symbol's current exchange leverage.
- `_assert_entry_admission` reads authoritative positions and enforces capacity, duplicates, and
  notional exposure. It does not read `settings.risk.max_leverage`, inspect the exchange `leverage`
  field, or fail when leverage is missing/malformed/mismatched.
- `BingXBrokerAdapter.get_all_positions` discards the exchange leverage field while hydrating the
  canonical `Position`, preventing downstream reconciliation.
- `ActivePositionManager` independently defaults ROE conversion to 10x and is instantiated as a
  singleton without loading authoritative per-position leverage. Its profit-lock trigger semantics
  can therefore diverge from both configuration and exchange state.
- Two orchestrator alert services also hard-code 10x. They are monitoring thresholds, not an entry
  enforcement boundary.

## Characterization Evidence

Focused tests prove that Order/Position carry no leverage, the final BingX admission currently
approves with a mocked authoritative 10x position while configured maximum is 5x, and the position
manager defaults independently to 10x.

## Required Correction Boundary

A separate implementation task must define one authoritative intended leverage, carry it through
the execution contract, explicitly set or verify isolated leverage per symbol before entry, read it
back from BingX, reject missing/malformed/mismatched state, preserve it during hydration, and make
ROE/trailing calculations use the authoritative per-position value. The fix must include tests for
5x/10x mismatch, unavailable readback, malformed leverage, restart hydration, and no exchange order
before successful verification.

No order was placed and no strategy, risk, trailing, symbol-admission, or leverage setting was
changed by this audit.
