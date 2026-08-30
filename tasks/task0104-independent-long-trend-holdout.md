# TASK-0104 — Independent Long-Only Trend Holdout C-15

**Status:** IN PROGRESS — PROTOCOL FROZEN, DATA UNOPENED

## Objective

Test C-14's post-result LONG clue once on five new perpetual-futures symbols without reusing
the opened six-symbol outcome panel.

## Acceptance Criteria

- Commit the boundary before acquiring the new price panel.
- Verify futures provenance, alignment, gaps, OHLC validity, and checksums.
- Reuse the frozen 180-day/28-day C-14 mechanics with LONG-only admission.
- Apply the frozen fold/symbol/concentration/confidence/cost gate.
- Do not change production or risk controls.
