# E43 — R20: price-risk-neutral funding carry (2026-11-25)

**Question.** Does ranking carry *within* volatility or beta terciles remove the price loss of the carry book?
**Method.** Evidence only. Pre-registered: `research/v2/experiments/e43_neutral_carry.py`. Everything else uses the frozen V1 machinery. All 7 weekly phases, paired. Both windows are exploratory.
**Raw data.** `E43_neutral_carry_by_phase.csv`.

## Results (annual, phase mean)

| Variant | 2020–24 net | 2025–26 net | 2025–26 price leg | 2025–26 max DD |
|---|---|---|---|---|
| A carry | +20.8 % | −32.3 % | −78.0 % | −64 % |
| A_VN vol-neutral carry | +14.1 % | −10.7 % | −50.6 % | −47 % |
| A_BN beta-neutral carry | +16.9 % | −28.7 % | −70.9 % | −59 % |
| D V1 (live) | +35.0 % | +30.4 % | −3.7 % | −19 % |
| D_VN V1 with vol-neutral carry | +32.5 % | +33.9 % | +0.7 % | −17 % |

**Comparisons**

| Comparison | 2020–24 | 2025–26 | Result |
|---|---|---|---|
| A_VN vs A | −6.7 %, 0/7 phases | +21.6 %, 7/7 phases | NOT BETTER |
| A_BN vs A | −3.9 %, 1/7 phases | +3.6 %, 5/7 phases | NOT BETTER |
| D_VN vs D | −2.5 %, 0/7 phases | +3.5 %, 4/7 phases | NOT BETTER (not a replacement candidate) |

## Reading

- **The effect depends on the era, like every factor so far.**
  - Vol-neutral carry removed about a third of the carry book's 2025–26 price loss (−78 % → −51 %).
  - It cost 2020–24 in every phase.
- **For V1 the change is small and inconsistent.** −2.5 %/yr in 2020–24 and +3.5 %/yr in 2025–26.
- **V1's diversification already does most of this job.**
- **R20 closed. XS-COMBO-V1 unchanged.**
