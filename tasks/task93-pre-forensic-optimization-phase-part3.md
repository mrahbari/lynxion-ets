- Always you must cover the rules and requirements that written in ./tasks/task0-force-to-cover.md
This is the kind of message a hedge-fund reviewer or principal engineer would send back.


You can copy this **exactly**.

---

# Institutional Review Response — Pre-Forensic Phase Claim

Your statement that the *pre-forensic optimization phase is fully implemented* is acknowledged. However, at this stage this remains a **self-asserted compliance claim**, not a validated institutional readiness confirmation.

Before this phase can be considered complete, the following **mandatory verification and proof requirements** must be satisfied.

---

## 1. Traceability Proof

Provide at least **one full trade trace** with:

* Same `trace_id` present in:

  * WATCHER
  * ENGINE
  * FUSION
  * STRATEGY
  * BROKER
  * BROKER_CLOSE

And demonstrate that:

* No layer generates a new trace_id
* No layer drops the trace chain
* Ordering is temporally consistent

> Without this, full reconstruction is not proven.

---

## 2. Field-Level Completeness Validation

For each layer, provide a **real log sample** showing:

| Layer        | Mandatory Field Proof                     |
| ------------ | ----------------------------------------- |
| WATCHER      | historical_percentile, data_freshness_sec |
| ENGINE       | historical_engine_accuracy                |
| FUSION       | fusion_entropy, correlation_penalty       |
| STRATEGY     | suppression_applied                       |
| BROKER       | expected_slippage vs actual_slippage      |
| BROKER_CLOSE | MFE / MAE                                 |

If any field is missing in production logs, the phase is **not complete**.

---

## 3. Decision Accountability Test

Provide one losing trade and demonstrate:

* Which engine contributed most
* Which fusion weight dominated
* Which regime context was active
* Which strategy component reduced or increased risk
* Which broker factor degraded execution

> If loss attribution is narrative instead of computed, accountability is not achieved.

---

## 4. Duplicate Decision Root Cause Test

Show logs proving:

* Strategy suppression logic triggers before broker duplicate blocking
* Suppression reason is logged
* Confidence is degraded when suppression occurs

> Broker-side blocking alone does not qualify as decision control.

---

## 5. Fusion Statistical Readiness Check

Confirm with evidence:

* Fusion weights are logged numerically
* Correlation penalty is applied dynamically
* Diversity score changes across regimes
* Fusion entropy varies across stable vs unstable markets

> Otherwise fusion remains engineering-based, not statistical.

---

## 6. Performance Overhead Proof

Provide benchmark showing:

* Logging ON vs OFF latency difference
* CPU overhead
* Memory overhead

> Claims of “zero overhead” require numeric proof.

---

## 7. Failure Scenario Logging

Demonstrate logs for:

* Rejected order
* Partial fill
* Exchange timeout
* SL / TP simultaneous hit
* Strategy veto

> Forensic logging must include failures, not only successes.

---

## 8. ML Training Readiness Proof

Provide:

* Exportable dataset schema
* Column consistency across trades
* Handling of missing fields
* Normalization readiness

> Logging without ML-ready structure is not forensic grade.

---

## 9. Regime Accountability Proof

Demonstrate at least two trades where:

* Regime differs
* Strategy behavior changes
* Fusion weighting shifts

> Otherwise regime_context is decorative, not functional.

---

## 10. Reconstruction Test

Provide a script or process description that:

Reconstructs a trade **only from logs** and reproduces:

* Entry logic
* Risk size
* SL/TP
* Execution price
* Final PnL

If reconstruction cannot be automated, forensic readiness is not achieved.

---

# Institutional Verdict

At this moment, your implementation can be classified as:

> **Forensic-Structured Logging Candidate**

Not yet:

> **Forensic-Validated Logging System**

---

# Critical Truth

Logging architecture is not proven by feature presence.
It is proven by **audit survivability**.

---

# Required Status Change

Until the above proofs are delivered, the system must be formally classified as:

**Pre-Forensic Phase: IMPLEMENTED BUT NOT YET VALIDATED**

---

# Next Permission Gate

Only after these proofs are satisfied can the system be formally authorized to enter:

> Hedge Fund Forensic Optimization Phase

---

# Final Statement

This is not a rejection.
This is an institutional readiness gate.

You are close — but **closeness is irrelevant in professional trading systems**.

Only proof upgrades status.


