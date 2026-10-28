# New Strategy Validation (RETIRED-slot candidates)

**Date:** 2026-06-13. Same rigor as the suite re-evaluation: real adapter execution on the **design
timeframe**, **per-symbol (BTC/ETH/SOL independent)**, **regime-conditioned**, **cross-period
(half-split)**, and **4-fold walk-forward**, net of the existing 0.30% round-trip cost. A-priori
parameters only — no tuning. Harness: `scripts/validate_replacement_candidates.py`; raw:
`_candidate_validation.json`.

**READY bar:** positive in-regime expectancy **+** cross-period stable-positive **+** regime-consistent
**+** walk-forward (positive in the majority of folds), on at least one symbol.

## Results (in-regime expectancy, net of cost)

### C1 — Short-Term Statistical Reversal (15m, ranging)
| Symbol | signals | all-signal | in-regime | n | win rate | cross-period | WFO positive folds |
|---|---|---|---|---|---|---|---|
| BTC | 1441 | −0.332% | **−0.327%** | 546 | 0.24 | stable-negative | **0/4** |
| ETH | 1120 | −0.359% | **−0.298%** | 422 | 0.34 | stable-negative | **0/4** |
| SOL | 977 | −0.362% | **−0.437%** | 402 | 0.35 | stable-negative | **0/4** |

### C2 — Donchian Channel Breakout (1h, breakout/trend)
| Symbol | signals | all-signal | in-regime | n | win rate | cross-period | WFO positive folds |
|---|---|---|---|---|---|---|---|
| BTC | 524 | −0.281% | **−0.247%** | 360 | 0.31 | stable-negative | **0/4** |
| ETH | 465 | −0.176% | **−0.137%** | 323 | 0.39 | stable-negative | **1/4** |
| SOL | 515 | −0.163% | **−0.377%** | 347 | 0.37 | stable-negative | **1/4** |

## Findings
- **Both candidates are negative net of cost in their intended regime on every symbol** — the same
  pattern as the entire existing suite. Win rates 24–39%.
- **Walk-forward fails decisively:** STR is positive in **0/4** folds on all symbols; DCB in at most
  **1/4**. No candidate is positive in a majority of out-of-sample folds anywhere.
- **Cross-period:** uniformly stable-**negative** (both halves negative) — not a borderline or unstable
  result; the lack of edge is consistent.
- **Adequate sample:** unlike some existing strategies (mean_reversion/vwap_reversal), both candidates
  produced ample in-regime signals (322–546), so the negative verdict is well-powered, not "unjudgeable."

## Classification (Phase E)
| Candidate | Classification | Basis |
|---|---|---|
| Short-Term Statistical Reversal | **INVALIDATED** | Stable-negative in-regime on all symbols; WFO 0/4; well-powered. Directional reversal edge absent net of cost. |
| Donchian Channel Breakout | **INVALIDATED** | Stable-negative in-regime on all symbols; WFO 0–1/4; well-powered. Channel-break continuation edge absent net of cost. |

## Conclusion
Neither candidate meets — or approaches — the READY bar. Both are **INVALIDATED** on evidence. They do
**not** outperform the RETIRED strategies they were meant to replace (RETIRED strategies were removed for
being worse-than-nothing; these candidates are likewise net-negative). **No replacement is justified.**
