# E47 — Token unlocks: short large insider cliff unlocks (2026-11-26)

**Idea.** Keyrock (16,000+ unlocks): most unlocks show negative price pressure, starting about 30 days ahead; team unlocks are the worst. Unlock schedules are public in advance.

**Method.** Pre-registered: `research/v2/experiments/e47_token_unlocks.py`.
- Free DefiLlama emissions dataset: 375 tokens, 195 mapped to Binance perps.
- Trade: short the perp from T−30 to T+14, hedged with a long equal-weight basket of liquid perps.
- Net of 4 × 7 bp costs and token funding.
- Events: insider cliff ≥ 1 % of circulating supply; one per token per 44 days.
- 360 insider events on 67 tokens.

| Family | Window | Events | Mean net | Median net | t (week) | Positive | T−30→T | T→T+14 | Funding |
|---|---|---|---|---|---|---|---|---|---|
| INSIDER ≥ 1 % | 2022–24 | 177 | +1.2 % | **+4.9 %** | 0.39 | **66 %** | +1.4 % | −0.2 % | +0.9 % |
| INSIDER ≥ 1 % | 2025–26 | 183 | −0.6 % | **+6.0 %** | −0.06 | **65 %** | +0.4 % | +0.4 % | **−3.5 %** |
| non-insider ≥ 1 % (contrast) | 2022–24 | 84 | −0.6 % | +5.8 % | −0.7 | 64 % | +2.5 % | −4.4 % | +0.1 % |
| non-insider ≥ 1 % (contrast) | 2025–26 | 108 | +0.2 % | +5.5 % | 0.6 | 57 % | +0.3 % | +2.6 % | −3.4 % |

Insider size buckets (mean net), 2022–24 / 2025–26:
- 1–3 %: −0.7 % / +0.8 %
- 3–10 %: +1.4 % / −0.2 %
- ≥ 10 %: +17.8 % (n = 14) / −7.5 % (n = 23)

**FAIL** (rule: mean ≥ +2 %, t ≥ 2, then TEST > 0).

## Reading

1. **The typical trade works; the average does not.**
   - About 65 % of shorts win, with a median of +5–6 % per event in both windows.
   - This agrees with the "most unlocks are negative" finding.
2. **Rare squeezes erase it.**
   - The distribution has a fat right tail against the short: 5 % of events lose more than 49 %.
   - The worst losses were RIVER −346 %, SEI −243 % and ARB −151 %.
   - The mean is about zero.
3. **The trade is already crowded in 2025–26.**
   - Shorts *paid* 3.5 % funding per event (+0.9 % received in 2022–24).
   - The market prices the known schedule.
4. **The effect is not insider-specific.** Non-insider unlocks look the same: the median short wins about 5 % for any large supply increase.
   - This looks like general weakness of supply-inflating tokens, plus rare squeezes.

## What could make it tradable (not tested here)

A short with a hard stop could cut the tail: cap the loss per event and keep the 65 % winners. Testing it on these
events would be data-snooping, because both windows have now been read. Because unlock dates are known weeks in
advance, a **prospective calendar shadow** is clean:
- pre-register the stop rule;
- log every upcoming qualifying unlock and its outcome;
- no trading.
Recorded as R31; it needs an operator decision.

## Limits

- The DefiLlama schedules are today's version; past entries may have been revised.
- CoinGecko symbol mapping can be wrong for rare ticker collisions.
- The market hedge funding is ignored.
