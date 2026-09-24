# Canonical replay — Unit 1 result

Starting HEAD `87affd4`. This unit added a network-free, strict closed-bar input primitive and focused tests. It did **not** connect that primitive to Watcher → Engine → Fusion → Aggregator → StrategyManager or to the authoritative risk/guard/order route. Calling it a canonical replay would be false. No market outcomes, PnL or historical strategy verdicts were opened.

The main blockers are source-grounded: the live aggregator triggers/evaluates in a thread using `datetime.now()` (`infrastructure/aggregators/signal_aggregator.py`); `SignalEvent` defaults to wall-clock timestamps; `HistoricalCandleWatcherAdapter` creates observations with `datetime.now()` even if its input candle is historical; watcher discovery/selection can require live data not present in a candle archive; and the current event processor/aggregator use module-level router/singletons. Merely feeding rows to the old backtest or to a new mock `FusedSignal` would violate G1/G8. Production code was left unchanged because a safe event-time and per-run state boundary was not established.

Gates: G1 NOT MET; G2 PASS for the new primitive only, NOT TESTED end-to-end; G3 PASS for the primitive only; G4 PASS for the primitive (no fill); G5 PASS for source iteration only; G6 PASS for source prefix only; G7 PASS for the primitive only; G8 NOT TESTABLE; G9 NOT TESTABLE; G10 PASS as a documented limitation, not replay coverage. No foundation verification or canonical baseline use is authorized.

خلاصهٔ فارسی: ورودی کندلِ بسته‌شده را طوری ساختیم که زمان آینده، کندل تکراری و شکاف داده را نپذیرد. اما مسیر تصمیم زنده هنوز به زمان واقعی و watcherهای غیرقابل‌بازسازی وابسته است؛ بنابراین هنوز نمی‌توان بک‌تست را معادل اجرای زنده دانست.
