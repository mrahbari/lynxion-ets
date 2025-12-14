# WFO Downloader System - Complete Guide

## 📋 Overview of Downloader Logic

The WFO Downloader System follows Hedge Fund standards for production-level data acquisition and management. The system implements the following architecture:

```
Downloader → Resample Engine → Market Data Loader → Strategy Engine → Watcher Layer → MultiSymbol Router → Execution Engine → WFO Engine
```

This system features:

- **Standard Data Architecture**: 25 crypto coins with 1m base timeframe data
- **Production-Ready Sync**: Full refresh (6-month) and daily incremental updates
- **Multi-Timeframe Generation**: Convert 1m → 5m/15m/30m/1h with zero-drift resampling
- **Enterprise Risk Management**: Capital allocation and position sizing controls
- **WFO Integration**: Seamless connection to Walk-Forward Optimization pipeline
- **Rate Limit Safety**: API-safe download patterns with bulk/batch processing
- **RETUNE Integration**: Automatic retune triggering when fresh data is available

## 📁 Data Directory Structure

The system uses the following standardized directory structure:

```
/data/
    /history/raw/
        /1m/
            BTCUSDT.csv
            ETHUSDT.csv
            ... (25 coins total)
    /history/processed/
        /5m/
            BTCUSDT.csv
            ETHUSDT.csv
        /15m/
            BTCUSDT.csv
            ETHUSDT.csv
        /30m/
            BTCUSDT.csv
            ETHUSDT.csv
        /1h/
            BTCUSDT.csv
            ETHUSDT.csv
```

## ⚙️ Configuration (`.env` file)

All settings are now configurable via `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit .env to configure your settings
nano .env
```

Key configurations:
- `WFO_COINS`: Comma-separated list of 25 coins
- `RETUNE_ENABLED`: Set to `true` to enable auto-retuning (preserved from original)
- `WFO_SYNC_DAYS`: Full refresh interval (180 days = 6 months)
- `WFO_REFRESH_INTERVAL_HOURS`: Incremental sync frequency
- `RETUNE_INTERVAL_HOURS`: How often to trigger retune after new data

## 🚀 How to Run Full Refresh

Full refresh downloads complete 180-day (6-month) history of 1-minute data for all 25 coins:

```python
from infrastructure.data.data_sync_engine import DataSyncEngine
from infrastructure.data.binance_client import BinanceClient
from infrastructure.data.candle_store import CandleStore
from infrastructure.data.wfo_config import config

# Initialize components with configuration
client = BinanceClient(
    retry=config.get_api_settings()['retry_attempts'],
    sleep=config.get_api_settings()['rate_limit_delay']
)
store = CandleStore(root=config.get_data_paths()['raw_dir'])

# Create sync engine with configured coins
engine = DataSyncEngine(
    symbols=config.get_coins(),  # Now configurable via .env!
    client=client,
    store=store
)

# Run full refresh (downloads 6 months of 1m data for all coins)
engine.full_refresh(days=config.get_sync_settings()['sync_days'])
```

Or use the simulation script for testing:
```bash
python simulate_full_download.py
```

## ⏱️ How Incremental Sync Works

Daily incremental sync appends new data and handles deduplication:

```python
# Run incremental sync (updates with recent data)
engine.incremental_update()
```

The incremental sync system:

1. **Downloads** recent 1-minute candles (last 2 days by default)
2. **Merges** with existing data
3. **Deduplicates** based on timestamp
4. **Sorts** by timestamp in ascending order
5. **Saves** the updated dataset

## 🔄 How to Generate Resampled Timeframes

Convert 1-minute data to higher timeframes:

```python
from infrastructure.data.resample_engine import ResampleEngine
from infrastructure.data.wfo_config import config

# Initialize resample engine with configuration
resample_engine = ResampleEngine(
    raw_root=config.get_data_paths()['raw_dir'],
    out_root=config.get_data_paths()['processed_dir']
)

# Resample a single symbol to all timeframes (5m, 15m, 30m, 1h)
resample_engine.resample_tf("BTCUSDT")

# Resample all configured symbols to all timeframes
symbols = config.get_coins()
resample_engine.resample_all(symbols)
```

## ⏰ Automatic Sync Service with RETUNE Integration

The system includes an automatic sync service that integrates with the existing RETUNE functionality:

```python
from infrastructure.data.auto_sync_service import create_auto_sync_service

# Create and start the auto-sync service
service = create_auto_sync_service()
service.start_auto_sync()

# The service will automatically:
# - Run full refresh every 180 days
# - Run incremental sync daily at 01:00
# - Run resampling daily at 02:00  
# - Trigger RETUNE when fresh data is available
# - Respect RETUNE configuration (RETUNE_ENABLED=true preserved)
```

