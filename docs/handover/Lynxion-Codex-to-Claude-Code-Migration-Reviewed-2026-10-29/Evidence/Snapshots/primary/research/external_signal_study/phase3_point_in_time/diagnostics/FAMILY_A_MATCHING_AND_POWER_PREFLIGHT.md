# Phase 3A Family-A matching and preliminary power preflight

**Status:** CONTROL_MATCHING_COMPLETE; FINGERPRINT_NOT_TESTED. Frozen protocol SHA-256: `96d0f336f9c0e335b61b8d90df81835180647f9c2d85498d210fa1e34c329193` (commit `b9ec946`). Public proxy source manifest: `manifests/phase3_proxy_source_manifest.json` (commit `5bc424c`).

The deterministic timestamp-only matcher `src/build_family_a_controls.py` applied the frozen primary Family-A rules: same symbol, copied side and execution timeframe, same ISO week and UTC four-hour block, valid pre-T 168-bar symbol/BTC lookback, any 1K_EVENT same-symbol signal excluded within ±6 hours, and up to three controls on distinct UTC dates chosen by the frozen SHA-256 ordering. No price/volume values, Telegram outcomes, post-signal returns, or economic results were read for matching.

| Quantity | Result |
| --- | ---: |
| Nominal primary interval-HMT cases | 58 |
| Cases with verified proxy and complete timestamp lookback | **56** |
| Cases with >=2 Family-A controls | **56** |
| Selected controls | **168** (3 per matched case) |
| Distinct matched-case UTC days | **23** |
| Distinct matched-case symbols | **22** |
| Matched-case sides | 25 LONG / 31 SHORT |
| Source-unverified cases | 2 (`ALUSDT`, `XAUUSD`) |
| Case/control availability audit records | **224**, all `max_input_close_time <= T` |

[Matched controls](../controls/matched_controls.csv) retain their deterministic hash, case ID, copied side/timeframe, control UTC date, source-file hash, and maximum permissible input close time. [Control diagnostics](../controls/control_diagnostics.csv) include all 58 cases, including the two unavailable cases rather than silently dropping them. [Leakage audit](./leakage_audit.csv) covers all 56 matched cases and all 168 controls. A focused boundary regression confirmed that a bar with open timestamp T is not used until its `open+899` close time; all recorded case/control input-close timestamps are <= their own event time.

**PRELIMINARY power/identifiability:** Raw control count is not independent N; the paired case count is 56 and there are only 23 UTC-day clusters. Breadth minima in the frozen protocol are met *before feature missingness*: >=40 matched cases, >=20 days, >=10 symbols, >=10 per side. This does **not** establish >=80% power. For orientation only, if all 56 paired case differences were independent with unit variance, a two-sided alpha=.05 test of d=.40 would have about 85% power. If effective independence were only 23 days, the same optimistic normal approximation is about 48% power, before within-day correlation, matching covariance, six-test FDR, temporal splits, and missing features. These are **not** formal power estimates and must not become a null-result gate. The planned clustered simulation/CI-width analysis must be performed on the frozen pre-T features before any `NO_DEFENSIBLE_FINGERPRINT` verdict is possible.

Remaining limitations: the true sibling opportunity universe and source instrument are unknown; Binance perpetual is an explicitly declared proxy. Current `exchangeInfo` does not independently prove every historical listing state, although the validated historical bar grid supports data availability for the 22 mapped symbols. The signal-exclusion list uses V2 extracted symbols except the raw-verified LDO correction already frozen in the derived case table; any additional extraction defect would require an append-only provenance amendment, not silent control changes. Family-B cross-symbol controls and M2/M3 sensitivity matching are not yet executed. No feature difference, q-value, placebo, economic result, or edge has been computed.

**خلاصهٔ ساده:** برای ۵۶ مورد، سه زمانِ مقایسه‌ایِ مستقل از روزهای دیگر پیدا شد و هیچ داده‌ای با زمان بسته‌شدن بعد از لحظهٔ بررسی وارد ورودی‌ها نشده است. با این حال ۵۶ معامله به معنی ۲۲۴ شاهد مستقل نیست؛ داده‌ها فقط ۲۳ روز را پوشش می‌دهند و توان آماری هنوز معلوم نیست. هنوز هیچ نتیجه‌ای دربارهٔ اثر یا سود نداریم.
