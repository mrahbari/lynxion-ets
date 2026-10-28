# TASK-0103 — Long-Horizon Time-Series Momentum C-14

**Status:** COMPLETE — C-14 REJECTED

## Objective

Evaluate a low-turnover 180-day directional signal with a fixed 28-day holding period on the
six-symbol native futures panel.

## Acceptance Criteria

- Commit the protocol before evaluating C-14 outcomes.
- Prove daily aggregation, shifted entry, holding period, and overlap behavior with tests.
- Keep primary and reverse-time samples separate.
- Apply realistic costs and a month-cluster confidence interval.
- Apply the frozen conjunctive gate without post-result tuning.
- Do not modify production, risk controls, symbol eligibility, or order handling.

## Result

- Primary 2023–2026: 228 trades, -2.5269% net expectancy, PF 0.7286, and month-cluster
  bootstrap 95% interval [-7.7323%, +2.1946%].
- Only fold 1 was positive; folds 2–4 were negative. Only three of six symbols were positive.
- LONG was +2.9290% over 126 trades, while SHORT was -9.2665% over 102 trades. This side clue
  was opened by the result and is not eligible for same-sample reslicing.
- Reverse-time 2020–2022 was positive (+12.6726%, PF 2.6389, N=167), demonstrating strong
  temporal instability rather than a durable edge.
- Primary expectancy remained negative at every frozen cost. Verdict: **REJECT**.

No production or risk-control behavior changed.
