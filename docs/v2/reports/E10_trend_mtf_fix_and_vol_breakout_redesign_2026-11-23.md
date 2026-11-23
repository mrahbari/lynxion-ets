# E10 — TrendMTF made multi-timeframe; volatility_breakout redesign (2026-11-23)

## 1. TrendMTF watcher (implementation bug, fixed)
**Finding.** `TrendMTFWatcher` was not multi-timeframe. It ran a linear regression over the last 5 / 15 / 30
*samples* of whatever was fed. Live feeds closed 1m bars, so its "timeframes" were 5, 15 and 30 minutes, and the
direction threshold (weighted normalized slope > 0.1% **per bar**) almost never fired on 1m bars. E8b: 100
directional samples at the 15m horizon in two months across 8 symbols.

**Fix** (`infrastructure/watchers/adapters/trend_mtf.py`, mode `"mtf"`):
- Closed 1m candles are downsampled into **closed** 15m / 1h / 4h bars. A forming higher-TF bar is never used, and a
  missing boundary bar closes its bucket on the next bucket.
- For each timeframe it computes the t-statistic of a log-price regression over the last 20 closed bars.
- `trend_positive` / `trend_negative` is emitted only when all three timeframes agree with |t| >= 2; otherwise
  `trend_neutral`.
- No observation is emitted until the 4h series has 20 closed bars (about 80h of 1m history).

Close-only feeds (the frozen research studies) keep the legacy behaviour (`mode="auto"`), so their pinned digests
are unchanged. Tests: `tests/unit/test_trend_mtf_multi_timeframe.py`.

**Re-test.** Same causal method as E8b: dev 2026-07..08, validation 2026-09..10, 8 symbols, gross of costs. Data:
`E8d_trend_mtf_retest.csv`.

| horizon | dev n | dev bps (t) | dev symbols+ | validation n | validation bps (t) | validation symbols+ |
|---|---|---|---|---|---|---|
| 15m | 4802 | +0.8 (1.1) | 6/8 | 5865 | -0.1 (-0.2) | 5/8 |
| 1h | 1247 | +3.6 (1.2) | 7/8 | 1521 | -1.4 (-0.6) | 2/8 |
| 4h | 313 | +19.7 (1.4) | 8/8 | 386 | -12.4 (-1.6) | 2/8 |

The watcher now works: about 48x more directional samples. It still has **no out-of-sample edge**: dev is
positive but not significant, and validation flips sign. Aligned 15m/1h/4h trend is not a stand-alone entry
signal. It stays a DIRECTION input for Fusion, with no claim of edge.

## 2. volatility_breakout redesign (no variant passes)
**Diagnosis of the original (E9).**
- 15m bars; entry on close > 20-bar high + 1.5 ATR (chasing an extended move).
- SL at the opposite 20-bar extreme, clamped to 3%; TP fixed at 2%. Reward/risk was 0.67.
- DEV PF 1.01, +12 bp gross.
- Disclosure: the E9 summary CSV also contained the original's holdout row (PF 0.88, -18.6 bp). It was visible
  before this design. So the original fails out of sample as well, and the "+12 bp gross" was DEV-only.

**Pre-registered variants.**
- Fixed in the script docstring before any result: `research/v2/experiments/e10_vol_breakout_redesign.py`.
- Common to all: Donchian-20 breakout without the ATR chase, a trend filter from the last closed higher-TF bar
  (close vs EMA50), SL = 2 ATR14, TP = 4 ATR14.
- Execution as in E9: live `sanitize_sltp_levels`, next-bar open, SL first, R-mode APM, fees and slippage.

**DEV 2025-11 → 2026-06, 10 symbols.**

| variant | trades | PF | mean R | net bps | gross bps | halves R | symbols+ | S2 DEV rule |
|---|---|---|---|---|---|---|---|---|
| A squeeze_1h (ATR14/ATR100 < 0.75, 4h filter) | 308 | 0.88 | -0.026 | -12.5 | -2.5 | -0.01 / -0.04 | 3/10 | fail |
| B donchian_1h (4h filter) | 1645 | 0.96 | -0.027 | -5.8 | +4.2 | +0.06 / -0.11 | 5/10 | fail |
| C donchian_4h (4h filter) | 771 | 0.84 | -0.103 | -31.2 | -21.2 | +0.02 / -0.23 | 2/10 | fail |
| D squeeze_15m (1h filter) | 957 | 0.85 | -0.089 | -11.7 | -1.7 | -0.16 / -0.02 | 2/10 | fail |

**Conclusion.**
- No variant passes the S2 DEV rule, so per the pre-registered rule no holdout was evaluated.
- All four are about zero before costs. Range breakouts on these 10 liquid perps over Nov 2025 – Jun 2026 carry
  no edge at 15m, 1h or 4h, with or without compression or trend filters.
- Count: 5 versions of this strategy tested in total (original + A–D). No further tuning: more variants on the
  same DEV period would be data snooping.
- volatility_breakout stays disabled in the allowlist. The platform strategy code is unchanged.

## 3. Where this leaves edge discovery
- The platform's own watcher and strategy layers have now been tested one by one with fixed plumbing. None shows a
  tradable edge.
- XS-COMBO-V1 (cross-sectional) remains the only strategy with out-of-sample evidence.
