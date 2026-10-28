You are now entering Engineering Sprint 5 of the Lynxion-ETS Quantitative Market Data Platform.

The following milestones are completed and approved:

- Backtest Engine Certification
- Market Data Domain Models
- Binance Futures Market Data Collector
- Venue Normalization Layer
- L2 Order Book Reconstruction Engine

The platform can now ingest and reconstruct market state.

Your next objective is NOT feature generation.

Your next objective is:

Milestone 2.5 — Deterministic Market Data Replay & Reconstruction Validation

=========================================================

MISSION

Build a deterministic replay validation layer that proves historical market events can be replayed and reconstructed identically to live processing.

The goal is to guarantee:

Same input event stream
=
Same reconstructed market state
=
Same generated outputs

Every time.

This is a critical requirement before quantitative feature research begins.

=========================================================

ARCHITECTURAL RULES

Preserve Hexagonal Architecture.

The replay layer must not depend on:

- Strategy layer
- Fusion engine
- Risk module
- Broker execution
- Exchange-specific adapters

The replay engine consumes only canonical market events.

Architecture:

Historical Event Source
|
v
Replay Engine
|
v
Order Book Reconstruction Engine
|
v
Market State

=========================================================

IMPLEMENT

## 1. Replay Domain Model

Create models for:

ReplaySession

Fields:

- session_id
- start_timestamp
- end_timestamp
- symbols
- source
- replay_speed
- deterministic_seed
- status


ReplayEvent

Fields:

- event_id
- timestamp
- event_type
- payload
- sequence_number


ReplayCheckpoint

Fields:

- timestamp
- order_book_checksum
- market_state_hash
- event_position


=========================================================

## 2. Replay Engine Port

Create:

ReplayEnginePort

Responsibilities:

- load historical events
- process events sequentially
- control replay speed
- pause/resume
- create checkpoints
- restore checkpoints
- verify deterministic output


=========================================================

## 3. Event Ordering Engine

Implement:

- timestamp ordering
- sequence ordering
- duplicate detection
- late event handling
- missing event detection


The system must clearly define:

exchange timestamp priority
vs
local ingestion timestamp priority.


=========================================================

## 4. Deterministic Validation

Implement validation that compares:

Run A:

Historical Events
|
v
OrderBook State

against:

Run B:

Same Historical Events
|
v
OrderBook State


The result must verify:

- identical best bid
- identical best ask
- identical depth levels
- identical checksum
- identical serialized state


=========================================================

## 5. Checkpointing

Implement checkpoint support.

The system should allow:

Replay 1 hour of data

Save checkpoint

Restart

Continue replay

Produce identical final state.


=========================================================

## 6. Testing Requirements

Add tests for:

- deterministic replay
- event ordering
- duplicate events
- missing events
- checkpoint restore
- multi-symbol replay
- different replay speeds
- corrupted event handling
- identical output after repeated runs


=========================================================

## 7. Documentation

Create:

replay_engine_documentation.md


Include:

- architecture
- event flow
- determinism guarantees
- limitations
- performance considerations
- future extensions


=========================================================

IMPORTANT RESTRICTIONS

Do NOT implement:

- Feature generators
- OBI
- CVD
- Liquidity signals
- Strategy logic
- Trading decisions
- Database storage

Do NOT optimize performance prematurely.

Focus on correctness and deterministic behavior.

=========================================================

DELIVERABLES

Provide:

1. Production implementation
2. Tests
3. Documentation
4. Determinism validation report
5. Known limitations

Stop after Milestone 2.5.

Do not continue to Feature Engine.