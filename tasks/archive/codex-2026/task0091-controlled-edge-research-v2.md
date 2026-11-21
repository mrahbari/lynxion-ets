# TASK-0091 — Controlled Edge Research v2

**Status:** COMPLETE — C-04 REJECTED

## Objective

Evaluate candidate C-04 from `tasks/research/edge-candidate-register-v2.md` without modifying
production strategy, execution, risk, sizing, or exit logic. Reuse existing research/backtest
infrastructure and historical data.

## Acceptance Criteria

- Registration commit precedes evaluation output.
- Four disjoint chronological OOS folds.
- BTC/ETH/SOL and BUY/SELL results remain separable.
- Costs are included and zero-cost results are not used for a decision.
- Any missing path-dependent execution fidelity is reported as a limitation, not silently
  treated as deployable evidence.
- Decision is KEEP FOR FURTHER VALIDATION or REJECT; never automatic production promotion.

## Evaluation Evidence

The protocol was committed as `b6281f5` before evaluation. The deterministic evaluator uses
the existing VWAPReversal adapter on processed 5m BTC/ETH/SOL candles, a fixed 12-bar horizon,
and the preregistered 0.30% round-trip cost.

Data coverage:

- BTCUSDT: 8,641 bars, 2026-06-19 13:05 UTC through 2026-07-19 13:05 UTC.
- ETHUSDT: 8,647 bars, 2026-05-21 21:50 UTC through 2026-06-20 22:20 UTC.
- SOLUSDT: 8,641 bars, 2026-06-19 13:05 UTC through 2026-07-19 13:05 UTC.

The regime label test proves that mutating future bars cannot change earlier regime labels.
Each symbol is split chronologically into four disjoint folds; the report does not claim that
the three symbol histories share identical calendar boundaries.

## Results

| Cell | N | Net expectancy/signal | PF | Win rate |
| --- | ---: | ---: | ---: | ---: |
| Overall | 4,765 | -0.3036% | 0.1611 | 17.75% |
| BUY | 2,763 | -0.3147% | 0.1369 | 15.85% |
| SELL | 2,002 | -0.2882% | 0.1952 | 20.38% |
| BTCUSDT | 1,711 | -0.2943% | 0.1126 | 13.91% |
| ETHUSDT | 1,610 | -0.3058% | 0.1725 | 17.83% |
| SOLUSDT | 1,444 | -0.3122% | 0.1981 | 22.23% |

Fold expectancies:

- F1: N=1,145, -0.3229%, PF 0.1363
- F2: N=1,131, -0.3060%, PF 0.2247
- F3: N=1,166, -0.2808%, PF 0.1857
- F4: N=1,323, -0.3049%, PF 0.0994

## Decision

**REJECT C-04.** Zero of four adequately sampled folds are positive. All symbols and both
sides are negative after costs. The candidate fails before path-dependent confirmation, so no
SL/TP simulation or production mutation is justified for C-04.

The positive residual VWAPReversal result in the prospective trade journal was not stable in
the preregistered historical diagnostic and is treated as a post-hoc artifact.

## Reproduction

```bash
python scripts/evaluate_vwap_candidate_v2.py \
  --data-dir data/history/processed/5m
```
