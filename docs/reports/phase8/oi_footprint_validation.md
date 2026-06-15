# Phase 8 — oi_footprint Validation (real OI requirement)

**Date:** 2026-06-12. Question: does oi_footprint's intended hypothesis require real Open
Interest data, and if so, does a real-OI data path change its results?

## Finding 1 — the hypothesis requires OI, but the IMPLEMENTATION never uses OI
The named hypothesis ("open-interest & volume footprint": OI build-up/flush confirming or
fading price moves) **does** conceptually require open-interest data. **However, the
implementation never reads open interest at all.**

Evidence (`infrastructure/strategies/adapters/oi_footprint_strategy_adapter.py`, 126 lines):
- `generate_signal` uses only `closes` and `volumes`: `volume_spike = current_volume >
  avg_volume * 1.5`, plus `price_momentum`, `RSI`, `ATR`. **No `open_interest` field is
  ever read.**
- The OI-specific config — `self.oi_expansion` (l.21), `self.delta_strength` (l.22) — is
  **defined but never referenced** anywhere in the file (vestigial dead config).
- The `volume × 1.5` term is **not an "OI proxy"** — it is a plain volume-spike threshold;
  the strategy is, in implementation, a **volume-momentum-RSI strategy mislabeled
  "OI footprint."**
- **No data path injects `open_interest`** into the strategy's bars (confirmed across
  `infrastructure/backtest/` and the base adapter).

## Finding 2 — real-OI delta is ZERO (empirically measured via an implemented OI data path)
A **clean real-OI data path was designed and implemented**: the real OI series
(`data/history/raw/open_interest/`) is merged into each 1h bar by timestamp as
`bar['open_interest']` / `bar['open_interest_value']`, **strategy logic unchanged**. The
relevant evaluation was re-run over the OI-covered window (1h; ~705–709 aligned bars per
symbol; BTC/ETH/SOL), once **without** OI in the bars and once **with real OI** injected,
comparing `generate_signal` outputs bar-by-bar.

| symbol | bars | signals (no OI) | signals (real OI) | **delta (differing bars)** |
|---|---|---|---|---|
| BTCUSDT | 705 | 84 | 84 | **0** |
| ETHUSDT | 709 | 92 | 92 | **0** |
| SOLUSDT | 709 | 88 | 88 | **0** |

**Delta = 0 on every symbol** — signals are byte-identical with vs without real OI. This
empirically confirms the strategy ignores open interest entirely. To make it *use* OI
would require **adding OI-based entry/exit conditions = changing strategy logic**, which
Phase 8 forbids ("keep strategy logic unchanged"). (Tooling: `/tmp/oi_delta.py`-style
comparison; the OI-merge is the clean data path.)

## Finding 3 — the available OI data is insufficient anyway
`data/history/raw/open_interest/{BTC,ETH,SOL}-USDT.csv`: **hourly, ~720 rows ≈ 30 days**
(2026-05-12 → 2026-06-11), versus the 1-year, 1-minute price history used for evaluation.
Even if logic consumed OI, this window could not support the 90/180/365-day matrices.

## Ruling
- **Does the hypothesis require real OI?** Yes.
- **Does the implementation use OI (real or proxy)?** No — volume only; OI config vestigial.
- **Can a clean real-OI data path change results without logic change?** No — a real-OI
  path was implemented and re-run; the measured delta is **0** on all three symbols (the
  strategy ignores OI).
- **Implication:** this is a **hypothesis–implementation mismatch**: oi_footprint does not
  test its named hypothesis. Realizing it requires new logic (forbidden) and more OI data
  (~30d hourly is insufficient). As the volume strategy it actually is, it shows **no
  stable edge** (Phase-7 WFO: ETH 2/4, BTC 0/4, SOL 1/4 — no persistence).

## Disposition: **NEEDS_IMPROVEMENT**
Correct and runnable as a volume-momentum strategy, but it does not implement its stated
OI hypothesis and cannot (within the no-new-logic constraint, and with insufficient OI
data). Not RETIRED (it functions and is not redundant); not READY (no edge). The OI
hypothesis remains **untested**, and testing it is **out of scope** (would be new logic).
