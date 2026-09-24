# Unit 2 — single in-process execution ownership

Source baseline: `1180371`. Scope: production execution ownership only; no strategy, Fusion, risk parameter, research definition, broker account, or runtime configuration change. No broker/VST/live order was placed.

## Root cause and change

`SignalProcessor.setup_signal_processing()` subscribed an immediate `EXECUTION_INTENT`-to-order handler, while `AutoDetectionOrchestrator` subscribed a second queue-to-order handler. `ArchitectureOrchestrator.__init__` and `start()` could register the direct handler twice. Unit 1 proved two pre-broker service calls for one intent in a network-incapable fixture.

The queued auto-detection path is now the **only event-subscribed execution owner**. `SignalProcessor` still handles market observations/interpreted/fused signals and heartbeat tracking, but no longer subscribes its direct order handler. Its setup is idempotent. The direct method remains callable only for isolated legacy/F01 characterization; it is not an event route. No third path was added.

The surviving queue path now calls the existing `shared.utils.sanitize_sltp_levels` utility, attaches sanitized SL/TP to the intent/order, checks finite/positive levels and distance, and applies the optional configured/environment `MAX_ORDER_NOTIONAL_AMOUNT` cap before constructing the order. A cap that would push quantity below the existing 0.001 floor rejects rather than increasing the capped order. These changes preserve the formerly direct-only controls without changing their configured numbers. Existing queue admission, cooldown, liquidity, sizing, leverage and broker service/guard remain in place. Shared `RiskEnforcement` retains final exposure, mandatory stop and side authority. Broker reconciliation and journal components were not edited.

`ExecutionIntent.intent_id` is an opaque UUID created once with the domain object. The queued execution owner atomically claims this ID before pre-broker work, independent of symbol duplicate-policy settings. Re-delivery and concurrent invocation of the same ID are suppressed for the lifetime of this process. This is a **process-local claim**, not a durable distributed/exchange exactly-once guarantee. An unknown broker result or restart still requires read-only order reconciliation before any retry; automatic resend is not authorized by this unit. The claim set is currently process-lifetime and unbounded; memory growth and durable restart recovery require separate review before runtime promotion.

## Evidence and limitations

- Network-incapable route tests cover LONG/SHORT normal, repeated event delivery, queue redelivery, concurrent method invocation, cooldown veto, optional notional cap and SL/TP sanitation, plus inverse-size order quantities and idempotent processor registration. The six original Unit-1 cases were rerun with post-remediation expectations.
- Focused F01, RiskEnforcement, LiveExecutionGuard, cooldown, heartbeat, portfolio-capacity and reconciliation tests were rerun: **90 passed**, 26 warnings. `git diff --check` passed.
- The inverse-sizing route fixture uses a controlled risk-engine spy returning 20/10 units; the original F01 tests exercise the real risk calculation on the direct characterization method. A full composed live-service guard/broker test and actual runtime subscriber inventory were **not** performed.
- The fixture's `PreBrokerSpy` has no broker/network/LiveExecutionGuard. Thus this proves event-route topology and source-level in-process claim behavior, not deployed runtime, exchange sends, fills, restart safety, or end-to-end risk/guard invocation in production.
- Existing `BrokerExecutionService` and `LiveExecutionGuard` tests validate their local gates, but cannot by themselves establish all integration semantics for the new route. A controlled runtime check is required before `RUNTIME_VERIFIED` or `LIVE/VST_VERIFIED` can be claimed.

## Status

`SOURCE_REMEDIATED`: yes, for registered in-process event ownership.

`TEST_VERIFIED`: yes, for the bounded no-network tests above.

`RUNTIME_VERIFIED`: no.

`LIVE/VST_VERIFIED`: no.

خلاصهٔ فارسی: مسیر مستقیم دیگر مشترکِ اجرای سفارش نیست و فقط مسیر صف مالک اجراست. کنترل‌های SL/TP و سقف مبلغ سفارش به مسیر باقی‌مانده منتقل شدند. تست‌های آفلاین موفق‌اند، اما این به معنی تأیید نسخهٔ در حال اجرا یا تضمین ثبت‌نشدن سفارش تکراری پس از قطع ارتباط/ری‌استارت نیست.
