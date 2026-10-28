# Lynxion New Edge Lead Tournament

**Adopted:** 2026-09-17
**Decision purpose:** select one high-information diagnostic without reopening rejected candidates
or expanding the research platform.

## خلاصه ساده فارسی

هشت سرنخ جدید با واقعیت داده‌های Lynxion مقایسه شدند. فقط تحلیل «پس‌دادن سود بعد از MFE» برای
diagnostic اولیه فعال می‌شود، چون هم در ۵۰ معامله اخیر BingX علامت توصیفی دارد و هم با داده‌های
موجود قابل بررسی است. اثر ربع‌ساعت رتبه دوم است، اما داده ۱۵‌دقیقه‌ای فعلی برای ادعای پنجره
۱۰ثانیه‌ای کافی نیست. بقیه ایده‌ها حذف نشده‌اند؛ برای جلوگیری از پراکندگی PARK هستند. این تصمیم
هیچ exit یا strategy production را تغییر نمی‌دهد و هنوز edge اثبات‌شده نداریم.

## Capacity and non-contamination boundary

- Frozen background work: C-11, C-33, and C-35 continue unchanged and do not donate opened outcomes
  to redesign their own rules.
- The previous five-family cycle is closed. Four families are rejected/deprioritized and C-11 is
  the only surviving directional hypothesis.
- New-lead budget: one active `MINIMAL_DIAGNOSTIC`; a second lead may advance only after an
  independent data-readiness finding and without shared outcome inspection.
- Historical and recent BingX trades may generate an exit-state hypothesis, but cannot confirm it.
- Every surviving rule requires a new unopened validation boundary before an economic claim.

## Tournament decision table

Qualitative ratings are deliberately not summed into a false-precision score.

| Lead | Mechanism / external evidence | Novelty and overlap | Existing point-in-time data | Missing data | Fastest valid falsification | Engineering / calendar | Economic hurdle and contamination | Decision |
|---|---|---|---|---|---|---|---|---|
| A — edge retention / profit giveback | Remaining holding value may become negative after a detectable change in flow, common factor, volatility, or execution state. Operator observation plus the 50-trade BingX audit show material descriptive giveback; literature support is indirect. | Distinct from entry-edge discovery. Prior lifecycle work measured MFE counterfactuals but did not establish an ex-ante exit state. | 1,913 normalized trade-journal rows; entry/exit fields; recent 50-trade audit; public candle paths; six-symbol 15m flow/OI/depth panels through 2026-08-29. | Authoritative manager ticks, exact mark-price path, exchange stop lifecycle, and aligned state for many non-six-symbol trades. | Reconstruct only provenance-valid paths; test whether giveback is broad and whether any state is observable before it. Reject if concentration/noise dominates or remaining value is below extra exit cost. | 1 disposable script + report + test, about 150–250 LOC; first descriptive answer in hours, clean prospective answer later. | Extra turnover, spread, slippage, false early exits. High historical contamination, controlled by descriptive-only label and unopened confirmation. | **ACTIVATE — MINIMAL_DIAGNOSTIC** |
| B — quarter-hour clock-phase order flow | External six-Binance-perpetual study reports abnormal first-seconds flow and 4–12h predictability. Mechanism is synchronized algorithmic activity. | New clock-phase representation; must not recycle failed 15m mean-reversion/flow thresholds. | Raw BTC Binance aggTrade daily archive exists; normalized flow is only 15m. Six-symbol flow cannot resolve first 10 seconds. | Exact raw coverage/integrity inventory; relevant BingX trade-level data; spread at seconds scale. | First verify raw timestamps and compare first 10 seconds with matched non-boundary clock phases; no PnL test yet. | 1 temporary BTC-only diagnostic, about 100–180 LOC; hours if raw coverage is sound. | 4–12h forecast must exceed costs and survive clock controls. Transferability from Binance BTC to BingX/other symbols is high risk. | **MINIMAL_DIAGNOSTIC NEXT — DATA READINESS FIRST** |
| C — dynamic cross-venue price discovery | Time-varying venue leadership may cause lagged adjustment on an executable venue. Empirical price-discovery literature supports the mechanism. | Genuinely different information boundary; not the old cross-sectional strategy family. | Separate venue adapters and some venue data exist, but no verified synchronized multi-venue trade/mid panel. | Exchange timestamps, receive timestamps, common contract/price-series semantics, spread and latency. | Reject immediately if timestamp error is not materially smaller than the proposed lag or net adjustment is below costs. | Likely collector/alignment work across venues; days to weeks. | Very high fee/latency hurdle and false-arbitrage risk. | **PARK** |
| D — order flow × execution state | Flow may be informative only when spread/liquidity make it capturable. Academic evidence supports flow information conditionally. | Strong overlap with rejected C-21/C-22/C-27/C-34, Phase 17, and TASK-0369; only a truly new execution-state field would make it distinct. | Six-symbol 15m taker flow and five-minute depth snapshots exist. Existing representation already failed incremental tests. | Reliable point-in-time spread/top-of-book and a genuinely new execution state. | Require new information before testing; do not retune old flow thresholds. | Low analysis cost but currently high contamination risk. | Existing flow results fail costs; easy to manufacture post-hoc filters. | **REJECT CURRENT REPRESENTATION / PARK NEW DATA** |
| E — cascade continuation vs exhaustion | Marginal price response to extreme forced flow may distinguish continuation from absorption. | Mechanistically sharper than liquidation direction, but overlaps C-16/C-17 and frozen C-33. | C-33 public liquidation buckets; six-symbol flow/OI panels do not overlap C-33 historically. | Aligned prospective OI/flow/liquidation/price response with adequate effective events. | Treat as explanatory analysis only; reject a new candidate if it redefines opened C-33 outcomes. | Slow forward collection; months at current rate. | Costs and correlation clusters are high; severe contamination risk around C-33. | **PARK — C-33 BACKGROUND ONLY** |
| F — funding settlement market-quality clock | Settlement may change spread, flow and volatility without predicting direction. Published work supports funding-cycle market-quality variation. | Distinct clock/no-trade question, but broad funding state variants failed and C-11 must remain frozen. | Funding timestamps/rates and 15m flow for six Binance symbols. | Venue-specific interval metadata through time plus spread/execution-quality series. | Compare pre/post windows with matched clock controls; reject if changes are small, unstable, or non-incremental. | Small diagnostic after metadata audit; roughly one day. | Benefit is avoided bad execution, not gross directional return; must exceed opportunity cost. | **PARK — THIRD PRIORITY** |
| G — BTC common-factor / correlated-alt no-trade | Simultaneous alt signals may be duplicated BTC beta rather than independent bets. | Portfolio admission question, distinct from directional entry; historical filtering can easily become post-hoc. | Trade journal, BTC/ETH candles, multi-symbol historical panels. | Reliable point-in-time intent census for simultaneous accepted and rejected signals and portfolio exposure. | Measure signal clusters before outcome inspection; reject if simultaneity/provenance cannot be reconstructed. | Moderate join/attribution work; days. | Must improve portfolio net expectancy/drawdown without selecting historical losers. | **PARK** |
| H — time/session modifiers | Liquidity transitions may modify stronger causal mechanisms. Calendar effect alone has weak persistence. | Modifier only; many post-hoc degrees of freedom. | Timestamps exist broadly. | A parent mechanism and unopened boundary. | No standalone test. | Near-zero code, extremely high data-mining risk. | Easily spurious and asset-specific. | **REJECT AS STANDALONE** |

