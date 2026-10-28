# TASK-0108 — OI-Flush Exhaustion Reversal C-17

**Status:** COMPLETE — C-17 REJECTED

## Objective

Acquire the new conditional universe and evaluate one OI-contraction exhaustion/reversal
hypothesis without reusing C-16 symbols.

## Acceptance Criteria

- Commit protocol before acquiring/opening the new OI-conditioned outcomes.
- Checksum and validate price, OI, and funding for both temporal samples.
- Reuse strict causal alignment and execution semantics; reverse direction only because the
  frozen mechanism is exhaustion/reversal.
- Apply the conjunctive gate without post-result changes.
- No production, broker, risk, symbol-admission, or order changes.

## Result

- New-universe OI: 8,665 official archives, approximately 2.49M unique observations, zero core
  integrity violations. Funding and reverse-price panels also passed with zero violations.
- Primary: 2,124 trades, -0.3546% funding-inclusive expectancy, PF 0.7983, and day-cluster
  bootstrap 95% CI [-0.5987%, -0.1115%].
- All four primary folds, both sides, and all five symbols were negative.
- Price-only expectancy was -0.3518%; mean funding contribution was -0.0028%.
- Reverse-time was effectively flat (+0.0146%, PF 1.0066, N=531) and cannot rescue primary.
- Frozen verdict: **REJECT**.

No production, broker, risk, symbol-admission, or order behavior changed.
