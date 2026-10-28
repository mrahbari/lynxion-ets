You are now entering Engineering Sprint 1 of the Lynxion-ETS Quantitative Market Data Platform.

The Market Data Architecture Specification has been approved.

Do NOT redesign it.

Your task is to implement ONLY Milestone 0.

Nothing else.

========================================================

OBJECTIVE

Implement the complete Domain Layer and Port Interfaces for the Market Data Platform.

No infrastructure adapters.

No WebSocket code.

No database code.

No Redis.

No TimescaleDB.

No replay engine.

Only the domain contracts.

========================================================

Deliverables

Implement:

1. Domain Models

Create immutable domain models for:

- OrderBookSnapshot
- OrderBookLevel
- TradeTick
- OpenInterest
- FundingRate
- LiquidationEvent
- MarkPrice
- IndexPrice
- PremiumIndex
- MarketState
- VolumeProfile
- SessionStatistics

2. Value Objects

Implement:

- Symbol
- ExchangeTimestamp
- Price
- Quantity
- Side
- OrderType
- LiquidityType

3. Ports

Create interfaces for:

- MarketDataCollectorPort
- MarketDataStoragePort
- FeatureGeneratorPort
- ReplayEnginePort
- DataValidationPort

4. Events

Define domain events for:

- OrderBookUpdated
- TradeReceived
- OpenInterestUpdated
- FundingUpdated
- LiquidationDetected
- FeatureGenerated

5. Serialization

All models must support deterministic serialization.

6. Validation

Implement invariant validation inside domain objects.

Reject invalid market data.

========================================================

Requirements

- Preserve Hexagonal Architecture.
- No framework dependencies.
- No infrastructure code.
- No persistence.
- No networking.
- No mocks.
- Full unit test coverage.
- Rich documentation.
- SOLID.
- DDD.
- Production-grade quality.

========================================================

Validation

Before completion verify:

- architecture consistency
- immutability
- serialization stability
- thread safety
- deterministic equality
- unit tests

========================================================

Stop after Milestone 0.

Do not implement any infrastructure.

Do not continue to Milestone 1.