## External evidence register

| Source | Claim | Actually verified here | Not verified | Transferability risk | Lynxion requirement |
|---|---|---|---|---|---|
| Kim & Hansen, *The Quarter-Hour Effect* (2026), `https://arxiv.org/abs/2607.09426` | First-seconds periodic futures activity; boundary imbalance predicts later returns in six Binance perpetuals | Paper scope, venue, approximate opening window, and 4–12h horizon reviewed | BingX behavior and Lynxion net profitability | High across venue, symbol, latency, and cost | Raw sub-minute trades plus clock controls |
| Easley et al., *Microstructure and Market Dynamics in Crypto Markets*, `https://ssrn.com/abstract=4814346` | Liquidity/price-discovery measures contain predictive information | Mechanism-level evidence reviewed | Lynxion feature portability and executable edge | Medium/high | Point-in-time flow/liquidity with realistic fills |
| Anastasopoulos et al., *Order Flow and Cryptocurrency Returns*, `https://ssrn.com/abstract=5020002` | International order flow predicts crypto returns | Mechanism-level evidence reviewed | Same-venue 15m representation or BingX execution | High | New information beyond already-rejected flow panel |
| Ruan & Streltsov, *Perpetual Futures and Cryptocurrency Market Quality*, `https://ssrn.com/abstract=4218907` | Market quality varies around funding cycles | Funding-clock mechanism reviewed | Current venue-specific no-trade benefit | Medium/high | Historical interval metadata and execution state |
| Lynxion recent BingX exit audit | 23/50 reached estimated +10% ROE; median estimated MFE +9.84%, exit +2.25%, giveback 9.11pp | Reproducible diagnostic artifact | Optimal exit, manager observability, causality, OOS profit | High due selected recent sample and inferred leverage | Provenance-valid path reconstruction and unopened confirmation |

## Selected first experiment

`LEAD A — EDGE RETENTION / PROFIT GIVEBACK STATE`, exploratory minimal diagnostic only.

### Frozen descriptive question

Among trades whose point-in-time price path is reconstructable without future leakage, is profit
giveback broad enough to matter, and does it concentrate after a state change observable at or
immediately after MFE rather than being dominated by a few symbols, strategies, or market events?

### Minimum outputs

- provenance/coverage table before economic analysis;
- MFE, MAE, realized return, retained-MFE fraction, entry-to-MFE, MFE-to-exit, and giveback;
- symbol/strategy/side/time concentration and clustered event counts;
- availability—not fabricated imputation—of BTC/ETH, flow, OI, funding, volatility, and clock state;
- explicit `REJECT`, `PREREGISTER_NEXT`, or `INSUFFICIENT_PROVENANCE` verdict.

No exit threshold, trailing percentage, production code, or economic promotion is authorized by
this diagnostic.
