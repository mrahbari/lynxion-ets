# Phase 6 · Predictive-Power Measurement Harness (Step 1)

Research-grade evaluation layer for **signal quality only**. Implements the
protocol in `docs/reports/phase6/phase6-signal-predictive-power-protocol.md`.
This is the foundation layer of Phase-6 edge discovery.

**Hard scope (by design):** NO SL/TP, NO sizing, NO cost model, NO trading
simulation, NO backtest, NO optimization. It measures whether a signal predicts
forward returns — nothing about how it would be traded. Promoted signals are
later handed to the *separate, existing* execution/edge-gate stack.

## Modules

| module | responsibility |
|---|---|
| `forward_labels.py` | forward-return labelling (raw + vol-normalised); last `h` rows NaN guarantees no future-less label |
| `predictive_power.py` | IC with **Newey-West (HAC)** t-stat (overlap-robust), decile-spread, event-study CAR, block-IC stability |
| `cv.py` | **purged + embargoed** walk-forward & k-fold; `assert_no_leakage` enforces train-before-test + embargo ≥ horizon |
| `multiple_testing.py` | Benjamini-Hochberg FDR + Deflated-Sharpe expected-max-under-null |
| `harness.py` | orchestrator: per-symbol + regime-conditional evaluation, cross-symbol aggregation, promote/archive verdict, `EdgeLedger` |

## No-lookahead / no-leakage guarantees

- Labels are forward (`log(close[t+h]/close[t])`); the **signal** must use only
  data ≤ t (caller's contract). Vol-normalisation uses backward-looking vol.
- CV `embargo` defaults to `max(horizons)` so a test label cannot overlap any
  training observation; `assert_no_leakage` verifies train-strictly-before-test
  and the embargo gap on every split.

## Usage

```python
import sys; sys.path.insert(0, "research/edge_discovery/measurement")
from harness import evaluate_across_symbols, EdgeLedger

res = evaluate_across_symbols(
    signal_by_symbol={"BTC": sig_btc, "ETH": sig_eth, "SOL": sig_sol},
    close_by_symbol={"BTC": close_btc, "ETH": close_eth, "SOL": close_sol},
    horizons=[1, 5, 15, 60], n_trials=<pre-registered # hypotheses>,
    regime_by_symbol={"BTC": regime_btc, ...},   # optional
)
# res["overall_verdict"] in {PROMOTE, PROVISIONAL, ARCHIVE, INSUFFICIENT_DATA}
EdgeLedger().record("my_signal", "cross_sectional", res).save()  # -> results/
```

## Promotion gate (default posture = REJECT)

A symbol PROMOTES at its best horizon only if **all** hold: BH-significant IC
(family scaled to `n_trials`), `|IC| ≥ 0.02`, decile monotonicity ≥ 0.6 with
spread sign == IC sign, OOS walk-forward sign-consistency ≥ 0.6, and block
sign-consistency ≥ 0.6. Overall PROMOTE requires a majority of symbols promoting
with the **same IC sign** (else PROVISIONAL / ARCHIVE).

## Validation

13-test suite at `tests/unit/test_edge_discovery_measurement.py` (tests/ is gitignored — run
locally): proves no-lookahead labels, HAC IC, BH-FDR, leakage-proof CV, and the
end-to-end behaviour — **detects a synthetic real edge, rejects pure noise**.

    .venv/bin/python3 -m pytest tests/unit/test_edge_discovery_measurement.py -q

## Outputs

`results/` — edge ledger of tested hypotheses (the Phase-6 analogue of the
Phase-5 blocker ledger). Records verdicts only, never trading results.

## Not in scope here (later, separate, on authorization)

Data ingestion, hypothesis generation, strategy design. This layer is the
measurement foundation; it does not produce or trade signals.