The auto-sync service intelligently triggers the RETUNE process when:
1. Full refresh completes successfully
2. Incremental sync completes successfully
3. RETUNE is enabled in configuration

## 🔌 RETUNE Integration

The system preserves and enhances the original RETUNE functionality:

- `RETUNE_ENABLED=true` is maintained from original configuration
- Auto-sync triggers RETUNE when new data is available
- All original RETUNE settings are preserved:
  - `RETUNE_INTERVAL_HOURS`
  - `RETUNE_PERFORMANCE_THRESHOLD`
  - `RETUNE_EVALS_PER_RETUNE`

## 🧪 Testing Instructions

### 1. Complete System Test

Run the comprehensive simulation:
```bash
python simulate_full_download.py
```

### 2. RETUNE Integration Test

Test RETUNE configuration:
```bash
python test_retune_integration.py
```

### 3. System Integration Test

Verify compatibility with existing components:
```bash
python test_system_integration.py
```

### 4. Downloader Tests

Test individual components:
```bash
python -m pytest tests/test_wfo_downloader.py -v
```

### 5. Manual Operation Tests

Test each component individually:

#### Downloader Tests
```bash
# Test individual downloader components
python -c "
from infrastructure.data.binance_client import BinanceClient
from infrastructure.data.candle_store import CandleStore
from infrastructure.data.wfo_config import config

client = BinanceClient()
store = CandleStore()

# Test with a small sample
data = client.get_klines('BTCUSDT', '1m', 1609459200000, 1609459800000, limit=10)
print(f'Downloaded {len(data)} klines')
"
```

#### Resampling Tests
```bash
# Test resample functionality
python -c "
from infrastructure.data.resample_engine import ResampleEngine
from infrastructure.data.wfo_config import config
import pandas as pd

# Test that the engine is properly configured
engine = ResampleEngine(
    raw_root=config.get_data_paths()['raw_dir'],
    out_root=config.get_data_paths()['processed_dir']
)
print('Resample engine initialized with configured paths')
print(f'Raw path: {config.get_data_paths()[\"raw_dir\"]}')
print(f'Processed path: {config.get_data_paths()[\"processed_dir\"]}')
"
```

#### Loader Tests
```bash
# Test data loader
python -c "
from infrastructure.data.market_data_loader import MarketDataLoader
from infrastructure.data.wfo_config import config

loader = MarketDataLoader(
    root_raw=config.get_data_paths()['data_dir'] + '/raw',
    root_processed=config.get_data_paths()['data_dir'] + '/processed'
)

print('MarketDataLoader initialized with configured paths')
print(f'Can load 1m data from: {config.get_data_paths()[\"data_dir\"]}/raw/1m/')
print(f'Can load processed data from: {config.get_data_paths()[\"data_dir\"]}/processed/')
"
```

#### RETUNE Tests
```bash
# Test RETUNE integration
python -c "
from infrastructure.data.wfo_config import config

retune_settings = config.get_retune_settings()
print(f'RETUNE is enabled: {retune_settings[\"enabled\"]}')
print(f'RETUNE interval: {retune_settings[\"interval_hours\"]} hours')
print(f'Performance threshold: {retune_settings[\"performance_threshold\"]}')
print(f'Evals per cycle: {retune_settings[\"evals_per_cycle\"]}')

if retune_settings['enabled']:
    print('✅ RETUNE system is properly configured and enabled')
else:
    print('⚠️ RETUNE system is disabled')
"
```

## 📊 Example Commands

### Full System Setup and Test:

```bash
# 1. Initialize data directories
mkdir -p ./data/{raw/1m,processed/{5m,15m,30m,1h}}

# 2. Run downloader test (with sample data)
python tests/test_wfo_downloader.py

# 3. Run complete system simulation
python simulate_full_download.py

# 4. Run RETUNE integration test
python test_retune_integration.py

# 5. Load and verify sample data
python -c "
from infrastructure.data.market_data_loader import MarketDataLoader
from infrastructure.data.wfo_config import config

loader = MarketDataLoader(
    root_raw=config.get_data_paths()['data_dir'] + '/raw',
    root_processed=config.get_data_paths()['data_dir'] + '/processed'
)

try:
    df = loader.load('BTCUSDT', '5m')
    print(f'Data loaded: {len(df)} records, columns: {list(df.columns)}')
    print('✅ Data loading from configured paths works correctly')
except Exception as e:
    print(f'Data availability check: {e}')
    print('Note: Run simulation first to generate sample data.')
"
```

### Production-Ready Downloader:

