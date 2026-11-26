# Structurally different edges for Lynxion: inventory, shortlist and pre-registerable experiments (2026-11-26)

Scope: proposal only. No code, strategy, risk control or live configuration was changed.

## 1. What is already known

**Live / focus**
- F1 XS-COMBO-V1: cross-sectional funding carry + illiquidity + taker flow; market-neutral weekly.
- F2 V1 + retail fade: shadow.
- F3 supply-shock short on unlocks: shadow.

**Rejected with evidence** (do not re-test without a new mechanism):

| Family | Experiments |
|---|---|
| Single-symbol price/indicator setups on 5m–4h: trend, breakout, mean reversion, VWAP, sweeps, CVD, absorption, capitulation, regime filters, trigger timing | E9–E42 |
| Single-symbol open interest | E20, E24 |
| Funding extremes | E23 |
| Pairs trading | E33 |
| Cross-sectional momentum, low-vol, skew, age, premium (premium decayed after 2021) | E2, E30, E32 |
| 1-day XS reversal (net of costs) | E31, E39 |
| Order-book imbalance, 4h | E45 |
| Top-trader following | E44 |
| Cash-and-carry: works, but positive funding compressed to 2–3 %/yr in 2025–26 | E46 |
| Unlock and new-listing shorts on history | E47, E48: typical case wins, tails and crowding kill the mean |

**Recurring lessons**
- Effects that worked in 2020–24 often decayed in 2025–26.
- Price-only single-symbol information does not survive costs.
- The survivors are structural: funding, crowding, supply.

## 2. Data

| Source | Status | Use |
|---|---|---|
| Binance USDT-M 1h klines with taker volume, 923 symbols incl. delisted, 2020–2026 | in lake | most studies |
| Binance premium index 1h, funding | in lake | basis, funding |
| Binance metrics (OI, long/short ratios), hourly, 619 symbols, 2020-09+ | in lake | positioning |
| Binance bookDepth, 5m, 40 symbols, 2023+ | in lake | liquidity |
| DefiLlama emissions (unlock schedules), 375 tokens | in lake | supply events |
| **Binance 1m klines** (monthly archives) | free, verified (HTTP 200) | intraday event timing |
| **Bybit linear funding history** | free API, back to at least 2021-01, verified | cross-venue funding |
| OKX funding history | API keeps only about 3 months | prospective only |
| **Deribit DVOL (BTC/ETH implied vol index)** | free API, from 2021, verified | volatility-risk regime |
| **DefiLlama stablecoin supply (daily)** | free API, verified | liquidity flows |
| BingX funding | live tracking already (shadow ledger) | venue spread |
| Exchange listing announcements (Binance, Coinbase, Upbit) | no clean free history; collect prospectively | listing shocks |
| Liquidations, full L2 book | paid only (Tardis / CoinGlass) | not now |

## 3. Shortlist, ranked

Scores are 1–5 (5 = best). Cost: 5 = cheap to trade.

| Rank | Hypothesis | Mechanism | Evidence potential | Novelty vs Lynxion | Data now | Cost | Feasibility on our infra | Diversification |
|---|---|---|---|---|---|---|---|---|
| 1 | **H1 Funding-settlement flow** | leveraged holders exit before paying funding; flow reverses after the stamp | 4 | 5 | yes (1m free) | 2 | 4 | 4 |
| 2 | **H2 Cross-venue funding dispersion** | leverage demand is segmented across venues; the same coin pays different funding | 4 | 4 | partial (Binance + Bybit history) | 3 | 2 (needs two venues) | 4 |
| 3 | **H3 Volatility-risk regime for XS-COMBO exposure** | after implied-vol spikes, cross-sectional carry is squeezed and spreads widen | 3 | 3 | yes (DVOL + XS returns) | 5 | 5 | 2 (overlay) |
| 4 | **H4 Stablecoin-supply impulse → crypto beta** | new USDT/USDC issuance is fresh buying power entering exchanges | 2 | 5 | yes | 5 | 4 | 5 (directional, complements neutral F1) |
| 5 | **H5 Listing-announcement demand shock** | sudden access to a large buyer base (Upbit KRW, Coinbase, Binance spot) moves perps on other venues | 3 | 5 | no (prospective) | 2 | 2 (seconds latency) | 4 |

