# XMRUSDT repeated-entry incident — forensic regression case

Scope: historical evidence and a future **generic** regression fixture only. No XMR-specific production rule, blacklist change, order, broker call, or replay run. Unit 3 ended at `UNIT3_REQUIRES_ARCHITECTURAL_REVIEW`; full isolated replay is not available, so the requested **post-isolation** regression test is deferred rather than simulated through production globals.

## Evidence separated by period

- The [July 27 SEV-1 report](../../incidents/SEV1_20260727_XMR_REENTRY_INCIDENT_README.md) lists seven sequential XMRUSDT LONG losses from 17:20–17:43 UTC and attributes missed cooldown to two different StrategyManager instances receiving decision versus reconciliation updates. This is a prior forensic conclusion; the current checkout does not contain a complete July intent/claim/broker-ID chain to independently re-prove its exact mechanism. Its quoted old singleton implementation is not the current `StrategyManager` class and must not be projected onto today's code.
- The current `data/trade_journal.csv` has August 3 XMRUSDT SELL rows at 08:02, 08:06, 08:11 and 08:15 UTC with distinct trade IDs, broker order IDs and client-order IDs, and exits recorded before the next entry. Matching `data/live_order_journal.json` INTENT rows have distinct order references/client-order IDs. These support repeated **separate recorded orders**, not two submissions from one logical `ExecutionIntent`. The journal does not carry the logical intent ID or a complete pre-broker route/claim trace.
- Later [cooldown audit](../../../tasks/epic-impls/task0052-p1.5-cooldown-enforcement-forensic-audit-report.md) reports broader cooldown violations, including XMR, and lists ephemeral cooldown state, symbol-format mismatch and missing reconciliation as mechanisms. [Task 0057](../../../tasks/epic-impls/task0057-p2-cooldown-remediation-report.md) documents subsequent market-order cooldown and active-position persistence fixes. These later retrospective claims are not independent event-level proof for the July route. Do not use their PnL counterfactuals as causal evidence here.
- Unit-1 later proved that its then-current offline wiring could give **two pre-broker service calls per one intent**. Unit-2 removed the direct execution subscription; Unit-3 verified one subscriber offline after `87affd4`. Neither test reconstructs the July/August deployed process or proves historical double exchange submission.

## Requested mechanism classification

| Mechanism | Classification for historical XMR incident | Reason |
|---|---|---|
| Shared StrategyManager/adapter state or disconnected instances | CONSISTENT_WITH_INCIDENT | July report identifies a disconnected reconciliation target; no surviving per-intent object identity/adapter-state snapshot independently links every entry. Current shared-state blocker is a separate, later finding. |
| Stale `current_positions` | INSUFFICIENT_EVIDENCE | Journal shows close-before-next-entry in sampled August sequence; no historical in-memory position snapshot or broker-vs-local comparison for each July decision. |
| Shared/global Fusion state | INSUFFICIENT_EVIDENCE | No per-event Fusion-state trace tied to these orders. Cannot claim it caused repeated entries. |
| Duplicate delivery of one ExecutionIntent | INSUFFICIENT_EVIDENCE | Historical journals have no logical intent ID/delivery count. August distinct order IDs do not establish whether a single intent or multiple intents generated them. |
| Historical dual execution ownership | CONSISTENT_WITH_INCIDENT | Later offline trace proved the risk existed in a later source state, but historical deployed registration and same-intent order linkage are unverified. Not a proven historical cause. |
| Intent claim lifecycle | INSUFFICIENT_EVIDENCE | Stable `intent_id`/atomic claim were added after the historical incidents; cannot infer prior claim state. |
| Cooldown state/feedback failure | CONSISTENT_WITH_INCIDENT | Re-entry intervals after recorded losses are shorter than the documented 60-minute rule; reports describe missed feedback/format/persistence pathways, but the exact per-entry cooldown state is absent. |
| Active-position state | INSUFFICIENT_EVIDENCE | Distinct sequential recorded August trades do not prove a concurrent active-position bypass; restart/reconciliation history is incomplete. |
| Reconciliation state/close feedback | CONSISTENT_WITH_INCIDENT | July report and later remediation identify missed closure feedback; no complete raw state timeline is available here. |

`PROVEN_CAUSAL` is not assigned to any of these *specific* mechanisms from the available event-level evidence. The repeated recorded entries and sub-hour intervals are observed facts; the causal path from signal to claim to broker remains incomplete. No candidate mechanism is `RULED_OUT` for the July process merely because a later test passed.

## Reconstructable lifecycle and missing links

For sampled August orders: `market signal UNKNOWN → strategy=trend_following in trade journal → ExecutionIntent ID UNKNOWN → route delivery/claim UNKNOWN → risk decision UNKNOWN → live-order journal INTENT with order_ref/client_order_id → distinct broker order IDs in trade journal → recorded close → next separately identified entry`. The source journals do not establish whether the broker position was active at each interim decision, when cooldown was set/cleared, or whether an execution attempt was duplicated before submission. The July lifecycle is still less complete: report-level entry/exit times exist, but the per-intent/order join is absent. Do not fill these gaps from current code.

## Deferred generic regression after isolation

Once Unit-3 architectural seams are reviewed and **per-run risk, claim, cooldown, position and persistence state is proven isolated**, use XMRUSDT only as one fixture symbol (repeat with another symbol). In a network-incapable context: publish one naturally formed eligible intent through the canonical queue twice, including concurrent delivery; assert at most one authoritative pre-broker attempt for its logical ID. Mark the symbol active in the replay-local position/broker spy, then publish a *new* conflicting and same-direction intent; assert the existing canonical active-position and cooldown decisions block or allow according to their unchanged policy, with zero broker dispatch for blocked cases. Close it with a loss and test replay-local 60-minute cooldown at fixed event time; verify symbol normalization. Compare two fresh contexts, assert no cross-run state, and hash production journals before/after. No forced live signal, exchange request, XMR-specific conditional or production blacklist edit.

Existing Unit-3 offline owner tests cover generic same-ID duplicate/concurrent and active-order cases, but not a full isolated lifecycle after position close/reconciliation. They do **not** make the XMR safety blocker provably redundant. Keep it unchanged unless separately authorized after stronger evidence.
