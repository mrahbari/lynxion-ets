You are now entering Engineering Sprint 3 of the Lynxion-ETS Quantitative Market Data Platform.

Milestone 1 (Binance Futures Market Data Collector) is complete and approved.

Important architecture clarification:

BingX is the ONLY execution broker.

Other exchanges are used for:
- market research
- historical data
- liquidity analysis
- feature generation
- alpha discovery

The system must explicitly separate:

1. Market Data Venue
2. Research Data Venue
3. Execution Venue

Do not assume that the execution venue is the same as the alpha data venue.

=========================================================

OBJECTIVE

Implement Market Venue Normalization Layer.

This layer must create a canonical representation of multi-exchange market data without coupling strategies to any exchange.

=========================================================

SUPPORTED VENUES

Initial support:

- Binance Futures (market data)
- BingX Futures (execution reference)
- Existing historical data providers

Design the system so additional exchanges can be added later.

=========================================================

IMPLEMENT

1. Venue Domain Model

Create:

ExchangeVenue
MarketType
ContractType
SymbolMapping
InstrumentSpecification

Support:

- spot
- perpetual futures
- futures
- inverse contracts
- linear contracts

=========================================================

2. Canonical Instrument Model

Normalize:

- symbol
- base asset
- quote asset
- contract size
- tick size
- lot size
- leverage limits
- funding interval
- price precision
- quantity precision

=========================================================

3. Market Data Normalization Port

Create:

MarketDataNormalizerPort

Responsibilities:

- exchange message -> canonical event
- timestamp normalization
- symbol normalization
- contract normalization
- price normalization
- quantity normalization

=========================================================

4. Execution Compatibility Layer

Create a mapping model:

Alpha Instrument
|
|
Execution Instrument

Example:

BTCUSDT Binance Futures
|
|
BTC-USDT Perpetual BingX

The system must explicitly track:

- source exchange
- execution exchange
- price difference
- latency difference

=========================================================

5. Validation

Add tests for:

- symbol mismatches
- precision differences
- contract differences
- missing mappings
- invalid instruments
- deterministic normalization

=========================================================

RULES

Do NOT implement:

- Order Book Builder
- Feature Generation
- Strategy Logic
- Broker Execution

Only implement venue normalization.

=========================================================

DELIVERABLES

Provide:

1. Implementation
2. Tests
3. Domain documentation
4. Exchange mapping examples
5. Known limitations

Stop after this milestone.