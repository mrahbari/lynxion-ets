"""Unit tests for the Walk Forward Alpha Qualification Framework (Milestone 5)."""

import pytest
import os
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from domain.value_objects import Symbol, Side, ExchangeTimestamp
from domain.entities import FeatureEventRecord, WalkForwardFold, AlphaQualificationSession
from infrastructure.research.walk_forward_engine import WalkForwardEvaluationEngine


@pytest.fixture
def btc_symbol():
    return Symbol("BTC-USDT")


@pytest.fixture
def generate_span_records(btc_symbol):
    """Generate mock feature event records spanning a specific number of days."""
    def _create(days: int) -> list:
        records = []
        base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(days):
            record_dt = base_time + timedelta(days=i)
            # Alternate positive and negative OBI with return correlation
            obi = Decimal("0.5") if i % 2 == 0 else Decimal("-0.5")
            ret = Decimal("0.02") if i % 2 == 0 else Decimal("-0.01")
            
            record = FeatureEventRecord(
                timestamp=ExchangeTimestamp(int(record_dt.timestamp() * 1000)),
                symbol=btc_symbol,
                market_regime="RANGING",
                obi=obi,
                obi_velocity=Decimal("0"),
                cvd=Decimal("10") if i % 2 == 0 else Decimal("-10"),
                is_sweep=False,
                is_absorption=False,
                spread=Decimal("1.0"),
                depth_total=Decimal("1000"),
                forward_return_1m=ret * Decimal("0.3"),
                forward_return_5m=ret,
                forward_return_15m=ret * Decimal("1.2"),
                forward_return_1h=ret * Decimal("2.0")
            )
            records.append(record)
        return records
    return _create


@pytest.mark.unit
def test_walk_forward_fold_generation_no_overlap(generate_span_records):
    """Verify train/validation windows are correct and have no lookahead overlap (leakage)."""
    # 160 days of records
    records = generate_span_records(160)
    engine = WalkForwardEvaluationEngine(train_days=90, validation_days=30, step_days=30)
    
    boundaries = engine.generate_folds(records)
    
    # 160 days total:
    # Fold 0: Train [0, 90], Val (90, 120] -> Val ends day 120. (Valid: 120 <= 160)
    # Fold 1: Train [30, 120], Val (120, 150] -> Val ends day 150. (Valid: 150 <= 160)
    # Fold 2: Train [60, 150], Val (150, 180] -> Val ends day 180 > 160 (Invalid, skipped)
    assert len(boundaries) == 2
    
    for idx, (t_start, t_end, v_start, v_end) in enumerate(boundaries):
        # Validation window starts exactly when training ends
        assert t_end == v_start
        # Train window size is 90 days
        assert (t_end - t_start).days == 90
        # Validation window size is 30 days
        assert (v_end - v_start).days == 30
        # No overlap between training and validation
        assert t_start < t_end <= v_start < v_end


@pytest.mark.unit
def test_walk_forward_cost_adjusted_edge(btc_symbol):
    """Verify that transaction fee, spread, and slippage are correctly deducted from returns."""
    # Maker: 0.0002, Taker: 0.0005, Spread: 0.0001, Slippage: 0.0001
    # Total Cost = 0.0009
    engine = WalkForwardEvaluationEngine(
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0005"),
        flat_spread=Decimal("0.0001"),
        flat_slippage=Decimal("0.0001")
    )
    
    # Gross edge average is 0.02
    records = [
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(100), symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("0.5"), obi_velocity=Decimal("0"), cvd=Decimal("10"), is_sweep=False, is_absorption=False,
            spread=Decimal("1.0"), depth_total=Decimal("1000"),
            forward_return_1m=Decimal("0.01"), forward_return_5m=Decimal("0.02"),
            forward_return_15m=Decimal("0.03"), forward_return_1h=Decimal("0.04")
        )
    ]
    
    costs = engine.calculate_cost_adjusted_edges(records)
    
    total_expected_cost = Decimal("0.0009")
    
    # 5m horizon edge
    assert costs["5m"]["gross_edge"] == Decimal("0.02")
    assert costs["5m"]["execution_cost"] == total_expected_cost
    assert costs["5m"]["net_edge"] == Decimal("0.02") - total_expected_cost


@pytest.mark.unit
def test_walk_forward_evaluation_reproducible(btc_symbol, generate_span_records):
    """Verify walk-forward splits and evaluation outputs are reproducible across runs."""
    records = generate_span_records(150)
    engine = WalkForwardEvaluationEngine(train_days=90, validation_days=30, step_days=30)
    
    session_a = engine.evaluate_walk_forward({btc_symbol: records})
    session_b = engine.evaluate_walk_forward({btc_symbol: records})
    
    assert session_a.stability_score == session_b.stability_score
    assert len(session_a.folds) == len(session_b.folds)
    assert session_a.validated_features == session_b.validated_features
    assert session_a.rejected_features == session_b.rejected_features


