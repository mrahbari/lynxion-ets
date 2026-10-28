# XMR case in architecture review — not a causal attribution

The [forensic case](XMR_INCIDENT_REGRESSION_CASE.md) separates the July 27 report from the August 3 journal rows. July reports rapid sequential re-entry and a disconnected StrategyManager/closure-feedback path. August journal records separate XMR SELL trades with distinct order/client IDs and intervening exits, but no stable `ExecutionIntent` ID or per-attempt route/claim trace. Neither dataset proves that Unit-3's newly identified shared Fusion/Risk state caused historical XMR re-entry. Later dual-route offline evidence establishes a **risk in a later source version**, not historical double exchange execution.

| Possible contributor | Status for historical incident | Architecture regression implication |
|---|---|---|
| Disconnected/shared StrategyManager and adapter feedback | CONSISTENT_WITH_INCIDENT | Fresh per-run manager must receive its own close feedback; live manager identity preserved. |
| Stale `current_positions` | INSUFFICIENT_EVIDENCE | Test canonical execution-side active position, not deprecated strategy-local position flag alone. |
| Shared/global Fusion state | INSUFFICIENT_EVIDENCE | Two contexts/two symbols must not cross-influence Fusion state. |
| Duplicate delivery of one ExecutionIntent | INSUFFICIENT_EVIDENCE | Same-ID sequential/concurrent delivery gives at most one pre-broker attempt. |
| Historical dual execution ownership | CONSISTENT_WITH_INCIDENT | Preserve Unit-2 one-owner invariant; no claim of historical exchange duplication. |
| Intent claim lifecycle | INSUFFICIENT_EVIDENCE | Run-local atomic claim; separate runs may use same fixture ID independently. |
| Cooldown feedback/state | CONSISTENT_WITH_INCIDENT | Loss close activates unchanged normalized-symbol cooldown at event time. |
| Active-position state | INSUFFICIENT_EVIDENCE | While broker/portfolio view says active, later same-symbol intents follow unchanged veto. |
| Reconciliation/close feedback | CONSISTENT_WITH_INCIDENT | Explicit simulated terminal event updates scoped position/cooldown state; no live journal. |

No specific row reaches `PROVEN_CAUSAL` on the available event-level lineage; none is `RULED_OUT` for the historical deployed process. This is intentionally narrower than the prior incident report's root-cause wording.

Future **generic** regression, only after risk/execution scope isolation: use XMRUSDT plus one unrelated symbol in an in-memory network-incapable composition. One naturally formed eligible intent delivered twice, including concurrently, must yield ≤1 authoritative pre-broker attempt. Mark its position active in the canonical simulated broker/portfolio view; then a new same-direction and conflicting same-symbol intent must receive exactly the existing position/cooldown decisions and zero sends when blocked. Close with a loss, advance event clock within and beyond existing cooldown duration, and verify unchanged normalized-symbol behavior. Compare normalized orders/rejections to live no-network fixture; hash live journals before/after. This is an invariant test, not replay of historical XMR market outcomes and not a strategy test.

Generic remediation could eventually make the XMR-specific blocker unnecessary, but current evidence does **not** prove redundancy. Do not remove or alter that blocker without separate authorization and runtime safety review.
