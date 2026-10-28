You are now entering Engineering Sprint 4 of the Lynxion-ETS Quantitative Market Data Platform.

Milestone 1.5 (Venue Normalization Layer) is complete and approved.

The platform now has:

- Canonical market data models
- Exchange normalization
- Binance market collectors
- BingX execution separation

Your next objective is ONLY:

Milestone 2 — L2 Order Book Reconstruction Engine.

Do not implement feature generation.

Do not implement strategies.

Do not implement alpha logic.

Do not implement execution.

=========================================================

MISSION

Build a production-grade deterministic Level 2 order book engine capable of reconstructing the exact market depth state from exchange diff-depth events.

The engine must support:

- live processing
- historical replay
- deterministic reconstruction
- gap recovery
- validation

=========================================================

ARCHITECTURE

Maintain:

Collector
|
v
Canonical Market Events
|
v
Order Book Builder
|
v
Market State

The Order Book Builder must be independent from:

- Binance
- BingX
- Strategy layer
- Feature layer

It consumes only canonical market events.

=========================================================

IMPLEMENT

1. OrderBookState

Create an in-memory order book representation.

Requirements:

- bid price levels
- ask price levels
- quantity updates
- insert
- update
- delete
- best bid
- best ask
- spread calculation
- mid price
- depth queries

=========================================================

2. Diff Update Processor

Implement:

- sequence tracking
- update ID validation
- snapshot initialization
- incremental updates
- stale event rejection
- duplicate event handling
- out-of-order event handling

=========================================================

3. Snapshot Recovery

Implement recovery flow:

When sequence continuity breaks:

Current state
|
X
|
REST snapshot recovery
|
|
rebuild state
|
continue processing

=========================================================

4. Deterministic Replay

The same event stream must always produce:

- identical order book state
- identical checksum
- identical serialized output

=========================================================

5. Validation

Implement:

- crossed book detection
- negative quantity rejection
- invalid price rejection
- sequence gap detection
- timestamp validation
- checksum validation if exchange provides it

=========================================================

6. Performance Requirements

Document:

- processing latency
- memory usage
- supported symbol count
- expected update throughput

=========================================================

TEST REQUIREMENTS

Add tests for:

- snapshot initialization
- bid update
- ask update
- level deletion
- sequence gap recovery
- duplicate events
- out-of-order events
- crossed book prevention
- deterministic replay
- multi-symbol isolation

=========================================================

DELIVERABLES

Provide:

1. Implementation
2. Unit tests
3. Integration tests
4. Performance notes
5. Order book reconstruction documentation
6. Known limitations

Stop after Milestone 2.

Do not continue to feature generation.