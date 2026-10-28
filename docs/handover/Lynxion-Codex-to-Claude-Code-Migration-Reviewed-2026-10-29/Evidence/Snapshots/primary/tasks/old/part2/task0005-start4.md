You are now entering Engineering Sprint 2 of the Lynxion-ETS Quantitative Market Data Platform.

Milestone 0 has been completed and approved.

Do NOT modify any domain models.

Do NOT redesign any interfaces.

Implement ONLY Milestone 1.

=====================================================================

OBJECTIVE

Implement a production-grade Market Data Collector Layer.

This layer is responsible ONLY for collecting and validating market data.

No feature generation.

No trading logic.

No strategy logic.

No replay engine.

No database implementation.

=====================================================================

SCOPE

Implement collectors for Binance Futures:

- Trade Stream
- Partial Book Depth
- Diff Book Depth
- Mark Price
- Funding Rate
- Open Interest
- Liquidation Stream

=====================================================================

REQUIREMENTS

The implementation must support:

- automatic reconnect
- heartbeat monitoring
- exponential backoff
- gap detection
- REST snapshot recovery
- sequence number validation
- timestamp normalization
- duplicate event detection
- malformed message rejection
- symbol isolation
- multi-symbol subscriptions
- graceful shutdown
- structured logging
- metrics hooks
- dependency injection
- configuration-driven subscriptions

=====================================================================

ARCHITECTURE

The collector layer must only communicate through:

MarketDataCollectorPort

It must never access:

- Strategy layer
- Engine layer
- Broker layer
- Feature layer

Maintain strict Hexagonal Architecture.

=====================================================================

QUALITY

Implement:

- unit tests
- integration tests (using mocked WebSocket payloads)
- reconnect tests
- sequence gap tests
- duplicate message tests
- malformed payload tests
- timestamp consistency tests

Target deterministic behaviour.

=====================================================================

OUTPUT

Produce:

1. Production implementation
2. Test suite
3. Technical documentation
4. Sequence diagrams (text)
5. Known limitations
6. Risk assessment

Stop after Milestone 1.

Do NOT implement the order book builder.

Do NOT implement TimescaleDB.

Do NOT implement Redis.

Do NOT implement feature generation.