# TASK-0104 — Independent Long-Only Trend Holdout C-15

**Status:** COMPLETE — C-15 REJECTED BY ROBUSTNESS GATE

## Objective

Test C-14's post-result LONG clue once on five new perpetual-futures symbols without reusing
the opened six-symbol outcome panel.

## Acceptance Criteria

- Commit the boundary before acquiring the new price panel.
- Verify futures provenance, alignment, gaps, OHLC validity, and checksums.
- Reuse the frozen 180-day/28-day C-14 mechanics with LONG-only admission.
- Apply the frozen fold/symbol/concentration/confidence/cost gate.
- Do not change production or risk controls.

## Result

- New panel: five symbols × 128,352 aligned 15m bars, zero gaps, duplicates, OHLC errors, or
  range violations; checksums are frozen in the C-15 manifest.
- Primary cost: 82 LONG trades, +1.4752% expectancy, PF 1.1504; expectancy remained +1.2752%
  at 0.50% cost.
- Month-cluster bootstrap 95% CI was [-8.1466%, +11.9049%].
- Only one adequately sampled fold was positive; fold 4 had no qualifying LONG observations.
- Only DOGE and LINK were positive with the required sample. Maximum positive-PnL symbol
  concentration was 39.60%, above the frozen 35% ceiling.
- Frozen verdict: **REJECT**. Positive aggregate return is not sufficient evidence of a stable
  edge.

No production, risk, symbol-admission, or order behavior changed.