Deprioritised:
- **Weekend / CME-gap effects:** small effects, many papers, little mechanism for alts.
- **BTC→alt minute lead-lag:** costs and spreads on lagging alts exceed the effect at our latency.
- **Options-expiry pinning:** few events (about 70 monthly) and a BTC/ETH-only universe.

## 4. Experiments (minimal, pre-registerable)

### H1 — Funding-settlement flow

**Mechanism.** Funding is paid only by positions open at 00/08/16 UTC.
- With large positive funding, some longs close just before the stamp and reopen after.
- Arbitrageurs (short perp, long spot) do the mirror.
- This creates a predictable, short-lived price pressure: down into the stamp, rebound after.
- When funding is negative, the pressure is mirrored.

**Hypothesis.** For perps whose last funding rate is in the top decile across symbols, the return from T−60 min to T is
negative and the return from T to T+60 min is positive. The rebound beats a 14 bp round trip on average. Mirror for the
bottom decile.

**Data.** Binance 1m klines (monthly zips) for about 60 liquid perps, 2022–2026; funding from the lake.

**Minimal experiment.**
- **Pre-registered constants:** windows ±60 min; deciles fixed; no other parameter.
- **Events:** every settlement (about 3 per day per symbol).
- **Report:** gross and net pre/post returns in bp; t clustered by settlement time; share of symbols with the predicted sign.
- **Windows:** DEV 2022–2024, TEST 2025–26.

**Validation.**
- Net of 2 × (5 + 2) bp.
- Funding is not paid when the position is closed through the stamp, so the "post" leg is exactly what a trader would get.
- Check that the effect is not a generic hour-of-day pattern: same windows on non-settlement hours as control.

**Failure modes.**
- Effect real but under 14 bp (likely for majors). Then use it only as execution timing for F1 rebalances and F3 entries:
  avoid buying into the minutes before a stamp on high-funding names.
- Partly overlaps F1 (both funding-based); timescale and mechanism differ.

**Criteria.**
- **Reject:** gross < 5 bp or wrong sign in TEST.
- **Execution aid:** gross ≥ 5 bp but net ≤ 0.
- **Prospective shadow:** net ≥ +3 bp, t ≥ 2 in both windows, ≥ 60 % of symbols.

### H2 — Cross-venue funding dispersion

**Mechanism.** Leverage demand differs by venue (user base, collateral rules, listing timing).
- The same coin can pay +0.05 %/8h on one venue and ~0 on another for days.
- Long perp where funding is low and short perp where it is high is price-neutral. It collects the spread net of fees
  and basis drift.

**Hypothesis.** When the trailing 3-day funding spread between Binance and Bybit for the same coin exceeds 20 %/yr:
- a long/short perp pair (long the cheaper venue, short the dearer) earns ≥ 8 %/yr on capital over the next 7 days;
- this is net of 4 × 7 bp, both venues' funding, and price-basis drift.

**Data.**
- Bybit funding history (free API, 2021+) for the common symbols; Binance funding and prices from the lake.
- Bybit 1h klines (free API) for the basis drift between venue prices.

**Minimal experiment.**
- Weekly decision, 2022–24 DEV, 2025–26 TEST.
- Report spread persistence (autocorrelation of the spread), net return, time invested, worst basis drift.

**Validation.**
- Capital counts both legs' margin (2× notional at 1×, or less with higher leverage, reported separately).
- Venue risk and transfer friction are not modelled; stated as a limit.

**Failure modes.**
- Spreads are rare or close before they can be harvested.
- Basis drift between venue mark prices eats the spread.
- Compression like E46.
- Overlap with F1: both earn funding, but this is venue-relative and price-neutral per coin.

**Criteria.**
- **Reject:** net < 4 %/yr in TEST, or spread half-life < 1 day.
- **Prospective:** ≥ 8 %/yr in both windows.
- **Live:** would need a Bybit account; an operator decision. Live BingX vs Binance funding is already logged by F1
  tracking and can serve as a third venue.

