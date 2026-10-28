Task: Implement HistoricalDerivativesCollector according to the approved Derivatives Data Layer Design Review.

IMPORTANT RULES:

- Architecture is frozen.
- Do not redesign anything.
- Do not create new architectural layers.
- Do not move responsibilities.
- Collector must ONLY ingest, validate, normalize and persist raw domain entities.
- No feature calculations.
- No strategy logic.
- No watcher logic.
- No Fusion changes.
- No backtester changes.

Before coding, acknowledge the following approved adjustments:

1. OpenInterest domain entity update:
   Add:
    - value_quote: Money
      Keep:
    - symbol
    - value
    - timestamp

2. Timestamp rules:
   All exchange timestamps must be normalized to UTC milliseconds.
   Historical ordering must be deterministic.

3. Feature DTO warmup handling:
   Do not implement FeatureEngine yet.
   Only ensure raw storage is compatible with future warmup handling.

4. Exchange compatibility:
   Add exchange field only if it fits existing entity conventions.
   Do not introduce unnecessary changes.

--------------------------------------------------

Implementation Scope ONLY:

Create HistoricalDerivativesCollector.

Responsibilities:

1. Binance Funding Rate Historical Downloader

Source:
Binance Futures REST API

Endpoint:
GET /fapi/v1/fundingRate

Requirements:

- Fetch historical funding rates.
- Support pagination.
- Respect exchange limits.
- Convert response into FundingRate entities.
- Validate:
    - symbol
    - timestamp
    - decimal rate precision
- Remove duplicates.
- Sort ascending by timestamp.

--------------------------------------------------

2. Binance Open Interest Historical Downloader

Source:
Binance Futures REST API

Endpoint:
GET /futures/data/openInterestHist

Requirements:

- Fetch historical OI.
- Support pagination.
- Convert response into OpenInterest entities.
- Store:
    - contract quantity
    - quote notional value
- Normalize timestamps.
- Remove duplicates.
- Sort ascending.

--------------------------------------------------

3. Storage Integration

Use existing infrastructure/data storage conventions.

Requirements:

- Persist raw entities only.
- Immutable historical records.
- Partition by:

symbol/year/month

Example:

funding_rate/BTCUSDT/2025/01
open_interest/BTCUSDT/2025/01

Do not store derived features.

--------------------------------------------------

4. Port / Interface Compliance

Before implementation inspect:

- application/data_sync/ports.py
- existing collector patterns

If a suitable port exists:
implement it.

If missing:
add the minimum required port only.

Do not redesign existing interfaces.

--------------------------------------------------

5. Error Handling

Must handle:

- API timeout
- rate limit
- empty response
- malformed exchange response
- duplicate records
- partial download

Rules:

- Fail safely.
- Never silently corrupt data.
- Log enough context for recovery.

--------------------------------------------------

6. Testing Requirements

Add tests for:

Domain:

- OpenInterest value_quote correctness
- timestamp normalization


Collector:

- successful funding download
- successful OI download
- pagination
- duplicate removal
- ordering
- API failure handling


Do NOT create tests for FeatureEngine.
It is not part of this task.

--------------------------------------------------

7. Validation Report

After implementation provide:

A) Files changed

B) Architecture impact assessment

C) Tests executed

D) Confirmation:

- No strategy code changed
- No watcher code changed
- No Fusion code changed
- No backtester behavior changed
- No lookahead risk introduced

E) Any remaining risks

--------------------------------------------------

Stop immediately if implementation requires architectural redesign.

Do not proceed beyond HistoricalDerivativesCollector.