# Quality Assurance (QA) Checklist for Lynx Hedge Fund Trading System

## Pre-Implementation Verification

### 1. Environment Setup
- [ ] Verify Python 3.9+ is installed
- [ ] Confirm all dependencies from `requirements.txt` are installed
- [ ] Create necessary directories (`logs`, `data/cache`, `data/results`, etc.)
- [ ] Copy `.env.example` to `.env` and verify placeholder values are set appropriately

### 2. Configuration Validation
- [ ] Verify `config/hyperopt_autotune_config.json` contains valid configuration
- [ ] Check that all paths in configuration files are accessible
- [ ] Confirm risk management parameters are within reasonable bounds
- [ ] Validate that database connections can be established if applicable

### 3. Data Access
- [ ] Verify access to market data sources (exchanges, APIs)
- [ ] Confirm data caching directories are writable
- [ ] Test historical data retrieval for major symbols (BTC/USDT, ETH/USDT)
- [ ] Check data quality and completeness for recent periods

## Core Functionality Testing

### 4. Backtesting System
- [ ] Run basic backtest: `python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTC/USDT`
- [ ] Verify backtest produces reasonable metrics (sharpe ratio, win rate, drawdown)
- [ ] Test backtest with optimized parameters: `--use-optimized-params`
- [ ] Confirm slippage and fees are applied correctly in backtesting

### 5. Hyperparameter Optimization
- [ ] Run optimization: `python run_trading_system.py --mode optimize --strategy crypto_breakout --symbol BTC/USDT --max-evals 20`
- [ ] Verify optimization completes without errors
- [ ] Check that results are stored properly
- [ ] Confirm that optimization respects risk constraints
- [ ] Test with different strategy types

### 6. Auto-Retune System
- [ ] Run auto-retune: `python run_trading_system.py --mode retune --strategy crypto_breakout --symbols BTC/USDT,ETH/USDT`
- [ ] Verify retune process completes for all specified symbols
- [ ] Check that optimized parameters are saved and accessible
- [ ] Confirm retune respects performance thresholds

### 7. Live Trading Simulation (Demo Mode)
- [ ] Run production mode with demo trading: `python run_trading_system.py --mode production --demo-mode --strategy crypto_breakout --symbol BTC/USDT`
- [ ] Verify demo mode executes without actual order placement
- [ ] Check that risk management is enforced in demo mode
- [ ] Monitor that trade execution logic functions correctly

## Auto-Detection System Testing

### 8. Auto-Detection Feature
- [ ] Run auto-detection with specific symbols: `python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT,ETH/USDT`
- [ ] Verify the system starts monitoring the specified symbols
- [ ] Confirm watcher components are initialized and running (MarketPulse, Volatility, TrendMTF, AnomalyML, OrderFlow, CMC)
- [ ] Check that opportunity detection is functioning
- [ ] Verify that appropriate strategies are selected based on detected opportunities
- [ ] Monitor for proper risk management during auto-detection
- [ ] Confirm CMC watcher integration is active and processing market data
- [ ] Verify CMC-based symbol discovery works when no symbols are specified

### 9. Dynamic Symbol Discovery
- [ ] Test auto-detection without specifying symbols: `python run_trading_system.py --mode production --auto-detect`
- [ ] Verify the system automatically discovers and monitors symbols
- [ ] Confirm the auto-discovered symbol list is reasonable and includes major trading pairs
- [ ] Check that monitoring continues with dynamically discovered symbols
- [ ] Verify opportunity detection works with auto-discovered symbols
- [ ] Test CMC-based symbol screening for high-growth potential coins
- [ ] Verify CMC crash-risk detection identifies volatile assets
- [ ] Confirm excluded coins (BTC, ETH, etc.) are properly filtered from discovery
- [ ] Test CMC API fallback to default symbols when API unavailable

### 10. Auto-Detection System Integration
- [ ] Confirm auto-detection mode preserves manual execution capability
- [ ] Verify the system can switch between auto-detect and manual modes
- [ ] Check that risk management works in auto-detection mode
- [ ] Validate that background services (monitoring, retuning) function properly in auto-detection mode

