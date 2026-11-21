# TASK-0388 — Lead-B economic holdout verdict

## خلاصه ساده فارسی

سیگنال ربع‌ساعته از نظر آماری واقعی بود، اما برای معامله‌کردن به‌اندازه کافی بزرگ نیست. در ۴۸۰
معامله بازنشده، سود قبل از هزینه فقط حدود ۰٫۰۱۷۳٪ در هر معامله بود؛ هزینه واقع‌گرایانه ۰٫۳۰٪ آن
را به زیان متوسط ۰٫۲۸۲۷٪ تبدیل کرد. هر دو دوره زمانی، هر دو ساعت ورود و هر دو جهت منفی شدند.
بنابراین Lead B صریحاً رد شد و با تغییر threshold یا انتخاب بخش‌های برنده دوباره باز نمی‌شود.

## Frozen evaluation

- Holdout: `2026-01-01..2026-08-28`, never opened for Lead B before TASK-0387 was committed.
- Integrity: PASS; 240/240 UTC days and 480/480 trades eligible, with no exclusion or hash failure.
- Gross expectancy: `+0.018174%`; gross PF `1.0337`.
- Mean funding contribution: `-0.000895%`.
- Pre-cost expectancy: `+0.017280%`; pre-cost PF `1.0320`.
- Primary 0.30% cost expectancy: `-0.282720%`; PF `0.6007`; win rate `39.17%`.
- Day-block 95% interval: `[-0.447346%, -0.123399%]`, wholly below zero.
- Stress 0.50% cost expectancy: `-0.482720%`; PF `0.4224`.
- Unlevered sequential max drawdown: `-77.99%`.
- Both chronological folds are negative.
- Both `00:00` and `12:00` UTC clock phases are negative.
- Both LONG and SHORT sides are negative; gross-profit side concentration passes at `51.35%`.
- Seven of eight frozen economic gates fail. Only the side-concentration gate passes.

## Verdict

`REJECT_ECONOMIC_EDGE`

The statistical association does not clear the executable cost hurdle. Leverage cannot repair
negative expectancy. Do not reopen this lead through imbalance thresholds, phase selection, horizon
selection, side removal, or lower post-hoc costs on the opened holdout.

## Engineering and validation

- One disposable evaluator and one focused helper-test file were added.
- Three preregistration/helper tests pass.
- The full report is reproducible from frozen raw hashes and actual point-in-time funding.
- No production strategy, broker call, order, account, runtime, risk setting, or external data was
  changed.

## Next

Return to the ranked lead tournament. Lead A remains blocked by provenance. Select the next
highest-information lead that uses existing point-in-time data and is economically distinct; do not
retune Lead B or expand infrastructure merely to keep it alive.
