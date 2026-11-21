# TASK-0176 — New Public Source Feasibility Review

**Status:** COMPLETE — NO_ADMISSIBLE_SOURCE

Performed a read-only source-contract review after TASK-0175 stopped reuse of the opened historical
panels. No endpoint was called, no data was downloaded, and no conditional outcome was examined.

## Decision

No reviewed source currently supports a new cost-adjusted historical candidate without either
reusing an exhausted mechanism, introducing unresolved point-in-time bias, or crossing a paid-data
approval gate. Record `NO_ADMISSIBLE_SOURCE`; do not manufacture C-35.

## Reviewed families

### Deribit options volatility/skew

Deribit's public API documents historical volatility and volatility-index candle endpoints with
explicit millisecond start/end timestamps and continuation. This is adequate for a DVOL index series,
but not for reconstructing an executable historical option surface with contemporaneous bid/ask
depth, instrument lifecycle, and four-leg costs. Using DVOL only as a BTC directional filter would
reuse already opened directional price outcomes rather than test an options risk premium.

Source: <https://docs.deribit.com/#public-get_volatility_index_data>

### Binance dated/COIN-M futures

Binance's official public archive provides checksum-verifiable USD-M and COIN-M futures klines and
trades. However, a dated-future/perpetual proposal remains a calendar-basis/carry mechanism after
C-20/C-23/C-24/C-25, while inverse contract multipliers, expiry rolls, and synchronized executable
depth are additional unresolved requirements. It is not admitted as an independent family.

Source: <https://github.com/binance/binance-public-data/blob/master/README.md>

### Stablecoin supply and exchange/on-chain flows

DefiLlama exposes historical stablecoin-supply series and downloadable stablecoin datasets, but the
reviewed public contract does not establish immutable point-in-time publication/revision timestamps.
The documented protocol inflow endpoint is under the Pro API. A backfilled series could therefore
leak revisions, and the stronger inflow data would introduce a paid-service approval gate.

Sources: <https://defillama.com/downloads> and
<https://github.com/DefiLlama/api-docs/blob/main/llms-pro.txt>

## Re-entry condition

Historical research may reopen only when a source provides all of: immutable/versioned raw history,
causal publication timestamps, instrument identity/lifecycle, executable prices or defensible cost
model, adequate coverage, free unauthenticated acquisition, and a distinct unopened mechanism.

## Next unit

TASK-0177 should return to direct profitability evidence and audit the currently active forward-exit
cohort against its frozen coverage/linkage gates, especially the operator's profit-giveback concern.
It may report collection deficiencies but cannot tune or deploy a +5% profit floor.
