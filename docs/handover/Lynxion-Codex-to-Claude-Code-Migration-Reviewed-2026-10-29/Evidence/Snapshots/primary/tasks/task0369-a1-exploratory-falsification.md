# TASK-0369 — A1 exploratory aggressive-flow falsification

## خلاصه ساده فارسی

اولین آزمون واقعی مأموریت جدید اجرا شد. MeanReversion پانزده‌دقیقه‌ای به‌تنهایی بعد از هزینه حدود
۰٫۲۹۲٪ در هر معامله منفی بود. شرط aggressive flow آن را فقط حدود ۰٫۰۰۳۹٪ بهتر کرد، اما نتیجه
نهایی همچنان حدود ۰٫۲۸۸٪ منفی ماند. هر چهار بازه زمانی، هر شش نماد و هر دو جهت منفی بودند؛ صدک‌های
۷۰ و ۸۰ هم کمکی نکردند. بنابراین این ایده در همین شکل سریع رد شد و برایش candidate یا زیرساخت
جدیدی نمی‌سازیم.

## Scope

Execute the TASK-0368 bounded exploratory comparison once using existing data. This is exploratory
falsification, not confirmatory evidence or a production-policy decision.

## Results

- Baseline: N=46,537, 1,301 UTC-day clusters, net expectancy -0.292016%, PF 0.4259.
- Primary p75 flow condition: N=16,585, 1,266 clusters, net expectancy -0.288098%, PF 0.3718.
- Incremental expectancy versus baseline: +0.003919 percentage points, economically immaterial.
- Stress 0.50% expectancy: -0.488098%.
- Clustered bootstrap 95% interval: [-0.306001%, -0.269605%], wholly below zero.
- All four chronological folds, all six symbols, LONG, and SHORT are negative.
- p70 expectancy is -0.288555%; p80 is -0.286972%; the negative result is not rescued by the frozen
  perturbation diagnostics.
- Positive-PnL symbol concentration is 27.58%, so concentration passes, but every economic and
  stability gate fails except a tiny improvement over the already-negative baseline.

## Verdict

`REJECT — AGGRESSIVE FLOW DOES NOT RESCUE THIS 15M MEAN-REVERSION SPECIFICATION`.

Do not preregister, productionize, retune, or build new flow infrastructure for this specification.
The result reinforces prior Phase-17 evidence that this flow representation is weak and largely
redundant with price movement.

## Verification

- Focused tests: 2 passed.
- Machine report: `docs/reports/a1_mean_reversion_flow_exploratory.json`.