```bash
# Full refresh of all 25 coins for 6 months (configurable)
python -c "
from infrastructure.data.data_sync_engine import DataSyncEngine
from infrastructure.data.binance_client import BinanceClient
from infrastructure.data.candle_store import CandleStore
from infrastructure.data.wfo_config import config

# Use configured settings
client = BinanceClient(
    retry=config.get_api_settings()['retry_attempts'],
    sleep=config.get_api_settings()['rate_limit_delay']
)
store = CandleStore(root=config.get_data_paths()['raw_dir'])

engine = DataSyncEngine(
    symbols=config.get_coins(),  # Configurable via .env
    client=client,
    store=store
)

print(f'Configured for {len(config.get_coins())} coins')
print(f'Sync days: {config.get_sync_settings()[\"sync_days\"]}')
print(f'RETUNE enabled: {config.get_retune_settings()[\"enabled\"]}')

# Would run: engine.full_refresh(days=config.get_sync_settings()['sync_days'])
print('Downloader engine configured and ready for production use!')
"
```

### Auto-sync Service:

```bash
# Start the auto-sync service (integrates with RETUNE)
python -c "
from infrastructure.data.auto_sync_service import create_auto_sync_service
from infrastructure.data.wfo_config import config

service = create_auto_sync_service()

print('Auto-sync service configured with:')
print(f'- {len(config.get_coins())} coins')
print(f'- Full refresh: every {config.get_sync_settings()[\"sync_days\"]} days')
print(f'- Incremental sync: every {config.get_sync_settings()[\"refresh_interval_hours\"]} hours')
print(f'- RETUNE: {config.get_retune_settings()[\"enabled\"]} (every {config.get_retune_settings()[\"interval_hours\"]} hours)')

print('Service is ready to start with: service.start_auto_sync()')
"
```

## 🔧 Troubleshooting

### Common Issues:

1. **"Data not found" errors**: Ensure data files exist in the correct directory structure
2. **API rate limit issues**: The system includes built-in rate limiting, but verify your API key limits
3. **Memory issues**: For large datasets, consider using chunked processing
4. **RETUNE not triggering**: Check that `RETUNE_ENABLED=true` in your .env file

### Log Files:

- System logs: `logs/` directory
- Data download logs: Check the logger output in each component
- WFO execution logs: Generated during pipeline runs
- Auto-sync logs: Generated by auto_sync_service

### Configuration Verification:

```bash
# Quick check of all configurations
python -c "
from infrastructure.data.wfo_config import config

print('📋 Current Configuration:')
print(f'WFO Enabled: {config.wfo_enabled}')
print(f'Coins: {len(config.get_coins())} ({config.get_coins()[:3]}...)')
print(f'Timeframes: {config.get_timeframes()}')
print(f'RETUNE Enabled: {config.get_retune_settings()[\"enabled\"]}')
print(f'Refresh Interval: {config.get_sync_settings()[\"refresh_interval_hours\"]} hours')
print(f'Sync Days: {config.get_sync_settings()[\"sync_days\"]}')
print('✅ Configuration loaded successfully')
"
```

## 🏗️ Architectural Notes

- **Hexagonal Architecture**: All components follow clean architecture principles
- **Dependency Injection**: Services are injected to maintain loose coupling
- **Rate Limit Safety**: Bulk downloading with controlled intervals
- **Data Validation**: Gap detection and data quality checks
- **Error Handling**: Comprehensive exception handling throughout
- **Scalability**: Designed to handle 25+ coins efficiently
- **RETUNE Integration**: Preserves original RETUNE functionality while adding auto-trigger capability
- **Backward Compatibility**: All original configurations maintained

## 🚀 Production Deployment

### 1. Initial Setup:
```bash
# Copy and configure the environment
cp .env.example .env
# Edit .env with your API keys and settings

# Create required directories
mkdir -p ./data/{raw/1m,processed/{5m,15m,30m,1h}}
mkdir -p ./logs
mkdir -p ./results
```

### 2. Initial Data Load:
```bash
# Run initial full refresh
python -c "
from infrastructure.data.auto_sync_service import create_auto_sync_service
service = create_auto_sync_service()
service.manual_full_refresh()  # Run once manually
"
```

### 3. Start Auto-sync:
```bash
# Start the production service
python -c "
from infrastructure.data.auto_sync_service import create_auto_sync_service
import time

service = create_auto_sync_service()
service.start_auto_sync()

print('Auto-sync service started successfully!')
print('The service will:')
print('- Download fresh data automatically')
print('- Trigger RETUNE when data is updated')
print('- Maintain all existing RETUNE functionality')
print('- Run continuously in the background')

# Keep running (in production, this would run as a service)
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    service.stop_auto_sync()
"
```

The system is now ready for production use with Backtesting, Hyperopt, and Walk-Forward Optimization workflows, with seamless RETUNE integration!