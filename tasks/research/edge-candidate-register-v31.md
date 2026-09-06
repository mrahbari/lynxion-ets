# Edge Candidate Register v31 — C-32 Cross-Venue Perpetual Dislocation

**Status:** PRE-REGISTERED — PROSPECTIVE READ-ONLY COLLECTION ONLY

**Prospective boundary:** `2026-09-06T04:39:12Z` (`1788669552` epoch seconds).

C-32 tests whether a simultaneously executable price disagreement between Binance USD-M Futures
and BingX USDT-margined perpetual swaps converges after conservative two-leg friction. It is market-neutral and
is not a Spot/perpetual basis, directional lead/lag, or single-venue signal.

## Frozen Universe and Data

- Symbols: BTCUSDT, ETHUSDT, and SOLUSDT only.
- Contracts must be linear USDT-margined perpetuals with the same base asset. Any delivery future,
  inverse contract, multiplier ambiguity, or symbol-mapping uncertainty is rejected.
- Fetch public REST order-book depth and public funding/mark data through a standalone research
  client. Authentication, account state, broker adapters, and order methods are prohibited.
- Schedule one sampling attempt per exact UTC minute. Record receipt monotonic time, venue server
  time when supplied, raw response SHA-256, normalized levels, and validation outcome.
- Both books must be received within two seconds of each other and each accepted payload must be no
  older than three seconds at comparison time. Missing server time is fail-closed.
- Preserve append-only JSONL raw observations. Only attempts strictly after the boundary may enter
  the cohort. Restarts deduplicate by `scheduled_minute:symbol`; no historical import is allowed.

## Frozen Executable Spread

- Reference notional is 1,000 USDT per leg. Compute base quantity from the more expensive venue's
  best ask, then calculate depth-walking VWAP for the identical base quantity on both venues.
- Direction A opens by selling Binance at bid-side VWAP and buying BingX at ask-side VWAP.
- Direction B opens by selling BingX at bid-side VWAP and buying Binance at ask-side VWAP.
- Gross executable spread is `sell_vwap / buy_vwap - 1`. Both legs must independently provide the
  full quantity; partial depth, crossed books, non-positive values, or unequal normalized quantity
  are rejected.
- A signal requires gross spread at least 0.60%. If both directions appear to qualify, reject the
  snapshot as invalid. At most one unresolved virtual position per symbol is allowed.

## Frozen Virtual Execution and Economics

- Entry uses the signal snapshot's depth-walking VWAPs; no midpoint or last price is permitted.
- Beginning with the next scheduled minute, close at the first valid snapshot where the executable
  unwind spread is at most 0.05%, or at the first valid snapshot at or after four hours. If no valid
  snapshot exists within five minutes of the four-hour deadline, mark the outcome incomplete.
- Charge a fixed 0.30% round-trip friction across the four virtual market-order legs. This includes
  fees plus a conservative latency/slippage allowance beyond recorded depth VWAP. Report a frozen
  0.50% stress cost; KEEP requires positive expectancy at both costs.
- Include each venue's actual public funding settlement strictly after entry and at or before exit,
  with the correct long/short sign. Missing or ambiguous funding makes the outcome incomplete.
- Net return is measured against the 1,000-USDT reference notional: add the two legs' USDT PnL,
  divide by 1,000 USDT, subtract frozen friction, and add signed funding on the same denominator.
  No leverage, liquidation, sizing, or capital scaling is modeled.

## Frozen Gate

- Collect for at least 90 UTC days and require at least 300 completed virtual trades, at least 60
  per symbol, at least 100 per opening direction, and observations in at least 12 distinct UTC weeks.
- Form four chronological folds without allowing positions to cross fold boundaries. Require at
  least three positive folds with at least 50 completed trades each.
- KEEP additionally requires net expectancy > 0, PF > 1, daily-clustered bootstrap 95% lower bound
  > 0 using 10,000 samples and seed 320032, all three symbols positive, each venue-opening
  direction positive, maximum positive-PnL symbol concentration <= 50%, equity max drawdown <= 15%,
  and positive expectancy under 0.50% cost.
- Before all gates are evaluable, verdict is `COLLECTING`. Any failed completed gate is `REJECT`.
  A pass is only `KEEP_FOR_EXECUTION_FEASIBILITY_REVIEW`, never deployment authorization.

## Frozen Prohibitions

No threshold, notional, venue, symbol, timing tolerance, convergence rule, horizon, friction,
funding boundary, overlap rule, sample gate, fold, bootstrap, concentration, or drawdown gate may
change after the first accepted observation. No backfill, diagnostic reslicing, paper order, real
order, broker execution call, production integration, account change, or secret is authorized.
