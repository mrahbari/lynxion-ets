# TASK-0160 — C-32 Endpoint Semantics Review

**Status:** COMPLETE — C-32 DATA-BLOCKED BEFORE ACTIVATION

## Objective

Independently verify that the frozen public endpoint semantics can satisfy C-32 before creating an
activation manifest or making the first prospective network call.

## Finding

- Binance's official USD-M order-book schema supplies `E` and `T` millisecond timestamps together
  with `[price, quantity]` bid/ask levels, matching the frozen parser contract.
- BingX's official depth references describe `data.bids` and `data.asks` but do not define a server
  timestamp in the depth payload. The newer official market-data skill additionally says these
  calls require a timestamp, HMAC signature, and API-key header despite being market data.
- C-32 requires a server timestamp for each exact book and prohibits secrets/authentication. A
  receipt timestamp or a separately fetched clock cannot be substituted after preregistration.

Therefore the frozen Binance/BingX cohort cannot meet its own provenance/time gate. No activation
manifest was created and no public endpoint was called. The correct verdict is `DATA_BLOCKED`, not
a relaxed parser or a venue substitution.

## Evidence

- Binance official market-data reference:
  `https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book`
- BingX official depth reference:
  `https://github.com/BingX-API/api-ai-skills/blob/main/skills/bingx-maker-entry/api-reference.md`
- BingX official market-data contract:
  `https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/SKILL.md`
- A disconnected regression proves the documented BingX shape fails closed when its server
  timestamp is absent. Existing signal and gate parameters remain unchanged.
- Eleven focused tests and the full suite pass with 903 passed and one optional import-linter skip.

## Next Unit

TASK-0161 must perform a new-mechanism/data-source selection under the sequential policy. It may
not reuse C-32's opened venue contract by changing venue, timestamp provenance, authentication, or
thresholds, and it may not call broker or production paths.
