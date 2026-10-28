# Deterministic Replay Engine & Validation Layer: Technical Documentation

**Component Path:** `domain/entities/replay.py`, `infrastructure/data/replay_engine.py`  
**Test Suite:** `tests/unit/test_replay_determinism.py`  

---

## 1. Replay Architecture & Flow
The `DeterministicReplayEngine` is responsible for replaying historical event sequences chronologically to reconstruct identical order book states. It is a critical layer for quantitative feature research, verifying that backtest simulations match live production processing step-by-step.

```
+-----------------------------------------------------------------------------------+
|                                 REPLAY PIPELINE                                   |
|                                                                                   |
|  +--------------------+      +--------------------+      +---------------------+  |
|  | Historical Events  |----->|   Replay Engine    |----->|   L2 Order Book     |  |
|  |  (ReplayEvents)    |      | (Deduplicate/Sort) |      |    Reconstruction   |  |
|  +--------------------+      +---------+----------+      +----------+----------+  |
|                                        |                            |             |
|                                        v                            v             |
|                              +--------------------+      +---------------------+  |
|                              | Checkpoint/Restore |      | Reconstructed State |  |
|                              +--------------------+      +---------------------+  |
+-----------------------------------------------------------------------------------+
```

### Event Processing Steps
1.  **Deduplication:** Filters duplicate events based on unique `event_id` and `sequence_number`.
2.  **Sequential Ordering:**
    *   **Exchange Priority:** Sorts primarily by `timestamp.to_millis()`, secondarily by `sequence_number`, and tertiarily by `event_id`.
    *   **Local Priority:** Sorts primarily by `local_timestamp` found in event payload metadata.
3.  **Late Event Detection:** Validates sequence contiguity post-sorting and logs warnings on out-of-order timestamps.
4.  **Builder Routing:** Routes and applies diffs to matching `OrderBookBuilder` instances.

---

## 2. Checkpoint & State Restoration
The engine supports state preservation through `ReplayCheckpoint` objects:
*   **Checkpoint Creation:** Captures the current stream index pointer and serializes snapshots of all active builders.
*   **Restoration:** Re-applies the captured snapshots to each builder and resets the stream pointer back to the checkpoint's index.
*   **Reproduction:** Allows resuming execution from arbitrary points while producing a mathematically identical final state.

---

## 3. Determinism Validation Report
To certify the engine's deterministic properties, a multi-run comparison framework was tested:
*   **Run A:** Pre-loads a randomized event stream, processes updates sequentially, and queries final order book levels.
*   **Run B:** Resets the builders, loads the same stream, and processes them sequentially.
*   **Validation Metrics Verified:**
    *   Identical best bid and ask prices.
    *   Identical price level densities and volumes.
    *   Identical byte-level serialized representation (`OrderBookSnapshot.to_dict()`).
    *   Identical hashed checksums.
*   **Certification Status:** **PASSED**. Replaying the identical event stream yields identical order book state outputs every time.

---

## 4. Known Limitations
1.  **In-Memory Load:** The current `DeterministicReplayEngine` loads all events into an in-memory list. For very large datasets (e.g. days of high-frequency tick data), this causes high memory usage. In production, we should implement a chunk-based generator that streams events incrementally from disk.
2.  **Single-Threaded Execution:** Replay is single-threaded to preserve absolute determinism. Running symbol playbacks in parallel requires managing multiple independent thread loops or process bounds.
