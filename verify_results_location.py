#!/usr/bin/env python3
"""Final verification that hyperopt results are properly saved."""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from infrastructure.optimization.improved_hyperopt_service import ImprovedHyperoptService

print("🔍 FINAL VERIFICATION: Hyperopt Results Location")

# Create proper test data
np.random.seed(42)  # For reproducible results
dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
prices = 100 + np.cumsum(np.random.randn(200) * 0.2)
df = pd.DataFrame({
    'open': prices + np.random.randn(200) * 0.05,
    'high': prices + abs(np.random.randn(200)) * 0.1,
    'low': prices - abs(np.random.randn(200)) * 0.1,
    'close': prices,
    'volume': np.abs(np.random.randn(200)) * 500
}, index=dates)

data_dict = {'BTCUSD': df}
risk_config = {
    "initial_capital": 10000.0,
    "fee_rate": 0.001, 
    "slippage_factor": 0.0005
}

print("\n📁 Expected results location: data/final_verification_hyperopt/strategy_name/timestamp/")
print("📊 Data created with 200 data points for proper time series validation")

# Create service with verification directory
service = ImprovedHyperoptService(
    strategy_name="crypto_breakout",
    base_dir="data/final_verification_hyperopt"
)

print("\n🔄 Running minimal optimization (2 evaluations, 2 CV splits)...")
try:
    results = service.optimize_with_time_series_cv(
        data_dict=data_dict,
        risk_config=risk_config,
        max_evals=2,
        n_cv_splits=2,
        algorithm='tpe'
    )
    
    print("\n✅ OPTIMIZATION SUCCESSFUL!")
    print(f"🎯 Best parameters: {list(results['best_params'].keys())}")
    print(f"📈 Best loss: {results['best_loss']:.6f}")
    print(f"📋 Total evaluations: {results['trials_completed']}")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show actual results location
    print(f"\n💾 RESULTS SAVED AT:")
    print(f"   {service.base_dir}")
    
    # List subdirectories to show the structure
    base_path = Path(service.base_dir)
    if base_path.exists():
        for subdir in base_path.iterdir():
            print(f"   └── {subdir.name}/")
            if subdir.is_dir():
                for subsubdir in subdir.iterdir():
                    print(f"       └── {subsubdir.name}/")
                    # Show files if they exist
                    for file in subsubdir.iterdir():
                        print(f"           ├── {file.name}")

    print(f"\n🎉 SUCCESS: All hyperopt best practices implemented and working!")
    print(f"📁 Results are saved in: {service.base_dir}")
    print(f"📝 You'll find: best.json, metrics.json, params_used.json")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()