## Risk Management & Safety

### 11. CMC Integration & Configuration
- [ ] Verify CMC_API_KEY is properly configured in environment
- [ ] Test CMC data retrieval for major coins (BTC, ETH, etc.)
- [ ] Confirm CMC growth potential detection identifies coins with high momentum
- [ ] Verify CMC crash-risk detection flags volatile assets
- [ ] Test CMC market sentiment analysis for overall market direction
- [ ] Check that CMC stablecoin filtering works correctly
- [ ] Verify CMC excluded coins list is properly applied

### 12. Risk Controls
- [ ] Verify maximum drawdown threshold is enforced
- [ ] Check leverage limits are respected
- [ ] Confirm position size constraints are applied
- [ ] Test that risk alerts are generated when thresholds are exceeded
- [ ] Verify stop-loss and take-profit logic functions correctly

### 13. Emergency Controls
- [ ] Test emergency stop functionality
- [ ] Verify order cancellation works properly
- [ ] Confirm position liquidation functionality
- [ ] Check that the system can be safely stopped and restarted

### 14. Error Handling
- [ ] Test system behavior with invalid symbol names
- [ ] Check handling of data access failures
- [ ] Verify system recovery from temporary network issues
- [ ] Confirm graceful degradation when market data is unavailable

## Performance & Monitoring

### 15. System Performance
- [ ] Monitor CPU and memory usage during auto-detection mode
- [ ] Check system responsiveness during heavy monitoring
- [ ] Verify that background threads don't interfere with main operations
- [ ] Confirm stable performance during extended runs (24+ hours)

### 16. Dashboard & Monitoring
- [ ] Start monitoring dashboard: `python run_dashboard.py --port 8050`
- [ ] Verify dashboard displays real-time metrics
- [ ] Check that performance metrics update correctly
- [ ] Confirm risk exposure displays are accurate
- [ ] Test API endpoints for metrics access

## Integration & End-to-End Tests

### 17. Full Workflow Testing (Watcher → Engine → Fusion → Strategy → Broker)
- [ ] Run complete workflow with auto-detection: `python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT`
- [ ] Verify each component in the workflow processes data correctly
- [ ] Check that signals flow from watchers to engines to fusion to strategies to broker interface
- [ ] Confirm the orchestrated workflow operates as expected

### 18. Multi-Symbol Testing
- [ ] Test with multiple symbols: `python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT,ETH/USDT,SOL/USDT`
- [ ] Verify all symbols are monitored simultaneously
- [ ] Check that opportunities are detected across all symbols
- [ ] Confirm risk allocation works across multiple symbols

## Final Verification

### 19. System Health Check
- [ ] Run comprehensive health check
- [ ] Verify all required services are running
- [ ] Confirm no memory leaks during extended operation
- [ ] Check log files for errors or warnings

### 20. Configuration Consistency
- [ ] Verify all configurations are consistent across environments
- [ ] Confirm risk parameters are appropriate for production use
- [ ] Check that any demo-specific settings are properly configured

### 21. Documentation Verification
- [ ] Confirm README.md accurately reflects current functionality
- [ ] Verify all command-line options are documented
- [ ] Check that auto-detection features are properly documented
- [ ] Ensure usage examples are current and functional

## Expected Outcomes

- [ ] Auto-detection system runs continuously without errors
- [ ] Market opportunities are detected and appropriate strategies are selected automatically
- [ ] Dynamic symbol discovery identifies relevant trading pairs
- [ ] All risk management controls function properly in auto-detection mode
- [ ] Manual execution capability remains available and functional
- [ ] System performance remains stable during auto-detection operations
- [ ] CMC integration provides valuable market intelligence and symbol discovery

## Sign-off

- [ ] All QA checklist items have been verified
- [ ] Test results documented
- [ ] System ready for production deployment (if applicable)
- [ ] Emergency procedures confirmed and accessible