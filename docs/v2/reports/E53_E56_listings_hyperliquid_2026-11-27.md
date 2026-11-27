# E53 listing announcements and E56 Binance–Hyperliquid funding (2026-11-27)

Both scripts were committed before running (c0e5641, 1720d82 mechanics-only fix; 0eb2ee3). TEST read once.

## E56 — Binance vs Hyperliquid funding spread, state-based exit: FAIL

Rule (fixed): daily, 3-day annualised funding spread HL − Binance; enter at |spread| ≥ 20 %/yr and 30-day carry
> 2 × 23 bp round trip; short the higher-funding venue; exit when the same-direction spread < 2 %/yr, or 60 days.
Price leg modelled through the two venues' premia (no free HL candle history). 60 coins (Binance top-60 listed on HL).

| Window | Trades | Mean days | Funding / trade | Basis / trade | Net / trade | t (week-clustered) | Win | Worst basis | Yield while invested | Yield per coin slot |
|---|---|---|---|---|---|---|---|---|---|---|
| DEV 2023-07..2024-12 | 615 | 16.2 | 1.26 % | +0.06 % | 1.09 % | 7.3 | 68 % | −0.34 % | **12.3 %/yr** | 3.7 %/yr |
| TEST 2025-01..2026-10 | 563 | 12.1 | 0.37 % | +0.05 % | 0.19 % | 4.4 | 52 % | −0.85 % | **2.9 %/yr** | 0.5 %/yr |

PASS needed ≥ 8 %/yr in both windows (t ≥ 2, worst basis > −5 %). TEST yield 2.9 %/yr → **FAIL**.

Descriptive (not part of the rule): yield while invested by half-year 15.9 % (2023H2) → 11.0 → 9.2 → 3.1 → 4.0 →
1.6 → 1.4 % (2026H2). The spread is real and statistically positive, the basis risk is small, but the edge has been
arbitraged away as Hyperliquid matured. Same conclusion as E50 (Binance–Bybit) and E46 (cash-and-carry): funding
dislocations between venues are now smaller than the cost of capturing them for a taker-only retail book.

## E53 — Listing-announcement demand shock (Upbit KRW, Binance spot): FAIL

416 deduplicated announcements (230 Binance, 186 Upbit); 138 with a Binance perp ≥ 1 day old.
LONG at announcement + 60 s, exit +15 min (primary), 20 bp costs.

| Window | n | Move already made t−5 min → t+60 s | Net +15 min | Median | t | Positive | Net +60 min |
|---|---|---|---|---|---|---|---|
| DEV (< 2025) | 18 | +11.5 % | −148 bp | −113 bp | −1.44 | 39 % | −128 bp |
| TEST 2025..2026-11 | 120 | +16.3 % | −15 bp | −59 bp | −0.26 | 44 % | +20 bp |

PASS needed ≥ +30 bp, t ≥ 2, ≥ 55 % positive in both windows → **FAIL**. The repricing (11–16 %) is complete within
the first minute; what remains after our latency is noise to slightly negative. Classified "latency race, not for us".

## Decisions

- E56: reject. No Hyperliquid account needed. Do not revisit without maker execution at both venues.
- E53: reject.
- Production: unchanged.
