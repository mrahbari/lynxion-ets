  All quantitative tasks and architectural audits up to Task 0039 — Runtime Position Sizing Ownership Audit have been
  successfully executed and validated.
  ──────
  ### Summary of Completed Tasks in Session

  1. Task 0037 — Portfolio Allocation Engine Implementation (COMPLETED):
      • Implemented pure, stateless, thread-safe PortfolioAllocationEngine supporting EQUAL_WEIGHT (1/N) and
      FRACTIONAL_KELLY (0.25 × Quarter-Kelly) modes in infrastructure/risk/portfolio_allocation_engine.py.
      • Built unit test suite tests/unit/test_portfolio_allocation_engine.py (10/10 tests passing).
      • Saved report portfolio_allocation_engine_implementation_report.md.
  2. Task 0038 — Integration Readiness Verification (COMPLETED):
      • Performed read-only audit proving zero active runtime pipeline references to PortfolioAllocationEngine.
      • Proved mathematical equivalence (wᵢ·N = 1.0) when allocation.enabled = false.
      • Saved report allocation_engine_integration_readiness_report.md.
  3. Task 0039 — End-to-End Position Quantity Ownership Audit (COMPLETED):
      • Traced the 6-step runtime execution call chain from strategy signal setup down to exchange submission.
      • Documented component quantity ownership matrix and double-scaling risk audit (0.0% risk).
      • Verified that PositionSizingEngineAdapter.compute_size is the EXACT AND ONLY single point of sizing ownership.
      • Saved report runtime_position_sizing_ownership_audit_report.md.

  ──────
  ### Codebase & Test Suite Status

  • Unit Tests: 382 / 382 Passed (100% Green).
  • Documentation Index: Updated README.md indexing all reports.
  • Pipeline Safety: Pipeline execution paths remain 100% frozen and invariant.






Task 0040 — Controlled Portfolio Allocation Engine Integration & Disabled-Mode Parity Validation

Role:
Act as Principal Quant Engineer responsible for safe production integration.

Objective:
Integrate PortfolioAllocationEngine into the existing position sizing pipeline in a strictly controlled manner and prove zero behavioural regression before enabling live usage.

IMPORTANT CONSTRAINTS

- Architecture remains frozen.
- No strategy logic changes.
- No indicator changes.
- No signal generation changes.
- No backtester changes.
- No DerivativesRiskGate changes.
- No broker changes.
- PortfolioAllocationEngine is the only new sizing component.

======================================================
PHASE 1 — CONFIGURATION WIRING
======================================================

Integrate PortfolioAllocationConfig through the existing configuration system.

Verify:

- allocation.enabled=false remains default.
- Existing production configuration produces identical behaviour.
- Missing configuration fails safely.

Required validation:

allocation.enabled=false

must guarantee:

Signal count unchanged.
Trade count unchanged.
Order direction unchanged.
Entry timestamp unchanged.
Stop loss unchanged.
Take profit unchanged.
Position quantity unchanged.

======================================================
PHASE 2 — DEPENDENCY INJECTION VALIDATION
======================================================

Verify PortfolioAllocationEngine registration in the existing DI container.

Audit:

- construction lifecycle
- singleton/transient scope
- dependency availability
- startup failures
- circular dependency risks

======================================================
PHASE 3 — POSITION SIZING PIPELINE INTEGRATION
======================================================

Integrate only at:

PositionSizingEngineAdapter.compute_size()

Expected flow:

Q_base

↓

PortfolioAllocationEngine.calculate_weight()

↓

Q_base × (wi × N)

↓

RiskGate multiplier

↓

EnterpriseRiskManager clamp

↓

Broker formatting


Verify:

Allocation scaling occurs exactly once.

======================================================
PHASE 4 — DISABLED MODE REPLAY PARITY TEST
======================================================

Run deterministic replay with:

allocation.enabled=false

Compare against Task 0030 baseline.

Required:

0 signal divergence

0 trade divergence

0 quantity divergence

0 PnL divergence

0 ledger divergence

======================================================
PHASE 5 — ENABLED MODE PAPER VALIDATION
======================================================

Enable:

allocation.enabled=true
allocation_mode=FRACTIONAL_KELLY

Run controlled paper replay.

Validate:

- weight sum = 1.0
- no NaN/Infinity weights
- no missing assets
- deterministic output
- position scaling matches research output

======================================================
PHASE 6 — SAFETY TESTS
======================================================

Test:

1. Missing performance statistics
   Expected:
   Equal Weight fallback.

2. Invalid Kelly inputs
   Expected:
   Equal Weight fallback.

3. Empty asset universe
   Expected:
   Signal rejection.

4. RiskGate BLOCK
   Expected:
   No order emitted regardless of allocation.

5. RiskGate REDUCE_SIZE
   Expected:
   Allocation scaling happens first, risk multiplier second.

======================================================
REQUIRED OUTPUT

Generate:

1. Integration change summary.
2. Runtime call graph after integration.
3. Disabled-mode parity results.
4. Enabled-mode paper validation results.
5. Safety test results.
6. GO / HOLD / STOP recommendation.

Do not modify strategy algorithms.
Do not redesign architecture.
Do not add speculative abstractions.