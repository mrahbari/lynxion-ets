# TASK-0393 — Funding Settlement market-quality verdict

## خلاصه ساده فارسی

زمان funding واقعاً با افزایش فعالیت بازار همراه است: حجم و تعداد معامله در همه سال‌ها و هر شش
نماد بیشتر شدند. اما تغییر خطرناک و بزرگی که بتواند یک قانون NO_TRADE را توجیه کند پیدا نشد؛
نوسان فقط حدود ۳٫۳٪ بیشتر شد، عدم‌تعادل جریان کمتر شد و عمق بازار کمی بهتر شد. بنابراین این مسیر
`LOW_INFORMATION_VALUE — DO_NOT_BUILD` است و Rescue Ladder بدون تغییر باقی می‌ماند.

## Frozen results

- Integrity: PASS.
- Eligible symbol-settlement records: 24,048 of 24,054 candidates (`99.975%`).
- Independent settlement-time clusters: 4,008.
- All six symbols and all four chronological folds are represented.
- Log quote-volume paired effect: `+0.07093`, CI `[+0.05036, +0.09173]`, same sign in 4/4 folds and
  6/6 symbols.
- Log trade-count paired effect: `+0.07241`, CI `[+0.05596, +0.08919]`, same sign in 4/4 folds and
  6/6 symbols.
- Absolute-return effect: positive, CI above zero, 3/4 folds and 6/6 symbols, but only `+3.33%`
  relative to settlement pre-state and negative in the 2026 fold.
- Absolute taker imbalance decreases `3.75%`; it does not show the preregistered adverse increase.
- ±1% depth increases `2.87%`; it does not show the preregistered adverse decrease.
- All three adverse/non-trivial execution-risk gates fail.

## Verdict

`LOW_INFORMATION_VALUE — DO_NOT_BUILD`

Settlement timing changes activity, but current evidence does not justify a new collector,
production `NO_TRADE` rule, or an unopened economic candidate. Do not retune the 10% materiality
threshold or select only older folds after seeing the 2026 reversal.

## Validation

- One disposable evaluator and one focused helper-test file.
- Two focused tests pass, including strict point-in-time depth selection.
- No broker call, runtime mutation, new download, production policy change, or Rescue Ladder change.

## Next

Place this result beside the fixed Rescue Ladder snapshot as negative evidence. Return to the
bounded decision board rather than expanding funding-clock infrastructure.
