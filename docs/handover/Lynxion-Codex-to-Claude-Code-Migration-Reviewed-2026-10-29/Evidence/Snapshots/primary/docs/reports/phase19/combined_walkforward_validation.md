# Phase 19 — Combined-Signal Walk-Forward Validation

**Date:** 2026-06-13. Analysis only; no profitability claim. Walk-forward (4 folds) and cross-symbol
robustness for the combined signals, net of 0.30% cost. Raw: `phase19_results.json`.

## Walk-forward fold nets (capitulation combo, the only positive candidate)

| Symbol / horizon | fold-1 | fold-2 | fold-3 | fold-4 | folds + | all-pos? |
|---|---:|---:|---:|---:|:--:|:--:|
| BTC 24h | +0.57% | −0.05% | −0.30% | +0.03% | 2/4 | ❌ |
| BTC 72h | **+2.35%** | +0.07% | −0.44% | +0.49% | 3/4 | ❌ |
| ETH 24h | +2.34% | +1.32% | −0.72% | −0.24% | 2/4 | ❌ |
| ETH 72h | +1.74% | +2.85% | −0.77% | −0.31% | 2/4 | ❌ |
| SOL 24h | (n/a) | −1.52% | +0.49% | −0.77% | 1/3 | ❌ |
| SOL 72h | (n/a) | +0.18% | −0.38% | −2.18% | 1/3 | ❌ |

- **Not a single combined signal is positive across all folds** on any symbol (the lone all-positive cell
  anywhere is capitulation+liquidity on BTC 24h, n=64 — too small to rely on).
- The positive BTC/ETH means are **driven by 1–2 early folds** (e.g. BTC 72h: +2.35% in fold-1, ~0 or
  negative afterward; ETH 72h: folds 1–2 positive, 3–4 negative). This is the **same back-loaded /
  single-window instability** flagged in Phases 12/14/15 — the edge is not stationary.
- **SOL fold nets are mostly negative**, confirming the cross-symbol failure.

## Cross-symbol robustness

| Signal @72h | BTC | ETH | SOL | cross-symbol verdict |
|---|---:|---:|---:|---|
| COMBO capitulation | +0.635% | +0.404% | −1.146% | **fails** (SOL negative) |
| COMBO exhaustion | −0.495% | −0.649% | −0.362% | fails (all negative) |
| COMBO capit+liqexp | +0.769% | −0.359% | −0.654% | fails (ETH/SOL negative) |

- The only positive signal (capitulation) is positive on **2 of 3** majors and strongly negative on the
  third — it does **not** generalise. A deployable edge must hold across symbols; this does not.

## Does the combination beat its components? (validation summary)

| | survives cost on BTC/ETH? | survives cost on SOL? | all-fold stable? | beats funding-only? |
|---|:--:|:--:|:--:|:--:|
| funding-only extneg | ✅ (BTC/ETH) | ❌ | ❌ | — |
| COMBO capitulation | ✅ (BTC/ETH) | ❌ | ❌ | ❌ (helps BTC, hurts ETH/SOL) |

The combination is **statistically indistinguishable in character from the funding-only thread**: same
symbols win, same symbol fails, same fold-fragility — and the microstructure filter does not produce a
net improvement. **Combining the two weak signals did not create a stronger one.**

## Conclusion

No combined signal is **cost-surviving + cross-symbol + walk-forward-stable**. The capitulation combo is
real and cost-surviving on BTC/ETH at 24–72h but is inconsistent (SOL-negative) and fold-fragile, and
microstructure adds no reliable value over funding-only. Classification → `phase19_final_verdict.md`.
