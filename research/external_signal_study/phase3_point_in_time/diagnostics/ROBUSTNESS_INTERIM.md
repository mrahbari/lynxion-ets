# Phase 3A fixed-split robustness — interim

Frozen preregistration: `b9ec946`. This uses only the already-opened six pre-T paired feature differences and does not inspect future returns or Telegram outcomes. It is descriptive robustness, **not** a new feature search and **not** a fingerprint verdict.

The [robustness table](./robustness_results.csv) applies one chronological split at the median UTC case day (11 early days, 12 late days), separate LONG/SHORT summaries, and one leave-top-symbol-out check. `ETHUSDT` was the most frequent matched case symbol (7/56), so it was removed without consulting feature results. No thresholds, symbols, or dates were chosen by observed performance.

F4 compression's case-minus-control difference retains the same sign in both chronological halves (26/30 cases), both sides (25 LONG/31 SHORT), and after removing ETH (49 cases; 1.16× the full-sample mean difference). This is a **descriptive clue only**. Its frozen primary screen failed BH q=.10 (q≈.163), its power at the practical d=.40 hurdle was under 80%, and placebos/M2 validity remain unresolved. It cannot be called a defensible fingerprint, much less a profitable edge. Other features' complete split results are in the CSV; F1 and F3 have directional instability across temporal halves or sides.

M3 same-week+same-weekday+same-four-hour-block controls are `NOT_IDENTIFIABLE` because all such timestamps fall within the frozen ±6-hour signal exclusion. M2 volatility-tercile matching lacks a frozen exact estimator/mapping and is not improvised after seeing the primary screen. A valid new boundary would be needed to test a newly specified M2/M3 design confirmatorily.

Next: run the frozen valid placebo shifts. If placebo behavior is comparable to F4, downgrade it further. Regardless, no non-significant result may be interpreted as no fingerprint because five of six primary dimensions are underpowered and one is marginal.

**خلاصهٔ ساده:** نشانهٔ خامِ «فشردگی» در چند برش داده هم‌جهت ماند، ولی هنوز از دروازهٔ آماریِ ازپیش‌تعیین‌شده رد شده است. آن را دستاورد سودآوری یا edge نمی‌نامیم؛ آزمون‌های ساختگیِ کنترل و محدودیت توان هنوز تعیین‌کننده‌اند.