@pytest.mark.unit
def test_qualification_report_writes_file(btc_symbol, generate_span_records, tmp_path):
    """Verify that report generation correctly formats and saves the markdown report."""
    records = generate_span_records(160)
    engine = WalkForwardEvaluationEngine(train_days=90, validation_days=30, step_days=30)
    
    session = engine.evaluate_walk_forward({btc_symbol: records})
    costs = engine.calculate_cost_adjusted_edges(records)
    
    report_file = os.path.join(tmp_path, "alpha_qualification_report.md")
    engine.generate_qualification_report(session, costs, report_file)
    
    assert os.path.exists(report_file)
    with open(report_file, "r") as f:
        content = f.read()
        
    assert "Walk-Forward Rolling Folds Summary" in content
    assert "Average Net Edge" in content
    assert "Alpha Qualification Summary" in content


@pytest.mark.unit
def test_walk_forward_out_of_sample_isolation_and_no_leakage(btc_symbol, generate_span_records):
    """Verify that validation period data has zero leakage into training statistics or thresholds."""
    records = generate_span_records(150)
    engine = WalkForwardEvaluationEngine(train_days=90, validation_days=30, step_days=30)
    
    # Run once normally
    session_normal = engine.evaluate_walk_forward({btc_symbol: records})
    normal_fold = session_normal.folds[0]
    
    # Create altered records where the validation period has completely different OBI values
    # (specifically the records in the validation window for fold 0, which is days 91 to 120)
    altered_records = []
    for i, r in enumerate(records):
        if 91 <= i < 120:
            # Modify the OBI of the validation record
            r_altered = FeatureEventRecord(
                timestamp=r.timestamp, symbol=r.symbol, market_regime=r.market_regime,
                obi=Decimal("999.0"),  # Extreme value
                obi_velocity=r.obi_velocity, cvd=r.cvd, is_sweep=r.is_sweep, is_absorption=r.is_absorption,
                spread=r.spread, depth_total=r.depth_total,
                forward_return_1m=r.forward_return_1m, forward_return_5m=r.forward_return_5m,
                forward_return_15m=r.forward_return_15m, forward_return_1h=r.forward_return_1h
            )
            altered_records.append(r_altered)
        else:
            altered_records.append(r)
            
    session_altered = engine.evaluate_walk_forward({btc_symbol: altered_records})
    altered_fold = session_altered.folds[0]
    
    # Assert training statistics are exactly identical (no leakage from validation to training)
    normal_train_stats = normal_fold.train_stats[btc_symbol.value].feature_stats["obi"]
    altered_train_stats = altered_fold.train_stats[btc_symbol.value].feature_stats["obi"]
    
    for metric in ["mean", "std", "median", "min", "max", "p25", "p75", "ic", "hit_rate"]:
        assert normal_train_stats[metric] == altered_train_stats[metric]
        
    # Assert that the validation statistics are different (proving validation data is isolated/used correctly)
    normal_val_stats = normal_fold.val_stats[btc_symbol.value].feature_stats["obi"]
    altered_val_stats = altered_fold.val_stats[btc_symbol.value].feature_stats["obi"]
    assert normal_val_stats["mean"] != altered_val_stats["mean"]


@pytest.mark.unit
def test_walk_forward_no_recalibration(btc_symbol):
    """Verify that validation period uses training-calibrated thresholds without recalibrating."""
    engine = WalkForwardEvaluationEngine(train_days=10, validation_days=10, step_days=10)
    
    # Create custom records where:
    # Train OBI values are around 10.0 (mean=9.5) => thresholds at mean +/- 0.5*std
    train_records = []
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(11):
        record_dt = base_time + timedelta(days=i)
        train_records.append(FeatureEventRecord(
            timestamp=ExchangeTimestamp(int(record_dt.timestamp() * 1000)),
            symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("10.0") if i % 2 == 0 else Decimal("9.0"),
            obi_velocity=Decimal("0"), cvd=Decimal("0"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("0.01"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        ))
        
    val_records = []
    for i in range(10):
        record_dt = base_time + timedelta(days=11 + i)
        val_records.append(FeatureEventRecord(
            timestamp=ExchangeTimestamp(int(record_dt.timestamp() * 1000)),
            symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("0.0"),  # Way below training thresholds (around 9 to 10)
            obi_velocity=Decimal("0"), cvd=Decimal("0"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("0.01"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        ))
        
    session = engine.evaluate_walk_forward({btc_symbol: train_records + val_records})
    fold = session.folds[0]
    
    train_stats = fold.train_stats[btc_symbol.value].feature_stats["obi"]
    val_stats = fold.val_stats[btc_symbol.value].feature_stats["obi"]
    
    # Training should have signals because OBI alternates around thresholds
    assert train_stats["hit_rate"] > 0
    # Validation should have 0 hit rate because no signals were generated (OBI is 0.0, never exceeds calibrated threshold)
    # This proves validation used the training-calibrated thresholds rather than its own distribution (no recalibration)
    assert val_stats["hit_rate"] == 0


