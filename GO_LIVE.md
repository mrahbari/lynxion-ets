# Go Live Guide: Preparing Lynxion ETS for Live Trading

This document provides a comprehensive guide to prepare your Lynxion ETS system for live trading operations, from initial setup to ongoing monitoring.

## Table of Contents
- [System Readiness Checklist](#system-readiness-checklist)
- [Pre-Live Preparation Steps](#pre-live-preparation-steps)
- [Environment Configuration](#environment-configuration)
- [Risk Management Setup](#risk-management-setup)
- [Live System Deployment](#live-system-deployment)
- [Monitoring & Alerting](#monitoring--alerting)
- [Emergency Procedures](#emergency-procedures)
- [Ongoing Operations](#ongoing-operations)
- [Compliance Considerations](#compliance-considerations)

## System Readiness Checklist

### ✅ **Before Going Live - Critical Items**
- [ ] **Complete backtesting** with 2+ years of historical data
- [ ] **Walk-forward analysis** validation across multiple market conditions
- [ ] **Parameter stability** testing (ensure parameters don't change drastically)
- [ ] **Risk management** rules properly configured and tested
- [ ] **Exchange API keys** properly configured for live trading
- [ ] **Capital allocation** rules established and tested
- [ ] **Emergency stop** procedures in place
- [ ] **Backup and recovery** procedures tested
- [ ] **Monitoring systems** operational with alerting
- [ ] **Performance tracking** and reporting configured

## Pre-Live Preparation Steps

### 1. **Historical Validation**
```bash
# Run comprehensive backtesting with optimized parameters
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --start 2022-01-01 --end today --optimized --report --plot

# Perform walk-forward analysis to validate strategy robustness
python runner_walkforward.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --train-days 90 --test-days 30 --evals 50

# Validate retuning stability across time periods
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --evals 100 --days 180 --validate
```

### 2. **Data Quality Verification**
```bash
# Ensure complete historical data coverage
python runner_resync.py --all

# Verify data integrity and gap detection
python runner_history_download.py --start 365d --end today --validate
```

### 3. **Paper Trading Phase** (Recommended)
- Run the system in paper trading mode for 1-2 months
- Compare paper trading results with backtesting results
- Monitor for any discrepancies or issues

## Environment Configuration

### 1. **Exchange Configuration**
```bash
# In .env file, configure live trading settings:
LIVE_TRADING_ENABLED=true
EXCHANGE_API_KEY=your_live_exchange_api_key
EXCHANGE_SECRET_KEY=your_live_exchange_secret_key
EXCHANGE_TESTNET=false  # Set to false for live trading
```

### 2. **Capital Management**
```bash
# Risk per trade configuration
RISK_PER_TRADE=0.02  # 2% per trade maximum
MAX_POSITION_SIZE=0.20  # 20% max per position
MAX_TOTAL_EXPOSURE=0.80  # 80% max total exposure
INITIAL_CAPITAL=50000.0  # Starting capital amount
```

### 3. **WFO Configuration for Live Trading**
```bash
# Adjust for live trading
WFO_COINS=BTCUSDT,ETHUSDT  # Start with 2-3 major pairs
WFO_TRAIN_SIZE=180  # 6-month training window
WFO_TEST_SIZE=30  # 1-month testing window
WFO_RETRAIN_FREQUENCY_DAYS=7  # Weekly re-optimization
WFO_MAX_EVALS=50  # Balanced optimization
```

## Risk Management Setup

### 1. **Critical Risk Controls**
```bash
# In .env file:
RISK_MAX_DRAWDOWN=0.15  # 15% maximum drawdown
RISK_MAX_POSITION_SIZE=0.20  # 20% max per trade
RISK_MAX_TOTAL_EXPOSURE=0.80  # 80% max total exposure
RISK_MAX_DAILY_LOSS=0.02  # 2% max daily loss
RISK_MAX_LEVERAGE=1.0  # No leverage for conservative trading
SAFETY_EMERGENCY_STOP_ENABLED=true
SAFETY_KILL_SWITCH_ENABLED=true
SAFETY_MAX_ORDER_SIZE_USD=10000  # Max order size limit
```

### 2. **Emergency Stop Configuration**
```bash
# Circuit breaker settings
RISK_EMERGENCY_STOP_DRAWDOWN=0.10  # Emergency stop at 10% drawdown
RISK_CAPITAL_PER_SYMBOL=0.05  # 5% max per symbol
MAX_CORRELATION_BETWEEN_POS=0.7  # Max correlation between positions
```

### 3. **Performance Thresholds**
```bash
WFO_PERFORMANCE_THRESHOLD=0.1  # Minimum Sharpe ratio
WFO_MAX_DRAWDOWN_THRESHOLD=0.15  # Maximum acceptable drawdown
WFO_PASS_RATE_THRESHOLD=0.60  # Minimum pass rate across WFO windows
```

## Live System Deployment

### 1. **Daily Operations Setup**

#### **Step 1: Morning Data Sync**
```bash
# Run at 00:00 UTC daily
python runner_resync.py --download --timeframes
```

#### **Step 2: Parameter Optimization Check**
```bash
# Run every 7 days (or based on WFO_RETRAIN_FREQUENCY_DAYS)
python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --evals 50 --days 90
```

#### **Step 3: Live Trading Execution**
```bash
# Main trading system execution
python run_trading_system.py --live
```

### 2. **System Startup Sequence**
```bash
# 1. Verify system dependencies
source venv/bin/activate

# 2. Check environment configuration
python -c "import os; print('LIVE_TRADING_ENABLED:', os.getenv('LIVE_TRADING_ENABLED'))"

# 3. Validate API connections
python -c "from infrastructure.brokers.binance_broker import BinanceBroker; broker = BinanceBroker(); print('API Connection:', broker.test_connection())"

# 4. Run comprehensive system check
python runner_resync.py --all  # Full data sync

# 5. Start live trading system
python run_trading_system.py
```

### 3. **Automated Scheduling (Cron Examples)**

Add to crontab for automated execution:

```bash
# Daily data sync at 12:05 AM UTC
5 0 * * * cd /path/to/lynxion-ets && source venv/bin/activate && python runner_resync.py --download --timeframes >> /var/log/trading_system.log 2>&1

# Weekly parameter re-optimization on Sundays at 2:00 AM UTC
0 2 * * 0 cd /path/to/lynxion-ets && source venv/bin/activate && python runner_retune.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --evals 25 --days 90 >> /var/log/retune.log 2>&1

# Hourly health checks
0 * * * * cd /path/to/lynxion-ets && source venv/bin/activate && python -c "import json; from datetime import datetime; open('/tmp/trading_heartbeat', 'w').write(json.dumps({'timestamp': datetime.utcnow().isoformat(), 'status': 'running'}))" >> /var/log/heartbeat.log 2>&1
```

## Monitoring & Alerting

### 1. **Critical Metrics to Monitor**
- Portfolio drawdown (should not exceed 15%)
- Daily P&L (monitor for unusual swings)
- Position sizes vs. limits
- Trading frequency vs. expected range
- API rate limits and connection status

### 2. **Alert Configuration**
```bash
# Telegram notifications
NOTIFICATION_TELEGRAM_ALERTS=true
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email notifications
NOTIFICATION_EMAIL_ALERTS=true
SMTP_SERVER=your_smtp_server
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
```

### 3. **Monitoring Scripts**

Create monitoring scripts for regular checks:

**trading_monitor.py:**
```python
import json
import smtplib
from datetime import datetime, timedelta
import os

def check_system_health():
    # Check heartbeat file
    try:
        with open('/tmp/trading_heartbeat', 'r') as f:
            heartbeat = json.load(f)
        
        last_heartbeat = datetime.fromisoformat(heartbeat['timestamp'])
        if datetime.utcnow() - last_heartbeat > timedelta(minutes=30):
            send_alert("Trading system appears to be down!")
            return False
    except:
        send_alert("Cannot read heartbeat file!")
        return False
    
    return True

def send_alert(message):
    # Send alerts via configured channels
    # Implementation depends on your notification setup
    pass
```

## Emergency Procedures

### 1. **Immediate Response Actions**

#### **Scenario: Excessive Drawdown**
1. **Immediate**: Execute emergency stop - set `SAFETY_KILL_SWITCH_ENABLED=true` in env
2. **Check**: Review last 10 trades and their outcomes
3. **Analyze**: Run diagnostics to identify the cause
4. **Correct**: Adjust parameters or pause trading if needed
5. **Resume**: Only after confirming system stability

#### **Scenario: API Connection Issues**
1. **Check**: Verify API keys and permissions
2. **Retry**: Wait for rate limit reset
3. **Fallback**: Monitor for manual intervention if needed
4. **Resume**: Automatic recovery when connection restored

#### **Scenario: System Crash**
1. **Diagnose**: Check log files for error details
2. **Restore**: Restart system with appropriate parameters
3. **Validate**: Confirm data integrity and position status
4. **Monitor**: Closely observe for first 24 hours after restart

### 2. **Kill Switch Procedures**
```bash
# To immediately stop all trading:
echo "SAFETY_KILL_SWITCH_ENABLED=true" >> .env
# Then restart the trading system
```

## Ongoing Operations

### 1. **Weekly Maintenance**
```bash
# Monday morning: Review weekly performance
python runner_backtest.py --strategy crypto_breakout --symbols BTCUSDT ETHUSDT --start 7d --end today --report

# Wednesday: Verify data integrity
python runner_history_download.py --start 30d --end today --validate

# Friday: Prepare weekly summary
# Generate performance reports and review parameter stability
```

### 2. **Monthly Review**
- **Performance Analysis**: Compare live results with backtesting
- **Parameter Stability**: Review if optimization parameters remain stable
- **Risk Assessment**: Check maximum drawdown and risk metrics
- **Capacity Planning**: Assess if current infrastructure handles trading volume
- **Strategy Evolution**: Plan for potential strategy updates

### 3. **Quarterly Updates**
- **System Updates**: Update dependencies and security patches
- **Strategy Review**: Comprehensive strategy performance review
- **Risk Controls**: Update risk parameters based on performance data
- **Capacity Planning**: Scale infrastructure if needed

## Compliance Considerations

### 1. **Regulatory Compliance**
- **Tax Reporting**: Maintain accurate records for tax purposes
- **Transaction Logs**: Keep detailed transaction history
- **Audit Trail**: Ensure all trades can be traced and verified

### 2. **Security Measures**
```bash
# Secure API keys
export EXCHANGE_API_KEY="your_key_here"  # Never commit to version control

# Limit API permissions to trading only
# Do not enable withdrawal permissions for live trading system

# Regular security audits
# Keep system dependencies updated
pip install --upgrade -r requirements.txt
```

### 3. **Backup Strategy**
```bash
# Daily backup of critical data
# - Trading results
# - Optimization parameters
# - Configuration files
# - Transaction logs

# Backup location should be secure and separate from primary system
```

## Final Go-Live Checklist

### ✅ **Day of Launch**
- [ ] All environment variables properly configured for LIVE trading
- [ ] API keys tested and confirmed working
- [ ] Risk controls properly enabled and limits set
- [ ] Monitoring system operational with alerting configured
- [ ] Backup procedures tested and confirmed
- [ ] Emergency procedures documented and accessible
- [ ] Capital allocation rules confirmed
- [ ] Trading system tested in isolated environment
- [ ] Log file locations and retention configured
- [ ] Notification systems tested

### 🚀 **Launch Command**
```bash
# Final verification before launch
python -c "import os; print('LIVE TRADING:', os.getenv('LIVE_TRADING_ENABLED', 'false')); print('EXCHANGE TESTNET:', os.getenv('EXCHANGE_TESTNET', 'true'))"

# Start live trading
python run_trading_system.py --live --config production_config.json
```

## Important Disclaimers

> ⚠️ **WARNING**: Live trading involves substantial financial risk. Never risk more than you can afford to lose.
> 
> 📊 **Performance Past Performance**: Historical backtesting results do not guarantee future performance.
> 
> 🔒 **Security**: Never share API keys or sensitive configuration details.
> 
> 📈 **Risk Management**: Always use appropriate risk management controls and position sizing.

---

**Success Factor**: Start with a small capital allocation and gradually increase as you validate the system's performance in live market conditions. Monitor closely during the first 30 days of live trading.