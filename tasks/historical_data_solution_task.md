# Task: Comprehensive Historical Data Solution for Trading System

## Overview
This task addresses the critical issue where more than 90% of symbols are being rejected due to historical data fetching failures. The system needs a robust solution that ensures historical data availability while maintaining performance and reliability.

## Current Issues
1. **High Rejection Rate**: 90%+ of symbols rejected due to historical data fetching failures
2. **Network Dependencies**: System completely dependent on real-time data fetching from exchanges
3. **Resource Exhaustion**: Repeated failed attempts causing "too many open files" errors
4. **No Fallback**: No local caching or synthetic data generation capabilities
5. **Connectivity Issues**: Network/DNS resolution errors preventing access to exchange APIs

## Solution Requirements

### 1. Automated Historical Data Download Job
Create a scheduled job that downloads historical data for approved symbols every hour:

```python
# Example implementation in runner_historical_data_sync.py
import schedule
import time
from datetime import datetime, timedelta
from utils.symbol_validator import symbol_validator
from infrastructure.data.configurable_historical_data_provider import ConfigurableHistoricalDataProvider
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter

class HistoricalDataSyncJob:
    def __init__(self):
        self.data_provider = ConfigurableHistoricalDataProvider()
        self.csv_loader = CSVHistoryLoaderAdapter(base_path="./data/historical_cache")
        
    def sync_approved_symbols(self):
        """Download historical data for all approved symbols"""
        approved_symbols = symbol_validator.get_approved_symbols()
        self.logger.info(f"Starting historical data sync for {len(approved_symbols)} approved symbols")
        
        for symbol in approved_symbols:
            try:
                # Fetch latest 24h of 1m data for each symbol
                historical_data = self.data_provider.get_historical_data(
                    symbol=symbol,
                    period='1d', 
                    timeframe='1m'
                )
                
                if historical_data:
                    # Save to local cache
                    self.csv_loader.save_historical_data(
                        symbol=symbol.value, 
                        data=historical_data, 
                        timeframe='1m'
                    )
                    self.logger.info(f"Successfully synced data for {symbol.value}")
                else:
                    self.logger.warning(f"No data retrieved for {symbol.value}")
                    
            except Exception as e:
                self.logger.error(f"Error syncing {symbol.value}: {e}")
                
    def start_scheduler(self):
        """Start the hourly sync scheduler"""
        schedule.every().hour.do(self.sync_approved_symbols)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
```

### 2. Environment Variable Configuration
The system uses the `CSV_DATA_PATH` environment variable to determine where to store and load historical data:

- **Variable**: `CSV_DATA_PATH`
- **Default**: `./data/history/raw/1m`
- **Usage**: The system automatically reads this environment variable to determine the data storage location
- **Configuration**: Should be set in your `.env` file

The historical data will be stored in the following directory structure based on the environment variable:
```
data/
└── history/
    └── raw/
        └── [timeframe]/
            └── [symbol]/
                └── [timeframe].csv
```

For example:
```
data/
└── history/
    └── raw/
        ├── 1m/
        │   ├── BTCUSDT/
        │   │   └── 1m.csv
        │   └── ETHUSDT/
        │       └── 1m.csv
        ├── 5m/
        │   ├── BTCUSDT/
        │   │   └── 5m.csv
        │   └── ETHUSDT/
        │       └── 5m.csv
        └── 1h/
            ├── BTCUSDT/
            │   └── 1h.csv
            └── ETHUSDT/
                └── 1h.csv
```

### 3. Enhanced Data Provider with Multiple Fallbacks
Implement a robust data provider with the following hierarchy:
1. Local CSV cache (fastest)
2. Online exchange data (fresh)
3. Empty list (no synthetic data - only real data is trusted)

### 3. Data Validation and Quality Checks
Implement data quality validation to ensure downloaded data is usable:

```python
def validate_historical_data(self, data: List[Dict], symbol: str) -> bool:
    """Validate the quality and completeness of historical data"""
    if not data or len(data) < 10:  # Minimum 10 data points
        return False
        
    # Check for required fields
    required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    for point in data[:5]:  # Check first 5 points
        if not all(field in point for field in required_fields):
            return False
            
    # Check for reasonable price relationships
    for point in data:
        if point['high'] < point['low'] or point['high'] < point['close'] or point['low'] > point['close']:
            return False  # Invalid OHLC relationships
            
    return True
```

### 4. Local Data Directory Structure
Organize local data storage efficiently:

```
data/
├── historical_cache/
│   ├── BTCUSDT/
│   │   ├── 1m.csv
│   │   ├── 5m.csv
│   │   └── 1h.csv
│   ├── ETHUSDT/
│   │   ├── 1m.csv
│   │   ├── 5m.csv
│   │   └── 1h.csv
│   └── ...
└── ...
```

### 5. Performance Optimization
- Implement data compression for storage efficiency
- Use memory-mapped files for large datasets
- Cache frequently accessed data in memory

## Implementation Steps

### Phase 1: Infrastructure Setup
1. Create the historical data sync job runner
2. Set up local data directory structure
3. Implement data validation utilities
4. Create backup and recovery mechanisms

### Phase 2: Data Provider Enhancement
1. Modify ConfigurableHistoricalDataProvider to use local cache first
2. Implement fallback chain (local → online → synthetic)
3. Add caching mechanisms and performance optimizations
4. Implement data quality checks

### Phase 3: Scheduled Job Deployment
1. Create hourly cron job/scheduler
2. Implement monitoring and alerting
3. Add logging and metrics collection
4. Set up error handling and recovery

### Phase 4: Testing and Validation
1. Test with various symbol types and market conditions
2. Validate data quality and integrity
3. Measure performance improvements
4. Document the solution

## Expected Outcomes
- **Reduce rejection rate**: From 90%+ to <5% of symbols rejected
- **Improve reliability**: System operates consistently regardless of network issues
- **Enhance performance**: Faster data access from local cache
- **Maintain data freshness**: Hourly updates ensure recent data availability
- **Increase resilience**: System continues operating during exchange outages

## Monitoring and Maintenance
- Monitor data sync success rates
- Track cache hit ratios
- Alert on data quality issues
- Regular cleanup of old cache files
- Backup and disaster recovery procedures

## Future Enhancements
- Real-time data streaming integration
- Machine learning-based data validation
- Cross-exchange data validation
- Predictive caching based on trading patterns
- Data compression and deduplication

This comprehensive solution ensures that the trading system has reliable access to historical data while maintaining performance and resilience against network and exchange issues.