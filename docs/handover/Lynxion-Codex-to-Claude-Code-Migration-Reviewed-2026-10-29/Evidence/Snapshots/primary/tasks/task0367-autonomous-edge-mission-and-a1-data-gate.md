# TASK-0367 — Autonomous edge mission and A1 data gate

## خلاصه ساده فارسی

مأموریت جدید کشف edge ثبت و board پنج‌خانواده‌ای ساخته شد. اولین سؤال انتخاب‌شده مقایسه
MeanReversion پانزده‌دقیقه‌ای با همان رویدادها پس از شرط aggressive flow است. داده لازم از قبل
برای شش نماد و بیش از ۱۲۸ هزار کندل هر نماد وجود دارد؛ پس بدون دانلود، سرویس یا زیرساخت جدید می‌توان
آزمون کم‌هزینه را شروع کرد. شواهد قبلی flow ضعیف و تا حد زیادی تکراری بوده، بنابراین هدف اول کشتن
سریع فرضیه در صورت نداشتن ارزش افزوده است.

## Scope

Adopt the operator-supplied autonomous edge-discovery rules, create the bounded persistent decision
board, and verify whether the first A1 feasibility question can use existing point-in-time data.

## Evidence

- Six normalized 15-minute futures files exist for ADA, BNB, BTC, ETH, SOL, and XRP.
- Each contains 128,352 unique rows from 2023-01-01 through 2026-08-29.
- The frozen manifest reports zero missing intervals, schema, timestamp, numeric, OHLC, and flow
  violations for every symbol.
- Each row contains quote volume, trade count, and taker-buy quote volume, sufficient to construct a
  causal completed-bar aggressive-flow state without raw L2 or aggTrades infrastructure.
- Phase-17 found flow/recent-return correlation about 0.58 and weaker reversal IC for flow than
  recent return, making incremental value the decisive falsification question.

## Engineering budget

- Expected implementation: one disposable research script, one machine-readable report, focused
  tests, and one preregistration only if exploratory feasibility survives.
- No new persistent market dataset, service, watcher, broker path, runtime, or production code.

## Verdict

`DATA_READY — START MINIMAL EXPLORATORY INCREMENTAL-VALUE TEST`.
