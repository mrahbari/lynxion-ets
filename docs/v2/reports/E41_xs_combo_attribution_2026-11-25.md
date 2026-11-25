# E41 — What drives XS-COMBO-V1? Attribution study (2026-11-25)

**Scope.** Evidence only. No change to factors, weights, lookbacks, rebalance timing or live behaviour.

**Method.**
- Script: `research/v2/experiments/e41_xs_combo_attribution.py`, pre-registered in its own commit before the run.
- The run reproduces `lib.backtest.run` exactly; this is asserted in the script.
- Books, all built with the frozen V1 machinery:

  | Book | Contents |
  |---|---|
  | D | V1 |
  | A | carry only |
  | I | illiquidity only |
  | T | taker only |
  | EQ3 | equal mix of the A, I and T books, rescaled to gross 1 |
  | SZ | small-minus-large size reference |

- Every number is the average over all 7 weekly rebalance phases.

**Status of the evidence: both windows are exploratory.**
- DEV (2020–24) is the design window of D.
- HOLDOUT_USED (2025-01..2026-10) has already been read several times.

**Raw data.** `E41_attribution_books.csv` and `E41_attribution_tests.csv`.

## Where the return comes from (V1 = D; annual, gross-1 book)

| Component | DEV 2020–24 | HOLDOUT_USED 2025–26 |
|---|---|---|
| **Net** | **+34.9 %** (Sharpe 1.94) | **+29.9 %** (Sharpe 1.43) |
| Price, long leg | +44.1 % | −43.8 % |
| Price, short leg | −14.7 % | +39.7 % |
| → Price total | +29.4 % | −4.0 % |
| … of which market exposure (book beta × market) | +4.5 % (Holm p 0.52) | +6.6 % (Holm p 0.62) |
| … of which cross-sectional selection | **+24.9 % (Holm p 0.02)** | −10.6 % (Holm p 1.0) |
| Funding, long leg | +0.4 % | **+38.6 %** |
| Funding, short leg | +9.7 % | +2.0 % |
| → Funding total | **+10.0 % (Holm p < 0.001)** | **+40.6 % (Holm p < 0.001)** |
| Execution cost (model) | −4.5 % | −6.7 % |
| Turnover (×gross/yr) | 40 | 51 |
| Book beta / BTC beta | −0.00 / −0.02 | −0.05 / −0.13 |
| Size tilt (z of log ADV) | −0.35 (small-cap) | −0.44 (small-cap) |
| Max drawdown | −16 % | −15 % |

## Findings

1. **The source of return changed between eras. It is not one stable mechanism.**
   - **2020–24:** the return was mainly price selection (+25 %/yr, significant). Long names beat short names. Funding added +10 %.
   - **2025–26:** selection was slightly negative and not significant. Almost the entire return was funding (+41 %/yr). Most of it was earned on the **long leg** (+39 %): the book was long names with negative funding (crowded shorts) and was paid for it.
   - **Funding is the only component that is significant in both windows** (t 15 and 11).

2. **It is not a market-exposure strategy.**
   - Book beta is about 0 and BTC beta is −0.02 / −0.13.
   - The market component is small (+4.5 % / +6.6 %) and not significant.
   - The book is a small-cap tilted, dollar-neutral, cross-sectional portfolio.

3. **The combination works through diversification, not signal interaction.**
   - The three single-factor books hold mostly different names. Name overlap (Jaccard) is 3–19 %.
   - Their daily returns are weakly or negatively correlated (−0.33 … +0.42).
   - D is almost a ⅓-⅓-⅓ blend of them: regression of D on A, I, T and SZ gives coefficients ≈ 0.5 each, with R² 0.85 in both windows.
   - Integration gain D − EQ3 (ranking on the summed signal vs simply mixing the three books) is +1.3 % and +4.8 %/yr, not significant (Holm p 1.0).
   - So the value is in **combining three weakly related books**, each of which fails in some era.

4. **Each factor's standalone behaviour is era-dependent.**

   | Book | DEV net | HOLDOUT net |
   |---|---|---|
   | A (carry) | +21 % | −32 % (funding +51 %, price −78 %) |
   | I (illiquidity) | +25 % | +24 % |
   | T (taker) | +19 % | +45 % |
   | SZ (size reference) | +24 % | −11 % |

   - **Illiquidity was largely a small-cap premium in DEV.** Correlation with SZ was 0.79 and its size tilt −1.05.
   - In 2025–26 the size premium turned negative (−11 %) while illiquidity stayed positive (correlation 0.43). Part of its effect is not size, but this is not proven.
   - No standalone book is promoted. T's holdout result is one era on a window already read.

## Which factors have defensible incremental value?

- **Not proven at the pre-registered 5 % level** for illiquidity or taker (E40: positive in 52 of 56 phase pairs, Holm not met).
- **Defensible as a statement about the mechanism:** D's return is a diversified blend of the three. Removing either price factor would have exposed the book to the carry leg's price loss in 2025–26 (A: −32 %/yr, max DD −63 %).
- The **funding** component is the only part that is statistically robust across both eras.

## What remains uncertain

- Which component will dominate next. Selection dominated 2020–24 and funding dominated 2025–26; nothing here predicts the next regime.
- Whether the 2025–26 long-leg funding income (long crowded-short names) persists. It is one era, already read.
- How much of illiquidity is a size premium.
- BingX realism. This study uses the Binance universe (survivorship-safe: delisted names included, closed at the last price). E2 found BingX-only Sharpe 0.96 vs 1.39. Venue effects are not attributed here.
- Statistical power. Every claim except "funding is positive in both windows" is exploratory.

## Implications (no action taken)

- **XS-COMBO-V1 stays unchanged.** Its diversification across three weakly related books is what made it survive both eras.
- **For the R5 monitor:** funding is the robust component, and the realized-carry and ex-ante carry lines watch it. Selection and price-leg risk are seen only in the P&L, drawdown and leg-correlation lines (INFO).
- Any follow-up must be separately pre-registered. One is recorded but not started: tracking the long-leg/short-leg funding split live.
