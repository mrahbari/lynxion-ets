Continue LYNXION ETS from the current canonical state.

Task: task0045-profitability-validation-and-p1-review

FIRST — READ THESE FILES COMPLETELY:
1. task0044-profitability-forensic-audit-phase2-final.md
2. task0044-p0.1-future-metadata-verification-report.md
3. task0044-p0.1-post-implementation-data-validation-report.md
4. task0044-p0.1-metadata-forwarding-summary.md (if present)
5. data/trade_journal.csv
6. data/trade_features.csv

Also inspect the current source implementation of:
- trade_feature_collector.py
- live_order_journal.py
- multi_broker_service.py

OBJECTIVE:
Do NOT implement P1.1 yet.

We need to validate whether the proposed profitability fix is actually justified before changing strategy/execution behavior.

Current P1.1 hypothesis:
Restrict SHORT positions on the identified problematic/high-wick symbols.

However, do NOT assume this is correct merely because the previous forensic report suggested it.

Perform a fresh, source-code-backed validation using the available completed-trade data.

Determine:

1. Whether SHORT losses are genuinely caused by direction/risk geometry rather than execution or data issues.
2. Whether LONG performance remains materially better.
3. Whether the identified symbols are consistently problematic or were merely exposed to unusual market conditions.
4. Whether the positive long-only/non-anomalous counterfactual survives independent recalculation.
5. Whether a symbol-specific SHORT restriction is actually the smallest defensible P1 change.
6. Whether there is a better P1 candidate than P1.1.

IMPORTANT:
- Do not modify production code.
- Do not modify strategy logic.
- Do not disable SHORT yet.
- Do not blacklist symbols yet.
- Do not optimize parameters.
- Do not curve-fit.
- Do not fabricate missing SL/TP metadata.
- Clearly classify conclusions as FACT / INFERENCE / HYPOTHESIS / UNKNOWN.
- Separate ENTRY QUALITY, RISK GEOMETRY, EXIT MANAGEMENT and EXECUTION QUALITY.

Also verify that P0.1 is actually working for NEW trades:
- confirm metadata is being written at intent creation;
- confirm the join into trade_features.csv works;
- identify whether any newly generated trades still have missing metadata;
- report exact resolution percentages.

Then produce:

# TASK0045 — PROFITABILITY VALIDATION & P1 REVIEW

Sections:

1. Current System State
2. P0.1 Verification
3. Updated Performance Baseline
4. LONG vs SHORT Analysis
5. Symbol-Level Analysis
6. Entry vs Risk vs Exit vs Execution Diagnosis
7. Counterfactual Validation
8. P1 Candidate Ranking
9. FACT / INFERENCE / HYPOTHESIS / UNKNOWN
10. Recommended Minimal Change
11. Validation Plan
12. Explicit DO-NOT-CHANGE List

FINAL RULE:

STOP after the forensic analysis.

Do NOT modify production code.

Do NOT implement P1.

End with one of:

- P1.1 APPROVED FOR IMPLEMENTATION
- P1.1 NOT JUSTIFIED
- ALTERNATIVE P1 RECOMMENDED
- INSUFFICIENT EVIDENCE

Wait for my explicit approval before making any P1 code changes.