### H3 — Volatility-risk regime overlay for XS-COMBO

**Mechanism.** In stress (implied vol jumps), crowded shorts are squeezed and illiquid longs gap down. A market-neutral
carry book suffers in exactly these windows. DVOL is a forward-looking, non-price-history measure of stress.

**Hypothesis.** XS-COMBO's next-7-day net return is lower after the BTC DVOL 7-day change is in its top decile (vol
shock) than otherwise, by enough that halving gross exposure in those weeks raises the Sharpe without cutting annual
return by more than 10 %.

**Data.** Deribit DVOL daily (2021+, free); V1 phase-averaged daily returns (E41 code).

**Minimal experiment.**
- One pre-defined rule: half exposure when DVOL 7-day change is above the DEV 90th percentile.
- 7 phases; DEV 2021-04..2024, TEST 2025–26.

**Validation.**
- Paired against V1.
- Guard against the E38 finding: "weak periods are followed by recovery", so de-risking after stress may cut the
  rebound. The test must show TEST improvement, not just DEV.

**Failure modes.** De-risking right before the recovery. Only about 25 shock weeks in TEST, so power is low.

**Criteria.**
- **Reject:** Sharpe not higher in both windows.
- **Monitor input only:** improvement in one window, recorded as an R5 INFO line.
- **Candidate:** both windows better, and drawdown lower.

### H4 — Stablecoin-supply impulse and crypto beta

**Mechanism.** Net stablecoin issuance (USDT + USDC) is new dollar liquidity that mostly enters through exchanges.
Literature: Griffin & Shams (2020) on Tether timing; later evidence is mixed.

**Hypothesis.** The 7-day change in total stablecoin supply (z-scored over 1 year) predicts the next-7-day return of an
equal-weight liquid-perp basket. Long the basket when z > 1, flat otherwise; this beats always-long on a risk-adjusted
basis, net of costs and funding.

**Data.** DefiLlama stablecoin charts (daily, free); lake prices and funding.

**Minimal experiment.**
- One rule, weekly, 2020–2024 DEV, 2025–26 TEST.
- Report hit rate, Sharpe vs buy-and-hold, and exposure.

**Validation.**
- About 100 independent weeks in TEST, so power is low.
- Must also beat a simple 4-week momentum timing rule, so it is not momentum in disguise.

**Failure modes.**
- Issuance follows prices (reverse causality).
- Effect concentrated in 2020–21.

**Criteria.**
- **Reject:** TEST Sharpe ≤ always-long, or not better than the momentum control.
- **Candidate:** both windows better than both benchmarks. It would be Lynxion's first directional sleeve; it diversifies
  F1, which is neutral.

### H5 — Listing-announcement demand shock (prospective only)

**Mechanism.** An Upbit KRW, Coinbase or Binance spot listing gives a coin a large new buyer base. Perps on other venues
reprice within seconds to minutes. The tradable part after our latency is uncertain.

**Hypothesis.** From announcement time + 60 s, the perp continues in the announcement direction for at least 15 minutes,
by more than 30 bp net on average.

**Data.** None historical and free. Build a collector: poll the announcement APIs/RSS every 15 s, plus Binance 1m klines.

**Minimal experiment.**
- 8 weeks of collection, then a pre-registered event study.
- Latency is measured as part of the result.

**Failure modes.**
- The move completes before +60 s.
- False or ambiguous announcements.

**Criteria.**
- **Reject:** mean net ≤ 0 at +60 s entry.
- **Further research:** positive at +10 s but not at +60 s. That would mean the edge is a latency race we do not win.

## 5. Recommended order

1. **H1 first.** Cheapest; data is free and quick to load (1m zips); a genuinely new mechanism. It has a fallback value
   as an execution aid for F1 and F3.
2. **H2 historical (Binance vs Bybit).** Strongest structural mechanism; tells us whether a second venue is worth having.
3. **H3** as a cheap overlay study for F1.
4. **H4** as the only directional candidate.
5. **H5 collector** only if 1–4 leave capacity. It is a long prospective project.

Each experiment will be committed before it is run, read once on TEST, and reported. Nothing is deployed without a
separate operator decision.
