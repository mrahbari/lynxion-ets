# Market Data Gap Analysis (Phase 13)

**Date:** 2026-06-13. For each high-value category: implementation effort, historical availability,
storage requirements, backtest feasibility, and **informational uniqueness vs OHLCV** (the key metric —
does it carry information NOT derivable from price/volume?). Grounded in the repo's already-integrated
sources (binance/bingx/mexc/phemex via ccxt + REST, CoinMarketCap) and those public APIs' real limits.
Analysis only; no profitability claims.

Scale: Effort L/M/H · Availability (usable history) None/Low/Med/High · Backtest feasibility
None/Low/Med/High · Uniqueness vs OHLCV Low/Med/High.

### Open Interest
- **Hypothesis value:** aggregate positioning (rising OI + rising price = new longs vs short-covering).
- **Effort:** L — archived ingestion stack already exists (ccxt `fetch_open_interest_history`), just re-wire.
- **Availability:** **Low** — Binance OI history endpoint caps at ~30 days (3 symbols × 30d already on disk).
- **Storage:** trivial (1 row/bar/symbol).
- **Backtest feasibility:** **Med-Low** — ~30d is too short for cross-period/WFO; deeper history needs a paid 3rd party (not integrated).
- **Uniqueness vs OHLCV:** **High** — positioning is not in price/volume. (But already tested via oi_footprint → `DIRECTIONAL_NO_GO`.)

### Funding Rates
- **Hypothesis value:** perp funding = crowd-positioning cost / sentiment; extremes precede squeezes.
- **Effort:** L — archived stack + **3 years × 24 symbols already on disk**; re-wire only.
- **Availability:** **High** — full history since listing, 8h cadence, free (binance/ccxt).
- **Storage:** trivial (8h cadence).
- **Backtest feasibility:** **High** — deep, clean, already present.
- **Uniqueness vs OHLCV:** **High** — funding is a separate market (derivatives positioning cost), not derivable from spot OHLCV.

### Liquidations
- **Hypothesis value:** forced de-leveraging cascades / reversal fuel.
- **Effort:** H — no integrated source; needs a 3rd-party aggregator (Coinglass-class).
- **Availability:** **None** (history) — Binance public REST liquidation backfill was removed; only a live WS `forceOrder` stream exists.
- **Storage:** moderate (event stream).
- **Backtest feasibility:** **None** without a paid provider (no backfill).
- **Uniqueness vs OHLCV:** **High** — forced flow is invisible in OHLCV. *(High value, but backtest-blocked.)*

### Order Book Depth (L2)
- **Hypothesis value:** resting liquidity, imbalance, spoofing/iceberg detection.
- **Effort:** H — must self-record the WS `@depth` stream going forward; reconstruction is non-trivial.
- **Availability:** **None** (history) — REST `/depth` is a snapshot; no historical book from any integrated source.
- **Storage:** **High** — full L2 is heavy (GB/day/symbol).
- **Backtest feasibility:** **None** today (snapshot/stream only); only forward-recorded data could ever be tested.
- **Uniqueness vs OHLCV:** **High** — but practically unusable for historical validation.

### Trade Flow (aggressor / CVD)
- **Hypothesis value:** buy-vs-sell aggressor imbalance (cumulative volume delta) — direction of pressure.
- **Effort:** **M-H** — build an aggTrades backfill + a CVD/imbalance store (ccxt `fetch_trades` / Binance `aggTrades`).
- **Availability:** **High** — Binance aggTrades give deep tick-by-tick history (free), backfillable.
- **Storage:** **High** — tick volume is large (compress to per-bar CVD).
- **Backtest feasibility:** **Med-High** — historical trades exist; reduce to per-bar CVD for tractable backtests.
- **Uniqueness vs OHLCV:** **High** — OHLCV has volume but not aggressor side; CVD is genuinely new directional information.

### Market Breadth
- **Hypothesis value:** % of universe advancing / aggregate momentum as a regime filter.
- **Effort:** **L** — derivable from the 514 on-disk 1m OHLCV symbols (cross-sectional), or CMC snapshots.
- **Availability:** **Med** — historical breadth derivable from existing OHLCV; CMC only gives current snapshots.
- **Storage:** low.
- **Backtest feasibility:** **High** (from existing OHLCV).
- **Uniqueness vs OHLCV:** **Low-Med** — it is a *transformation of OHLCV across symbols*, not new information; mostly a regime context.

### Cross-Asset Relationships
- **Hypothesis value:** BTC-dominance / lead-lag / correlation regimes.
- **Effort:** **M** — derivable from existing multi-symbol OHLCV, but the per-symbol adapter architecture
  can't see other symbols (would need a framework change — out of scope/frozen).
- **Availability:** **High** (data already on disk).
- **Storage:** low.
- **Backtest feasibility:** **Med** (architecture-limited).
- **Uniqueness vs OHLCV:** **Low-Med** — derived from the same OHLCV; new only in the cross-sectional relationship.

### Stablecoin Flows
- **Hypothesis value:** stablecoin supply expansion = dry powder / liquidity.
- **Effort:** **H** — true on-chain mint/burn needs an on-chain provider (not integrated; archive flags on-chain "approval-gated"). CMC market-cap is a weak proxy snapshot.
- **Availability:** **Low** (proxy snapshots only without a paid feed).
- **Storage:** low.
- **Backtest feasibility:** **Low**.
- **Uniqueness vs OHLCV:** **Med-High** — but no usable source today.

### Exchange Flows
- **Hypothesis value:** exchange in/outflows = accumulation/distribution.
- **Effort:** **H** — on-chain only (Glassnode/CryptoQuant-class), not integrated, approval-gated.
- **Availability:** **None** (no integrated source).
- **Storage:** low.
- **Backtest feasibility:** **None** today.
- **Uniqueness vs OHLCV:** **Med-High** — but no source.

## Takeaways
- **Genuinely new information vs OHLCV:** funding, OI, liquidations, order-book depth, trade flow,
  stablecoin/exchange flows (High/Med-High uniqueness). Breadth + cross-asset are **OHLCV-derived**
  (Low-Med uniqueness) — they don't add new information, only re-frame it.
- **The binding constraint is backtest feasibility, not uniqueness.** The highest-uniqueness categories
  split into: backtestable now (Funding High, Trade Flow High, OI short) vs backtest-blocked
  (Liquidations, Order Book, Stablecoin/Exchange flows — no usable history from integrated sources).
- Ranked synthesis → `data_edge_opportunity_matrix.md`.
