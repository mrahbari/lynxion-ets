# Forensic Governance Implementation

## Overview
The forensic governance system implements PRE-FORENSIC and FORENSIC requirements for the enterprise hedge fund trading system. It ensures that all trading decisions meet statistical and causal defensibility standards before capital deployment.

## Components

### 1. Decision Gate Controller (`decision_gate_controller.py`)
- Evaluates decisions against statistical requirements
- Blocks decisions with insufficient evidence
- Applies approval multipliers based on statistical validity
- Supports all system layers (Watcher, Engine, Fusion, Strategy, Broker)

### 2. Trade Classifier (`trade_classifier.py`)
- Classifies trades as SCIENTIFIC, PROBATIONARY, or RANDOM
- Uses multiple statistical and forensic criteria
- Provides detailed classification reasons

### 3. Forensic Attribution Model (`forensic_attribution_model.py`)
- Attributes gains/losses to specific system components
- Performs counterfactual analysis
- Calculates regret metrics
- Supports root cause analysis

### 4. Forensic Governance Layer (`forensic_governance_layer_separate.py`)
- Orchestration layer for all forensic controls
- Provides governance methods for each system layer
- Separated to avoid circular imports

## Key Features

### Statistical Validation Gates
- Minimum sample size requirements (default: 30)
- Statistical significance testing (p < 0.05)
- Authority score thresholds (minimum: 0.7)
- Contributor diversity validation

### Automatic Rejection System
- Blocks decisions with insufficient statistical evidence
- Rejects decisions with high randomness exposure
- Prevents execution of non-defensible decisions
- Enforces maturity requirements

### Trade Classification System
- **SCIENTIFIC**: Statistically proven, full capital allocation
- **PROBATIONARY**: Limited evidence, restricted capital (10%)
- **RANDOM**: Insufficient evidence, blocked from capital

### Evidence Accumulation Requirements
- Historical performance validation
- Out-of-sample testing requirements
- Risk-adjusted return thresholds
- Drawdown limitations

## Integration Points

### Enhanced Forensic Logger
The forensic logger now incorporates governance controls:
- Evaluates each decision against statistical requirements
- Blocks logging of non-compliant decisions
- Adds governance metadata to log entries
- Maintains historical records for learning

### Layer-by-Layer Governance
Each system layer now has governance enforcement:
- **Watcher**: Validates market observations
- **Engine**: Validates signal interpretations
- **Fusion**: Validates signal combinations
- **Strategy**: Validates strategy selections
- **Broker**: Validates execution decisions

## Usage

### Running with Forensic Governance
```bash
# Enable forensic logging
export FORENSIC_LOGGING_ENABLED=true

# Run the system with governance
python run_trading_system.py --mode production --auto-detect --comprehensive-logs
```

### Analyzing Forensic Logs
```bash
# Generate forensic analysis report
python analyze_forensic_logs.py
```

## Configuration
The system uses the following default thresholds:
- Minimum sample size: 30
- Statistical significance: p < 0.05
- Authority score threshold: 0.7
- Defensibility threshold: 0.7
- Maximum contributor correlation: 0.7

These can be adjusted in the `DecisionGateController` class.

## Compliance
This implementation ensures compliance with institutional requirements:
- Statistical defensibility for all decisions
- Complete audit trail with causal chains
- Evidence-based capital allocation
- Regulatory and investor audit readiness