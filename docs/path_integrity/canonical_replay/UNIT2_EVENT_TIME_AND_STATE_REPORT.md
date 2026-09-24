# Unit 2 — event time and state boundary

Starting commit `3da13d5`. Scope: minimum time/state seams in the existing event and aggregation path. No replay driver, synthetic watcher, broker, profitability run or production configuration change.

## Changes and semantics

`LiveClock` retains `datetime.now()` for the existing live aggregator default. `ReplayClock` advances monotonically in UTC under a caller-controlled event time. `SignalAggregator` now accepts an injected clock/router/strategy selector and a synchronous scheduling option. Its `_rank_signals`, `_select_best_signals`, and `_generate_execution_intent` operations are **the same methods** in both modes. Live default still uses the existing thread scheduler and global router/manager; isolated tests use a fresh router, clock and selector, invoking aggregation after releasing the collection lock. No Fusion, strategy, risk or numeric policy was changed.

The event router's typed publish helpers now carry each domain object's timestamp into `SignalEvent`; direct construction retains its live wall-clock fallback. `HistoricalCandleWatcherAdapter` uses the candle's `close_time` when supplied (otherwise its previous timestamp/now fallback) and stamps its observation with that stored candle time. This corrects historical timestamp semantics without changing pattern logic. A future canonical replay must require explicit completed-bar time at its adapter boundary; this unit does not yet wire Unit-1 bars into watchers.

Two fresh routers and aggregators did not share candidates or duplicate subscriptions in the focused test. The replay clock and source have no broker/persistence dependency. **This is not full per-run application isolation**: `SignalProcessor._process_observation` reads the global container risk engine and forensic logger; Fusion uses a shared hierarchical singleton; default StrategyManager/adapters may carry state; auto-detection claim/cooldown/position and journals remain global or persistent. These were not reset or touched, so full G4/G5 remain open. In particular, constructing a full replay with present globals could read/write production state; it is not authorized.

Other decision-relevant wall-clock reads remain in multi-signal Fusion timestamps, auto-detection cooldown/execution, and strategy/adapter behavior requiring further bounded trace. No full decision trace exists. Historical watcher coverage remains as in Unit 1; missing order flow, tick and screener archives were not proxied. No authenticated exchange request or production-state mutation occurred in tests.

Gate result: U2-G1 PARTIAL (typed event and candle-watcher time); U2-G2 PARTIAL; U2-G3 PASS for aggregator entry; U2-G4 PARTIAL; U2-G5 PASS for tested isolated slice only, NOT ESTABLISHED end-to-end; U2-G6 focused regressions PASS; U2-G7 PASS for focused tests. Full Unit-2 verification is not claimed.

خلاصهٔ فارسی: زمان کندل تاریخی دیگر در watcher به ساعت فعلی تبدیل نمی‌شود و انتخاب aggregator را می‌توان با زمان مشخص، بدون رقابت thread، تکرار کرد. اما وضعیت سراسریِ Fusion/Strategy/Risk هنوز از اجرای تاریخی جدا نشده؛ پس replay کامل و قابل‌اتکا هنوز آماده نیست.
