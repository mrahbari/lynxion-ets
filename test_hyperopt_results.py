#!/usr/bin/env python3
"""Quick test to verify hyperopt results are saved properly."""

import pandas as pd
import numpy as np
from datetime import datetime
from infrastructure.optimization.improved_hyperopt_service import ImprovedHyperoptService

# Create simple test data with more points for time series splitting
dates = pd.date_range(start='2023-01-01', periods=150, freq='D')
prices = 100 + np.cumsum(np.random.randn(150) * 0.5)
df = pd.DataFrame({
    'open': prices + np.random.randn(150) * 0.1,
    'high': prices + abs(np.random.randn(150)) * 0.2,
    'low': prices - abs(np.random.randn(150)) * 0.2,
    'close': prices,
    'volume': np.abs(np.random.randn(150)) * 1000
}, index=dates)

data_dict = {'BTCUSD': df}
risk_config = {
    "initial_capital": 10000.0,
    "fee_rate": 0.001, 
    "slippage_factor": 0.0005,
    "max_drawdown_threshold": -0.15
}

print("Running quick hyperopt test...")

# Create service with specific directory
service = ImprovedHyperoptService(
    strategy_name="crypto_breakout",
    base_dir="data/test_hyperopt_results"
)

# Run a minimal optimization
try:
    results = service.optimize_with_time_series_cv(
        data_dict=data_dict,
        risk_config=risk_config,
        max_evals=2,  # Just 2 evaluations for quick test
        n_cv_splits=2,  # 2 splits to keep it fast
        algorithm='tpe'
    )
    print("✅ Optimization completed successfully!")
    print(f"Best parameters: {results['best_params']}")
    print(f"Best loss: {results['best_loss']}")
    
    import os
    print(f"✅ Files saved in: {service.base_dir}")
    for root, dirs, files in os.walk(service.base_dir):
        level = root.replace(service.base_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()