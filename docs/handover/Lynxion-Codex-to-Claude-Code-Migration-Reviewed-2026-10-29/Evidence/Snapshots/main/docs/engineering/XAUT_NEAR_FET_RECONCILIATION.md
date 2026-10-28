# XAUT / NEAR / FET broker reconciliation — final offline disposition

Scope: existing evidence only; no new authenticated request, order action, runner restart, or deployment. This closes the **false current-open-position incident**, not the historical fill/exit investigation. All times below are UTC unless noted.

## Snapshot provenance and limit

**FACT:** the prior operator-approved, allowlisted GET-only BingX VST audit (`scripts/audit_bingx_vst_gate_a.py`) returned zero nonzero positions and zero open orders. The result was recorded in commit `46b98e1` at 2026-10-13 08:50:29 UTC. The corrected historical-query result was recorded in `c9161a0` at 08:53:20 UTC. The audit deliberately printed only counts/status, not raw broker payloads, order identities, fill rows, or a query-time UTC timestamp. Thus the **exact observation timestamp is UNKNOWN**; commit time is an upper bound on documentation, not a fabricated broker timestamp. The operator independently reports no current open positions (OPERATOR_TESTIMONY), but this does not extend the old snapshot's authority to every later moment.

**FACT:** the old audit returned 31 XAUT, 23 NEAR, and 19 FET historical `allOrders` rows. Its summary recorded at least one `FILLED` reduce-only `STOP_MARKET` row for XAUT and NEAR, but not identifying IDs, quantities, fill prices, or event-to-alert joins. No trade/fill-history export is preserved in this worktree. The FET pending local client ID did not match those 19 rows; direct client-ID lookup returned `109421`. This is not proof of never-submitted, rejected, or filled. The earlier `100001` responses were caused by the audit script's signed/sent parameter-order mismatch; they are not broker-state evidence.

The original local files in the main checkout are preserved. `data/active_positions_journal.json` currently lists AAVE, SOL, XLM and XRP, not these three. The append-only `data/live_order_journal.json` contains historical INTENT records, including later XAUT/NEAR attempts and FET attempts through 2026-10-10 11:35:04; an INTENT is neither current broker exposure nor proof of submission. `logs/execution_truth_ledger.jsonl` contains route/results for some attempts, but is not a broker fill ledger. The latest FET local INTENT and its historical unknown outcome remain auditable; no journal line is deleted or rewritten.

## Per-symbol disposition

| Symbol | current_broker_position_state | current_broker_open_order_state | historical_order_outcome | historical_exit_attribution | evidence_quality | observation_timestamp | reconciliation_status |
|---|---|---|---|---|---|---|---|
| XAUTUSDT | `CURRENT_BROKER_FLAT_AT_OBSERVED_SNAPSHOT` | zero at same snapshot | Filled reduce-only STOP_MARKET row(s) in summary; exact target order unknown | `HISTORICAL_EXIT_ATTRIBUTION_UNVERIFIED` | Broker count/status summary plus local journals; no preserved fill identity/quantity/price join | Exact query UTC unknown; documented by 2026-10-13 08:50:29 UTC | `CURRENT_OPEN_POSITION_INCIDENT_CLOSED; HISTORICAL_RECONCILIATION_INCOMPLETE` |
| NEARUSDT | `CURRENT_BROKER_FLAT_AT_OBSERVED_SNAPSHOT` | zero at same snapshot | Filled reduce-only STOP_MARKET row(s) in summary; exact target order unknown | `HISTORICAL_EXIT_ATTRIBUTION_UNVERIFIED` | Broker count/status summary plus local journals; no preserved fill identity/quantity/price join | Exact query UTC unknown; documented by 2026-10-13 08:50:29 UTC | `CURRENT_OPEN_POSITION_INCIDENT_CLOSED; HISTORICAL_RECONCILIATION_INCOMPLETE` |
| FETUSDT | `CURRENT_BROKER_FLAT_AT_OBSERVED_SNAPSHOT` | zero at same snapshot | `HISTORICAL_SUBMISSION_OUTCOME_UNKNOWN`; no matching client ID in bounded 19-row summary, lookup `109421` | Not established; no exit may be inferred | Broker count/status summary and local INTENT; no affirmative matching order/fill | Exact query UTC unknown; documented by 2026-10-13 08:50:29 UTC | `CURRENT_OPEN_POSITION_INCIDENT_CLOSED; HISTORICAL_RECONCILIATION_INCOMPLETE` |

No exact XAUT/NEAR order-ID/client-ID/position-side/time/filled-quantity/price match can be performed because the prior audit intentionally discarded those fields. Presence of filled stops alone does not identify *which* local lifecycle or alert they closed. No realized PnL, exact stop execution price, or exit reason is inferred. FET is **not** relabeled rejected/canceled/never sent. `HISTORICAL_RECONCILIATION_COMPLETE` is not warranted for any symbol.

## Operational and safety decision

Close the historical **active-open-position alert** for all three at the verified snapshot. Keep separate UNKNOWN historical identity/submission audit flags and all existing unknown-exit cooldown/unknown-submission gates. Flat at one snapshot is not permission to clear cooldowns, retry FET, or loosen trading eligibility. No production-code state correction is justified: the local active-symbol file does not mark these three active, and changing the append-only INTENT ledger would falsify history. The read model/reporting layer should show a snapshot-qualified flat state separately from unresolved historical attribution; this document supplies that disposition without deployment.

## Acceptance-case audit (offline; no production test claim)

| Case | Safe expected classification | Current verification |
|---|---|---|
| Broker flat / local OPEN | Snapshot-qualified flat; retain historical local OPEN | Decision rule recorded; production regression NOT RUN |
| Broker flat / local INTENT | Snapshot-qualified flat; historical submission UNKNOWN | FET evidence matches this case; production regression NOT RUN |
| Missing historical exit join | Attribution UNVERIFIED, PnL unknown | XAUT/NEAR evidence matches |
| Filled stop with exact matching identity | Verified historical exit, never inferred PnL without fills | No identity-bearing evidence; NOT TESTED |
| Filled stop without identity join | Attribution UNVERIFIED | XAUT/NEAR evidence matches |
| Unknown submission retry | No blind retry | No retry performed; production regression NOT RUN |
| Immutable history | Do not edit original journal/broker evidence | No original file modified |
| Repeated reconciliation | Same classification for same snapshot/evidence | Pure disposition is idempotent; production regression NOT RUN |

Execution-sensitive tests and production reconciliation edits remain blocked by the P0 Phase-0 credential/network/client-construction isolation gate and unavailable test dependencies. This is a documented partial acceptance, not a claimed passing eight-case suite. A later operator-authorized identity-bearing **existing export** could settle history, but no new broker query is authorized here. Do not turn the residual forensic uncertainty into a false current-open-trade alert.
