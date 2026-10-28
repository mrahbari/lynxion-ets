# Binance Futures Market Data Collector: Technical Documentation

**Component Path:** `infrastructure/data/collector/binance_collector.py`  
**Implements Port:** `MarketDataCollectorPort` (from `domain.ports.data_ports`)  
**Target Platform:** Binance USD-M Futures WebSockets and REST API  

---

## 1. Overview & Architecture
The `BinanceMarketDataCollector` acts as the inbound gateway for all market microstructure events. Operating as an infrastructure adapter inside the Hexagonal Architecture, it connects to external exchange feeds, parses raw payloads, validates them against domain rules, and dispatches clean domain entities to registered callbacks.

```
+-----------------------------------------------------------------------------------+
|                                 HEXAGONAL CONTEXT                                 |
|                                                                                   |
|  +---------------------------+           +-------------------------------------+  |
|  |   INFRASTRUCTURE LAYER    |           |            DOMAIN LAYER             |  |
|  |                           |           |                                     |  |
|  |  +---------------------+  |           |  +-------------------------------+  |  |
|  |  | BinanceMarketData   |--|---------->|  |    MarketDataCollectorPort    |  |  |
|  |  | Collector           |  |           |  +---------------+---------------+  |  |
|  |  +----------+----------+  |           |                  |                  |  |
|  |             |             |           |                  v                  |  |
|  |             |             |           |  +-------------------------------+  |  |
|  |             +-------------|-----------|->|      Domain Event Dispatch      |  |  |
|  |                           |           |  +-------------------------------+  |  |
|  +---------------------------+           +-------------------------------------+  |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Sequence Diagrams

### A. Real-Time Stream Message Processing
The following diagram details the standard path of an incoming WebSocket packet (e.g., Trade, Mark Price, or Partial Depth):

```mermaid
sequenceDiagram
    autonumber
    participant BinanceWS as Binance WebSockets
    participant Collector as BinanceMarketDataCollector
    participant Entity as Domain Entities (dataclass)
    participant Callback as Subscriber Callbacks

    BinanceWS->>Collector: Raw JSON Packet
    activate Collector
    Collector->>Collector: Parse JSON & extract Event Type / Symbol
    alt Malformed JSON or Missing Symbol
        Collector->>Collector: Increment metrics["malformed_messages"] & log Warning
    else Valid Payload
        Collector->>Collector: Perform Duplicate Check (e.g. Trade ID)
        alt Duplicate Detected
            Collector->>Collector: Increment metrics["duplicate_messages"] & Discard
        else Unique Event
            Collector->>Entity: Construct (Invariants Check)
            alt Invariant Fails (ValueError)
                Collector->>Collector: Increment metrics["malformed_messages"] & Discard
            else Invariants Pass
                Collector->>Callback: Dispatch Normalized Entity (e.g., TradeTick)
            end
        end
    end
    deactivate Collector
```

### B. Sequence Gap Detection & REST Snapshot Recovery
For order book updates, keeping contiguity is critical. Gaps in update sequences trigger a REST depth snapshot synchronization:

```mermaid
sequenceDiagram
    autonumber
    participant BinanceWS as Binance WebSockets
    participant Collector as BinanceMarketDataCollector
    participant BinanceREST as Binance REST API
    participant Callback as Subscriber Callbacks

    BinanceWS->>Collector: depthUpdate event (u = 150)
    activate Collector
    Collector->>Collector: Check contiguity (expected 101, got 150)
    Collector->>Collector: Gap Detected! Increment metrics["gap_detections"]
    Collector->>Collector: Set self.book_snapshot_syncing = True
    Note over Collector: WebSocket diff depth updates are now buffered
    
    Collector->>BinanceREST: GET /fapi/v1/depth (Snapshot request)
    BinanceREST->>Collector: Snapshot payload (lastUpdateId = 160)
    
    Collector->>Callback: Dispatch OrderBookSnapshot (lastUpdateId = 160)
    
    loop For each Buffered WebSocket packet
        Collector->>Collector: Discard updates where u <= 160
        alt update covers S+1 (U <= 161 <= u)
            Collector->>Collector: Process and fast-forward state
            Collector->>Callback: Dispatch depth_diff event
        end
    end
    
    Collector->>Collector: Set self.book_snapshot_syncing = False
    deactivate Collector
```

---

## 3. Key Implementation Details

### A. Resilient Reconnections & Heartbeats
*   **Exponential Backoff:** If the WebSocket breaks, the collector sleeps for `current_reconnect_delay` (starting at 1s), doubling on each failed attempt up to `max_reconnect_delay` (60s). It resets back to 1s upon successful connection.
*   **Heartbeat Monitor:** Spawns a background task checking `time.time() - self.last_heartbeat_time` every few seconds. If it exceeds `heartbeat_interval`, it logs an error and force-closes the socket to trigger a clean reconnect.

### B. Open Interest (OI) Polling
*   Because Binance Futures does not push public Open Interest over standard WebSocket streams, the collector implements an isolated async task that polls the Binance REST API `/fapi/v1/openInterest` at configurable intervals (default: 10s) and dispatches it through the normal callback pipeline.

---

## 4. Known Limitations
1.  **Polling Latency for Open Interest:** Open Interest is retrieved via polling rather than streaming, which introduces a polling delay (up to 10s).
2.  **No L3 (Tick-by-Tick Order Queue):** Binance only provides public L2 book data (aggregated price levels). Sub-millisecond queue position tracking is not possible with these public streams.
3.  **Local Clock Dependance for Ingest Timestamps:** Local timestamps rely on the system clock. System clock drift or NTP synchronization steps can cause minor jitter in calculated ingestion delays.

---

## 5. Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **REST API Rate Limits (HTTP 429)** | High | Medium | Implement exponential backoff on REST snapshots; limit Open Interest polling frequency; reuse `httpx.AsyncClient` connections. |
| **High WebSocket Traffic during Volatility** | Medium | High | Move JSON parsing and L2 serialization to dedicated threads or async workers to prevent blocking the main asyncio event loop. |
| **Connection Drops / Silence** | High | High | Heartbeat monitor checks quietness and closes stale connections; REST recovery resolves missing sequences. |
| **Malformed Messages** | Low | Low | Strict schema checks and `try-except` blocks on object creation prevent parsing crashes. |
