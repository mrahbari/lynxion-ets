# TASK-0090 — TASK 002 Edge Failure Decomposition

**Status:** COMPLETE — dominant failure is execution/risk-control contamination; residual
strategy edge remains unproven

## Decision

The prospective aggregate loss is dominated by a verified XMRUSDT rapid-reentry cascade,
not by fees and not by evidence that every strategy uniformly lacks signal quality. However,
removing that cascade post hoc does not establish a deployable edge. The remaining cohort is
only marginally positive, lacks regime/MFE/MAE attribution, and has not passed the registered
four-fold OOS gate.

No production strategy or exit parameter change is justified by this decomposition.

## Primary Root Cause

The entry-time prospective cohort contains 142 XMRUSDT trades:

- 142/142 exited through `MARKET` with cost-adjusted PnL **-261.7112 VST**.
- 132 were BUY; 10 were SELL.
- 123 of 141 consecutive re-entry transitions occurred less than 60 minutes after the prior
  XMR exit; 116 occurred in under five minutes.
- Entry clusters span five consecutive days: Aug 16 (13), Aug 17 (37), Aug 18 (18), Aug 19
  (39), and Aug 20 (35).
- Every row has a unique trade/order reference, so final-record deduplication does not remove
  the cascade.
- All rows are incorrectly labeled `is_execution_unwind=False`.

The frozen checkpoint report already identified the initial sequence's mechanism: losing
timeout MARKET exits did not trigger the STOP-only cooldown path. Git evidence shows the
broker reconciliation rule that activates cooldown for any non-profitable/unknown close was
added on 2026-08-22 (`ba3bdd6`), after the observed Aug 16–21 cascade. The trade collector also
now registers every negative realized PnL with `SymbolCooldownGate`, and XMR is permanently
blacklisted by current configuration.

Therefore the loss concentration is classified as **confirmed execution/risk-control
contamination caused by uncovered negative MARKET exits and rapid re-entry**, not as 142
independent observations of normal strategy edge.

## Failure Decomposition A–J

### A. Entry quality — UNKNOWN / mixed

The contaminated aggregate cannot identify unconditional entry quality. After removing XMR
descriptively, VWAPReversal is +21.0837 VST across 86 trades, while SweepScalper and
TrendFollow remain negative. Regime and excursion fields are absent, so no entry condition is
promoted.

### B. Direction quality — both aggregate sides fail

BUY expectancy is -0.7376 and SELL expectancy is -0.3082 VST/trade in the full cohort. BUY
contains 132 XMR cascade records, so the asymmetry is substantially contaminated. Direction
quality is not isolated causally.

### C. Symbol selection — DOMINANT

XMR contributes -261.7112 VST against total -256.8029 VST. This concentration is causal
evidence for an incident/control failure, not a license to hardcode profitable symbols from
the same sample. Current blacklist enforcement is the correct safety containment.

### D. Market regime — UNMEASURABLE

All 418 prospective rows have blank regime. Any regime claim from this journal would be
invented. Candidate research must reconstruct point-in-time regimes with closed/shifted bars.

### E. Timing — DOMINANT WITHIN INCIDENT

123 sub-hour re-entries after prior XMR closes violated the intended loss-spacing behavior;
116 were under five minutes. Timing amplified one adverse symbol episode into 142 trades.

### F. Exit management — MARKET label is contaminated, not proven harmful

Full-cohort MARKET exits are -260.5934 VST, but 142 of 152 are XMR. The ten non-XMR MARKET
exits are +1.1178 VST cost-adjusted with PF 1.729. Consequently, the MARKET order type alone
is not the economic root cause. The missing source label (timeout/risk/manual/etc.) remains a
telemetry deficiency.

### G. Fees/slippage/funding — secondary / incomplete

Recorded fees are -7.8472 VST versus -248.9557 recorded PnL and do not explain the failure.
Slippage and funding are not captured reliably enough for separate attribution; this blocks a
final friction claim for any narrow candidate.

### H. Position sizing — AMPLIFIER, not root signal

Every XMR trade uses quantity 0.177 and about 74 VST notional. The 25–100 VST bucket loses
-259.4221 VST, whereas the <=25 VST bucket is +2.6191 VST. Since XMR dominates the larger
bucket, this is sizing concentration coupled to repeated entry, not proof that smaller size
creates expectancy.

### I. Execution defects — DOMINANT

Negative MARKET closes were not reliably converted into cooldown events during the incident;
the current collector/reconciliation code covers this case only after the incident window.
The unwind attribution flag also fails to identify the event. These are verified execution
and telemetry defects.

### J. Risk controls — DOMINANT HISTORICALLY, contained in current code

The intended cooldown/circuit breaker did not stop the cascade. Current controls now apply
loss cooldown by realized PnL and permanently blacklist XMR. Runtime evidence after loading
the latest branch is still required; code presence alone is not deployment proof.

## Three Required Views

| View | N | Cost-adjusted PnL | Expectancy | PF | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| All prospective trades | 418 | -256.8029 | -0.6144 | 0.2071 | Current aggregate edge rejected |
| Excluding confirmed XMR cascade | 276 | +4.9082 | +0.0178 | 1.0790 | Descriptive residual only |
| Excluding all XMR | 276 | +4.9082 | +0.0178 | 1.0790 | Same here because all prospective XMR rows match the cascade pattern |

The equality of the last two views is specific to this prospective window. It must not be
generalized to historical XMR trades or used as a permanent universe optimization result.

## Residual Strategy View After Incident Removal

| Strategy | N | Cost-adjusted PnL | Expectancy | PF | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| VWAPReversal | 86 | +21.0837 | +0.2452 | 2.9910 | Research candidate only |
| OIFootprint | 13 | +2.5375 | +0.1952 | 2.3236 | Insufficient N |
| MeanReversion | 21 | +1.9667 | +0.0937 | 1.4177 | Insufficient N |
| trend_following | 3 | -0.3487 | -0.1162 | 0.0000 | Reject in this slice |
| MTFTrend | 51 | -4.7846 | -0.0938 | 0.6734 | Reject in this slice |
| TrendFollow | 39 | -5.6355 | -0.1445 | 0.4724 | Reject in this slice |
| SweepScalper | 63 | -9.9107 | -0.1573 | 0.4853 | Reject in this slice |

VWAPReversal is the only adequately sampled positive residual cell, but it was identified
after observing this cohort, has no regime breakdown, and may be unstable across symbols and
time. It may seed a new pre-registered hypothesis; it is not eligible for production or shadow
promotion from these numbers.

## Next Controlled Step

Resume isolated hypothesis-first research. Evaluate a newly versioned, pre-registered
VWAPReversal candidate alongside the existing C-01/C-02/C-03 register using chronological
OOS folds, point-in-time regime reconstruction, realistic costs, symbol stability, and no XMR
incident rows. Do not modify live strategy logic while researching.
