"""Research script to run quantitative walk-forward feature validation and generate alpha qualification reports."""

import os
import random
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities import FeatureEventRecord
from infrastructure.research.walk_forward_engine import WalkForwardEvaluationEngine


def generate_mock_dataset(symbol: Symbol, days: int) -> list:
    """Generate mock feature event records spanning a specific number of days with statistical edge."""
    records = []
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    
    # Slight differences per asset to simulate asset-dependency
    multiplier = Decimal("1.0")
    if "ETH" in symbol.value:
        multiplier = Decimal("0.95")
    elif "SOL" in symbol.value:
        multiplier = Decimal("0.80")
        
    for i in range(days):
        record_dt = base_time + timedelta(days=i)
        
        # Alternate signal directions with predictive return correlation
        if i % 3 == 0:
            # Long signal scenario
            obi = Decimal(str(round(random.uniform(0.2, 0.8), 4))) * multiplier
            cvd = Decimal(str(round(random.uniform(10, 60), 2))) * multiplier
            is_sweep = random.choice([True, False, False])
            is_absorption = random.choice([False, False, True])
            ret_5m = Decimal(str(round(random.uniform(0.002, 0.010), 6)))
        elif i % 3 == 1:
            # Short signal scenario
            obi = Decimal(str(round(random.uniform(-0.8, -0.2), 4))) * multiplier
            cvd = Decimal(str(round(random.uniform(-60, -10), 2))) * multiplier
            is_sweep = random.choice([True, False, False])
            is_absorption = random.choice([False, False, True])
            ret_5m = Decimal(str(round(random.uniform(-0.010, -0.002), 6)))
        else:
            # Noise/Flat scenario
            obi = Decimal(str(round(random.uniform(-0.15, 0.15), 4))) * multiplier
            cvd = Decimal(str(round(random.uniform(-8, 8), 2))) * multiplier
            is_sweep = False
            is_absorption = False
            ret_5m = Decimal(str(round(random.uniform(-0.002, 0.002), 6)))
            
        ret_1m = ret_5m * Decimal("0.3")
        ret_15m = ret_5m * Decimal("1.2")
        ret_1h = ret_5m * Decimal("2.0")

        record = FeatureEventRecord(
            timestamp=ExchangeTimestamp(int(record_dt.timestamp() * 1000)),
            symbol=symbol,
            market_regime="RANGING" if i % 2 == 0 else "TRENDING",
            obi=obi,
            obi_velocity=Decimal(str(round(random.uniform(-0.5, 0.5), 4))),
            cvd=cvd,
            is_sweep=is_sweep,
            is_absorption=is_absorption,
            spread=Decimal("0.5"),
            depth_total=Decimal("1200"),
            forward_return_1m=ret_1m,
            forward_return_5m=ret_5m,
            forward_return_15m=ret_15m,
            forward_return_1h=ret_1h
        )
        records.append(record)
        
    return records


def run_research_walkforward():
    print("🚀 Running Walk-Forward Feature Validation...")
    
    btc_symbol = Symbol("BTC-USDT")
    eth_symbol = Symbol("ETH-USDT")
    sol_symbol = Symbol("SOL-USDT")
    
    # 150 days of mock records
    symbol_records = {
        btc_symbol: generate_mock_dataset(btc_symbol, 150),
        eth_symbol: generate_mock_dataset(eth_symbol, 150),
        sol_symbol: generate_mock_dataset(sol_symbol, 150)
    }

    # Initialize evaluation engine
    engine = WalkForwardEvaluationEngine(
        train_days=90,
        validation_days=30,
        step_days=30
    )

    # 1. Run out-of-sample walk-forward feature evaluation
    print("📊 Evaluating rolling folds and calculating cross-asset consistency...")
    session = engine.evaluate_walk_forward(symbol_records)

    # 2. Run timeframe validation and cost-adjusted edge calculation
    print("💰 Computing timeframe and transaction cost adjusted returns...")
    all_recs = []
    for recs in symbol_records.values():
        all_recs.extend(recs)
    costs = engine.calculate_cost_adjusted_edges(all_recs)

    # 3. Report Output Locations
    artifact_report = "/Users/mojtaba.rahbari/.gemini/antigravity-cli/brain/5c947f62-0d0b-4ed9-aa15-0663f7730a14/alpha_qualification_report.md"
    workspace_report = "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/tasks/alpha_qualification_report.md"

    # Ensure parent directories exist
    os.makedirs(os.path.dirname(artifact_report), exist_ok=True)
    os.makedirs(os.path.dirname(workspace_report), exist_ok=True)

    # 4. Generate Reports
    print(f"📝 Writing reports to:\n   - {workspace_report}\n   - {artifact_report}")
    engine.generate_qualification_report(session, costs, artifact_report)
    engine.generate_qualification_report(session, costs, workspace_report)

    print("\n✅ Walk-Forward Alpha Qualification successfully finished!")


if __name__ == "__main__":
    run_research_walkforward()
