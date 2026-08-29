# TASK-0087 — Exchange-Side Profit Lock and Trailing Stop Verification

**Priority:** P0 operational safety / execution correctness  
**Status:** IN PROGRESS — mechanical defect verified; live VST repair remains approval-gated  
**Scope:** Verify and minimally repair existing `ActivePositionManager` profit-lock and
trailing-stop execution. Do not add a new exit framework or alter strategy parameters.

## Problem Statement

The existing intended policy is not yet proven against BingX VST execution:

1. At the configured breakeven/profit-lock threshold, an open position must have its
   exchange-side stop moved to at least entry plus the configured fee/slippage buffer for a
   long (or entry minus the buffer for a short).
2. At the trailing threshold, the exchange-side stop must ratchet in the profitable
   direction from the observed peak price and must never loosen.
3. A local in-memory state update or log line is not sufficient evidence; the amended
   exchange-side conditional order must be verified by a read-only pending-order query.

Read-only VST evidence obtained during this task confirms the defect: ZECUSDT is LONG at
793.89 entry / 810.56 mark (about +21.00% ROE at the configured 10x estimate) with its
STOP_MARKET still at 784.79, below entry. AVAXUSDT is SHORT at 7.553 entry / 7.270 mark
(about +37.47% ROE) with its STOP_MARKET still at 7.700, above entry. Both exceed the
configured +6% profit-lock and +10% trailing triggers but do not have an exchange-side
profit-lock stop. No orders were changed while collecting this evidence.

An additional startup defect was confirmed after a runner restart: background services were
started while `is_running` was still false. The trailing loop uses that flag as its loop
condition, so it could exit before its first evaluation. The corrected startup sequence sets
the flag before launching any background thread; a regression test asserts that ordering.

A third mechanical blocker was found from live evidence: the multi-broker protection loop
could abort its full pass when an earlier non-BingX adapter raised, preventing later BingX
positions from being evaluated. Broker evaluation is now isolated, so a failure is logged and
the loop continues to the remaining adapters, including BingX VST.

The VST primary broker is now evaluated first in each protection pass. This prevents market
data/API work for ancillary exchanges from delaying a BingX stop adjustment for qualifying
positions such as CCUSDT, INJUSDT, or AAVEUSDT.

Restart handling now hydrates the existing exchange-side stop into the manager state before
computing a new breakeven/trailing candidate. An already profit-locked stop is retained and is
only amended if a later candidate is strictly more protective.

## Guardrails

- Do not close, reduce, or otherwise alter an existing VST position without explicit operator
  authorization.
- Do not modify real-money settings, historical trade rows, prospective boundaries, strategy
  thresholds, or risk limits.
- Use VST/testnet only for any exchange-side verification.
- Preserve mandatory SL and TP coverage throughout every test.
- Fail closed: an inability to read, create, replace, or verify a protective order must be
  surfaced as a safety failure; it must not be represented as a successful profit lock.

## Evidence to Collect

1. Current `ActivePositionManager` threshold/configuration values and all call sites.
2. ZEC and AVAX VST position entry price, mark price, side, ROE, pending SL/TP orders, and
   order-update history, obtained read-only and without exposing credentials.
3. Broker adapter semantics for cancelling/replacing conditional SL orders and the exact
   acknowledgement returned by BingX VST.
4. Existing logs/journal entries that demonstrate (or fail to demonstrate) a real amendment.

## Acceptance Criteria

- Regression tests cover long and short positions at: below trigger, breakeven trigger,
  trailing trigger, new favorable peak, and adverse retrace.
- For a long, the profit-lock SL is greater than entry by the configured buffer; for a short,
  it is lower than entry by the configured buffer.
- A trailing SL only moves toward profit; no code path loosens it after a new evaluation.
- Tests assert the broker-side amend/cancel-replace call and a subsequent pending-order
  verification, not merely local state mutation.
- Restart persistence restores the latest protected-stop state without duplicate amendments.
- A VST observation report for ZEC and AVAX is produced. Any required live order amendment is
  presented to the operator before execution.
- The runner is restarted after the startup-order correction and the active-position loop's
  startup is evidenced before asserting live trailing behavior.
- Full local test suite remains green.

## Deliverables

- Minimal production-code correction only if a verified mechanical defect exists.
- Focused regression tests.
- Read-only VST evidence report for ZEC and AVAX.
- Update to `docs/LYNXION_GROUND_TRUTH_AUDIT.md` with facts, commands, remaining risk, and
  any operator decision required.

## Explicit Do Not Do

- Do not claim economic benefit from trailing based solely on one or two positions.
- Do not tune trigger thresholds from the current prospective cohort.
- Do not use close prices to simulate intrabar stop behavior in research validation.
