# TASK-0092 — Controlled Edge Research C-01/C-02/C-03

**Status:** COMPLETE — C-01/C-02/C-03 REJECTED

## Objective

Evaluate preregistered trend-continuation and volatility-breakout candidates with realistic,
path-dependent execution and four chronological OOS folds, without production mutation.

## Acceptance Criteria

- Protocol commit precedes evaluation output.
- Closed-bar, shifted MTF alignment is tested against future-data mutation.
- Entry occurs no earlier than the next bar.
- SL/TP use candle high/low with SL priority when both are touched.
- Costs are included in every decision metric.
- Symbols, sides, and folds remain separable.
- Results and limitations are documented with an explicit KEEP/REJECT verdict.

## Evaluation Evidence

Protocol v3 was committed as `5465625` before this result existed. The evaluator uses the
existing production strategy adapters, next-bar-open entries, setup-provided SL/TP levels,
intrabar high/low exits, adverse gap handling, SL priority on dual-touch bars, and a fixed
0.30% round-trip cost. Four chronological folds are evaluated independently for each symbol.

Regression tests prove shifted completed-hour alignment, next-open entry, dual-touch SL
priority, overlapping-signal exclusion, and that an unresolved position blocks every later
signal in its fold. The final condition corrected a pre-result simulator defect; all reported
results below were regenerated after that correction.

## Results

| Candidate | N | Net expectancy | PF | Win rate | Unresolved | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| C-01 trend BUY | 12 | -1.2892% | 0.3465 | 16.67% | 5 | REJECT |
| C-02 trend SELL | 17 | +0.5389% | 1.4468 | 52.94% | 1 | REJECT |
| C-03 volatility breakout | 26 | -0.6602% | 0.5826 | 53.85% | 5 | REJECT |

C-01 is negative in every fold and every symbol. C-03 is negative overall, negative on both
sides, and non-positive on all three symbols after costs. C-02 is the only positive aggregate,
but it has no adequately sampled fold: F1/F2 are positive with N=3/8, F3/F4 are negative with
N=3/3, BTC is negative, and the apparent profit is dependent on ETH. It therefore fails the
pre-registered robustness and no-single-symbol-dependence gates.

## Decision

**REJECT C-01, C-02, and C-03.** None is eligible for production or shadow promotion. C-02's
small positive aggregate is retained as a research clue only; it is not statistically
defensible evidence of edge.

Historical bid/ask and funding observations are unavailable. Spread/slippage is represented
by the frozen round-trip cost, and funding is explicitly unmodeled.

## Reproduction

```bash
python scripts/evaluate_edge_candidates_c01_c03.py \
  --output docs/reports/edge_candidates_c01_c03_oos.json
```
