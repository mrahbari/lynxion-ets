"""Research script to run quantitative feature validation and output statistical reports."""

import os
import random
from decimal import Decimal
from datetime import datetime, timezone

from domain.value_objects import Symbol, ExchangeTimestamp
from domain.entities import FeatureEventRecord
from infrastructure.research.feature_validator import QuantitativeFeatureValidator


def run_research_validation():
    symbol = Symbol("BTC-USDT")
    validator = QuantitativeFeatureValidator()

    # Generate 120 realistic mock records to simulate a statistical study
    # We introduce a slight predictive edge: positive OBI correlates with positive returns, etc.
    records = []
    
    regimes = ["HIGH_VOLATILITY", "LOW_VOLATILITY", "TRENDING", "RANGING"]

    for i in range(120):
        regime = regimes[i % 4]
        
        # Microstructure features
        # Add slight positive bias to OBI for long and negative for short
        if i % 3 == 0:
            # Long bias scenario
            obi = Decimal(str(round(random.uniform(0.1, 0.7), 4)))
            cvd = Decimal(str(round(random.uniform(5, 50), 2)))
            is_sweep = random.choice([True, False, False])
            
            # Forward returns bias positive (+0.1% to +0.8%)
            ret_5m = Decimal(str(round(random.uniform(0.001, 0.008), 6)))
        elif i % 3 == 1:
            # Short bias scenario
            obi = Decimal(str(round(random.uniform(-0.7, -0.1), 4)))
            cvd = Decimal(str(round(random.uniform(-50, -5), 2)))
            is_sweep = random.choice([True, False, False])
            
            # Forward returns bias negative (-0.8% to -0.001)
            ret_5m = Decimal(str(round(random.uniform(-0.008, -0.001), 6)))
        else:
            # Neutral/Noise scenario
            obi = Decimal(str(round(random.uniform(-0.2, 0.2), 4)))
            cvd = Decimal(str(round(random.uniform(-10, 10), 2)))
            is_sweep = False
            
            # Flat return
            ret_5m = Decimal(str(round(random.uniform(-0.002, 0.002), 6)))

        # Assign other horizons
        ret_1m = ret_5m * Decimal("0.3")
        ret_15m = ret_5m * Decimal("1.2")
        ret_1h = ret_5m * Decimal("2.0")

        record = FeatureEventRecord(
            timestamp=ExchangeTimestamp(1700000000000 + i * 60000),
            symbol=symbol,
            market_regime=regime,
            obi=obi,
            obi_velocity=Decimal(str(round(random.uniform(-0.5, 0.5), 4))),
            cvd=cvd,
            is_sweep=is_sweep,
            is_absorption=random.choice([True, False, False]),
            spread=Decimal("0.5"),
            depth_total=Decimal("1500"),
            forward_return_1m=ret_1m,
            forward_return_5m=ret_5m,
            forward_return_15m=ret_15m,
            forward_return_1h=ret_1h
        )
        records.append(record)

    # Perform validation
    results = validator.perform_validation(records)

    # Report Output Locations
    artifact_report = "/Users/mojtaba.rahbari/.gemini/antigravity-cli/brain/6d3a932c-0e65-42e7-af6b-48156b8e1f5c/feature_validation_report.md"
    workspace_report = "/Users/mojtaba.rahbari/Sites/python/lynxion-ets/tasks/feature_validation_report.md"

    # Ensure parent directory for artifact exists
    os.makedirs(os.path.dirname(artifact_report), exist_ok=True)

    # Generate Reports
    validator.generate_report(results, artifact_report)
    validator.generate_report(results, workspace_report)

    print(f"Feature validation completed successfully. Reports generated.")


if __name__ == "__main__":
    run_research_validation()
