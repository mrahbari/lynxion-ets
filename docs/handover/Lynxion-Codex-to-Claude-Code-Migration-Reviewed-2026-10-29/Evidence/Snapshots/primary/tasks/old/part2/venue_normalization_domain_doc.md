# Market Venue Normalization: Domain Documentation

**Package Path:** `domain/entities/venue.py`, `domain/value_objects/venue.py`  
**Ports:** `MarketDataNormalizerPort` (from `domain.ports.data_ports`)  
**Adapters:** `VenueMarketDataNormalizer` (from `infrastructure/data/venue_normalizer.py`)  

---

## 1. Domain Objective & Venue Separation
In institutional quantitative trading, the venue where alpha signals are researched and generated is often different from the venue where orders are executed. To support this cleanly, the platform explicitly separates:
1.  **Market Data Venue (Alpha Source):** Real-time/historical data feeds used to generate signals (e.g. Binance Futures).
2.  **Research Data Venue:** Normalized historical datasets used for backtesting and parameter tuning (e.g. static CSV or Parquet files).
3.  **Execution Venue (Broker target):** The actual brokerage interface where positions are opened and closed (e.g. **BingX Futures**, which is the exclusive execution venue for this platform).

By normalizing all data feeds into a canonical representation, trading strategies are fully decoupled from exchange-specific formats, ensuring extensibility to other venues without strategy code changes.

---

## 2. Venue Normalization Concepts

```
+--------------------------+          +------------------------------+
|     Source Exchange      |          |      Canonical Domain        |
|  (e.g., Binance Futures) |          |                              |
|                          |          |  +------------------------+  |
|  Raw Trade:              |          |  |       TradeTick        |  |
|  {"s": "BTCUSDT",        |          |  | - symbol: BTC-USDT     |  |
|   "p": "45000.5",  ------|--------->|  | - price: 45000.5       |  |
|   "q": "0.15",           | normalize|  | - quantity: 0.15       |  |
|   "T": 1700000000000}    |          |  | - side: Side.BUY       |  |
+--------------------------+          |  +------------------------+  |
                                      +------------------------------+
```

### A. Value Objects
*   **`ExchangeVenue` (Enum):** Defines the list of supported exchanges (`BINANCE_FUTURES`, `BINGX_FUTURES`, `MEXC_FUTURES`, `PHEMEX_FUTURES`, `HISTORICAL_PROVIDER`).
*   **`MarketType` (Enum):** Identifies the type of market (`SPOT`, `FUTURES`).
*   **`ContractType` (Enum):** Classifies derivatives contracts (`SPOT`, `PERPETUAL`, `FUTURES`, `INVERSE_PERPETUAL`, `LINEAR_PERPETUAL`).
*   **`InstrumentSpecification` (Dataclass):** Details contract size, tick size, lot size, min quantity, max leverage, funding interval, and precision parameters.

### B. Entities
*   **`CanonicalInstrument`:** Binds a canonical `Symbol` to its asset definitions (`base_asset`, `quote_asset`), its `ExchangeVenue`, `MarketType`, `ContractType`, and its detailed `InstrumentSpecification`.
*   **`SymbolMapping`:** Translates an exchange-specific symbol representation (e.g. `BTCUSDT` on Binance) to the execution/canonical representation.
*   **`InstrumentMapping` (Execution Compatibility Layer):** Maps an Alpha/Market instrument (e.g., Binance Futures `BTC-USDT`) to an Execution instrument (e.g., BingX `BTC-USDT`), tracking historical price spreads (`price_difference`) and network latency offsets (`latency_difference_ms`).

---

## 3. Exchange Mapping Examples

Here is a practical example of mapping a Binance Futures instrument (Alpha source) to a BingX Futures instrument (Execution target):

### A. Instrument Setup
```python
from decimal import Decimal
from domain.value_objects import (
    Symbol, ExchangeVenue, MarketType, ContractType, InstrumentSpecification
)
from domain.entities import CanonicalInstrument, InstrumentMapping

# Binance Futures BTCUSDT Specification
binance_spec = InstrumentSpecification(
    contract_size=Decimal("1.0"),
    tick_size=Decimal("0.1"),
    lot_size=Decimal("0.001"),
    min_quantity=Decimal("0.001"),
    max_leverage=125,
    funding_interval_hours=8,
    price_precision=2,
    quantity_precision=3
)
binance_instrument = CanonicalInstrument(
    symbol=Symbol("BTC-USDT"),
    base_asset="BTC",
    quote_asset="USDT",
    venue=ExchangeVenue.BINANCE_FUTURES,
    market_type=MarketType.FUTURES,
    contract_type=ContractType.PERPETUAL,
    specification=binance_spec
)

# BingX Futures BTC-USDT Specification
bingx_spec = InstrumentSpecification(
    contract_size=Decimal("1.0"),
    tick_size=Decimal("0.1"),
    lot_size=Decimal("0.0001"),
    min_quantity=Decimal("0.0001"),
    max_leverage=150,
    funding_interval_hours=8,
    price_precision=2,
    quantity_precision=4
)
bingx_instrument = CanonicalInstrument(
    symbol=Symbol("BTC-USDT"),
    base_asset="BTC",
    quote_asset="USDT",
    venue=ExchangeVenue.BINGX_FUTURES,
    market_type=MarketType.FUTURES,
    contract_type=ContractType.PERPETUAL,
    specification=bingx_spec
)
```

### B. Compatibility Mapping
```python
# Create the compatibility mapping
compatibility_mapping = InstrumentMapping(
    alpha_instrument=binance_instrument,
    execution_instrument=bingx_instrument,
    price_difference=Decimal("2.50"),       # Binance price is typically $2.50 lower/higher than BingX
    latency_difference_ms=12                # BingX execution takes ~12ms longer than Binance feed data
)
```

---

## 4. Known Limitations
1.  **Static Calibration of Price/Latency Offsets:** Latency difference and price spread offsets are static in `InstrumentMapping`. In production, these should be continuously updated by a dynamic calibration task based on execution logs.
2.  **No Automatic Order Size Scaling:** While `InstrumentSpecification` tracks `lot_size` differences, the normalization layer does not automatically scale order volumes. The execution engine must read the mapping specification and format order volumes accordingly before submission.
