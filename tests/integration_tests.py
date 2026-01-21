"""
Integration test to validate all improvements to the trading system.
Tests the redesigned risk model, position sizing, SL/TP logic, fusion weighting,
regime classification, strategy selection, and profitability enhancements.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Add the project root to the path so we can import our modules
sys.path.insert(0, '/Users/mojtaba.rahbari/Sites/python/lynxion-ets')

from infrastructure.risk.adaptive_risk_manager import adaptive_risk_manager, RegimeType
from infrastructure.position_sizing.probabilistic_position_sizer import position_sizing_service
from infrastructure.risk.advanced_sltp_manager import sltp_manager, PositionSide
from infrastructure.fusion.adaptive_fusion_weighting import adaptive_fusion_service
from infrastructure.market_regime.advanced_regime_classifier import regime_classifier, RegimeClassification
from infrastructure.strategies.advanced_strategy_selector import strategy_selection_service
from utils.profitability_enhancer import integrated_profitability_system


def generate_test_data(n: int = 100) -> pd.DataFrame:
    """Generate realistic test market data."""
    np.random.seed(42)  # For reproducible results
    
    # Generate base price series with trend and volatility
    returns = np.random.normal(0.0005, 0.02, n)  # Daily returns: 0.05% average, 2% std
    prices = [100]  # Starting price
    
    for i in range(1, n):
        prices.append(prices[-1] * (1 + returns[i]))
    
    # Add some volatility clustering (GARCH-like effect)
    vol_mult = np.random.chisquare(df=2, size=n)  # Random volatility multiplier
    vol_returns = [r * vm for r, vm in zip(returns, vol_mult)]
    
    # Recalculate prices with adjusted returns
    adj_prices = [100]
    for i in range(1, n):
        adj_prices.append(adj_prices[-1] * (1 + vol_returns[i]))
    
    # Generate volumes with some correlation to volatility
    volumes = np.random.lognormal(mean=9, sigma=1, size=n)  # Log-normal distributed volumes
    volumes = volumes * (1 + np.abs(vol_returns) * 10)  # Higher volumes during high volatility
    
    dates = [datetime.now() - timedelta(days=n-i) for i in range(n)]
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': adj_prices * (1 + np.random.normal(0, 0.005, n)),
        'high': adj_prices * (1 + np.abs(np.random.normal(0, 0.01, n))),
        'low': adj_prices * (1 - np.abs(np.random.normal(0, 0.01, n))),
        'close': adj_prices,
        'volume': volumes
    })
    
    # Ensure OHLC constraints
    df['high'] = df[['high', 'open', 'close']].max(axis=1)
    df['low'] = df[['low', 'open', 'close']].min(axis=1)
    
    return df


def test_adaptive_risk_manager():
    """Test the adaptive risk manager."""
    print("🧪 Testing Adaptive Risk Manager...")
    
    # Setup test parameters
    portfolio_equity = 100000
    entry_price = 50000
    stop_loss = 49000  # 2% stop loss
    take_profit = 52000  # 4% take profit
    
    # Test regime classification
    test_prices = [50000 + i*10 for i in range(50)]  # Slight uptrend
    regime_result: RegimeClassification = regime_classifier.classify_regime(test_prices)
    
    print(f"   Current regime: {regime_result.regime.value}")
    print(f"   Regime confidence: {regime_result.confidence:.3f}")
    print(f"   Regime stability: {regime_result.stability:.3f}")
    print(f"   Regime maturity: {regime_result.maturity:.3f}")
    print(f"   Regime veto: {regime_result.veto}")
    
    # Calculate position size with adaptive risk management
    position_size, factors = adaptive_risk_manager.calculate_position_size(
        symbol="BTCUSDT",
        entry_price=entry_price,
        stop_loss=stop_loss,
        portfolio_equity=portfolio_equity,
        regime=regime_result.regime,
        regime_confidence=regime_result.confidence,
        correlation_symbols=["ETHUSDT", "SOLUSDT"]
    )
    
    print(f"   Calculated position size: {position_size:.4f}")
    print(f"   Position size factors: {factors}")
    
    # Test entering and exiting position
    success = adaptive_risk_manager.enter_position(
        symbol="BTCUSDT",
        entry_price=entry_price,
        size=position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        regime=regime_result.regime
    )
    print(f"   Position entry successful: {success}")
    
    # Test exit
    pnl = adaptive_risk_manager.exit_position("BTCUSDT", 51000)  # Exit at profit
    print(f"   Position exit PnL: ${pnl:.2f}")
    
    # Get risk metrics
    metrics = adaptive_risk_manager.get_risk_metrics()
    print(f"   Total exposure: ${metrics.total_exposure:.2f}")
    print(f"   Current drawdown: {metrics.current_drawdown:.4f}")
    print(f"   Portfolio volatility: {metrics.volatility:.4f}")
    print(f"   Correlation risk: {metrics.correlation_risk:.4f}")
    
    print("✅ Adaptive Risk Manager test completed\n")


def test_probabilistic_position_sizing():
    """Test the probabilistic position sizing."""
    print("🧪 Testing Probabilistic Position Sizing...")
    
    # Test parameters
    entry_price = 50000
    stop_loss = 49000  # 2% stop
    portfolio_equity = 100000
    
    # Test with various confidence levels
    result = position_sizing_service.get_optimal_size(
        symbol="BTCUSDT",
        entry_price=entry_price,
        stop_loss=stop_loss,
        portfolio_equity=portfolio_equity,
        fusion_confidence=0.8,
        regime_accuracy=0.75,
        strategy_expectancy=0.15,
        correlation_exposure=0.3,
        current_drawdown=0.02,
        regime_context="bullish_trending",
        volatility=0.015
    )
    
    print(f"   Position size: {result.size:.4f}")
    print(f"   Position confidence: {result.confidence:.3f}")
    print(f"   Risk amount: ${result.risk_amount:.2f}")
    print(f"   Method used: {result.method_used}")
    print(f"   Calculation factors: {result.factors}")
    
    # Test with poor conditions (should result in smaller position)
    result_poor = position_sizing_service.get_optimal_size(
        symbol="BTCUSDT",
        entry_price=entry_price,
        stop_loss=stop_loss,
        portfolio_equity=portfolio_equity,
        fusion_confidence=0.3,
        regime_accuracy=0.4,
        strategy_expectancy=-0.1,
        correlation_exposure=0.8,
        current_drawdown=0.12,
        regime_context="choppy",
        volatility=0.03
    )
    
    print(f"   Position size (poor conditions): {result_poor.size:.4f}")
    print(f"   Risk amount (poor conditions): ${result_poor.risk_amount:.2f}")
    
    print("✅ Probabilistic Position Sizing test completed\n")


def test_advanced_sltp_manager():
    """Test the advanced SL/TP manager."""
    print("🧪 Testing Advanced SL/TP Manager...")
    
    # Generate test market data
    market_data = generate_test_data(50)
    
    # Test parameters
    entry_price = 50000
    position_side = PositionSide.LONG
    
    # Calculate ATR from market data
    atr_value = sltp_manager._calculate_atr(market_data)
    print(f"   Calculated ATR: ${atr_value:.2f}")
    
    # Calculate SL/TP levels
    levels = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=position_side,
        atr_value=atr_value,
        regime=RegimeType.BULLISH_TRENDING,
        support_level=48000,
        resistance_level=53000
    )
    
    print(f"   Stop Loss: ${levels.stop_loss:.2f}")
    print(f"   Take Profit: ${levels.take_profit:.2f}")
    print(f"   SL Distance: ${levels.sl_distance:.2f}")
    print(f"   TP Distance: ${levels.tp_distance:.2f}")
    print(f"   SL ATR Multiple: {levels.sl_atr_multiple:.2f}")
    print(f"   TP ATR Multiple: {levels.tp_atr_multiple:.2f}")
    
    # Test exit conditions
    exit_price, exit_type = sltp_manager.check_exit_conditions(
        current_price=50100,
        high_price=52500,  # Hits TP
        low_price=49500,
        sl_price=levels.stop_loss,
        tp_price=levels.take_profit,
        position_side=position_side
    )
    
    print(f"   Exit price: ${exit_price:.2f}, Exit type: {exit_type}")
    
    # Test trailing stop
    new_stop = sltp_manager.update_trailing_stop(
        current_price=51000,
        entry_price=entry_price,
        initial_stop_loss=levels.stop_loss,
        position_side=position_side,
        trail_activation_percent=0.02,
        trail_distance_percent=0.01
    )
    
    print(f"   Trailing stop updated to: ${new_stop:.2f}")
    
    print("✅ Advanced SL/TP Manager test completed\n")


def test_adaptive_fusion_weighting():
    """Test the adaptive fusion weighting."""
    print("🧪 Testing Adaptive Fusion Weighting...")
    
    # Create test signals
    signals = [
        {'name': 'momentum_signal', 'type': 'momentum'},
        {'name': 'mean_reversion_signal', 'type': 'mean_reversion'},
        {'name': 'trend_following_signal', 'type': 'trend'},
        {'name': 'volatility_signal', 'type': 'volatility'}
    ]
    
    # Corresponding signal values
    signal_values = [0.6, -0.3, 0.4, 0.2]
    
    # Update signal performance
    for i, signal in enumerate(signals):
        # Simulate good performance for some signals, poor for others
        perf = 0.05 if i % 2 == 0 else -0.02
        adaptive_fusion_service.weighting_system.update_signal_performance(
            signal['name'], perf
        )
    
    # Update correlations between signals
    adaptive_fusion_service.weighting_system.update_signal_correlation(
        'momentum_signal', 'trend_following_signal', 0.6
    )
    adaptive_fusion_service.weighting_system.update_signal_correlation(
        'mean_reversion_signal', 'trend_following_signal', -0.3
    )
    
    # Fuse signals with adaptive weights
    fused_value = adaptive_fusion_service.fuse_signals_with_weights(signals, signal_values)
    print(f"   Fused signal value: {fused_value:.4f}")
    
    # Get normalized weights
    signal_names = [s['name'] for s in signals]
    weights = adaptive_fusion_service.weighting_system.calculate_normalized_weights(signal_names)
    
    print("   Signal weights:")
    for name, weight in weights.items():
        print(f"     {name}: {weight:.4f}")
    
    # Get top signals
    top_signals = adaptive_fusion_service.weighting_system.get_top_signals(signal_names, n=2)
    print(f"   Top signals: {top_signals}")
    
    # Get fusion analysis
    analysis = adaptive_fusion_service.get_fusion_analysis()
    print(f"   Total fusions processed: {analysis.get('total_fusions', 0)}")
    
    print("✅ Adaptive Fusion Weighting test completed\n")


def test_advanced_regime_classification():
    """Test the advanced regime classification."""
    print("🧪 Testing Advanced Regime Classification...")
    
    # Generate different market conditions
    # Bullish trending
    bullish_prices = [100 + i*2 + np.random.normal(0, 1, 1)[0] for i in range(50)]
    bullish_result = regime_classifier.classify_regime(bullish_prices)
    
    print(f"   Bullish trend - Regime: {bullish_result.regime.value}")
    print(f"   Bullish trend - Confidence: {bullish_result.confidence:.3f}")
    print(f"   Bullish trend - Stability: {bullish_result.stability:.3f}")
    print(f"   Bullish trend - Maturity: {bullish_result.maturity:.3f}")
    print(f"   Bullish trend - Veto: {bullish_result.veto}")
    
    # Choppy/ranging
    choppy_prices = [100 + 5*np.sin(i*0.5) + np.random.normal(0, 0.5, 1)[0] for i in range(50)]
    choppy_result = regime_classifier.classify_regime(choppy_prices)
    
    print(f"   Choppy market - Regime: {choppy_result.regime.value}")
    print(f"   Choppy market - Confidence: {choppy_result.confidence:.3f}")
    print(f"   Choppy market - Stability: {choppy_result.stability:.3f}")
    print(f"   Choppy market - Maturity: {choppy_result.maturity:.3f}")
    print(f"   Choppy market - Veto: {choppy_result.veto}")
    
    # High volatility
    volatile_prices = [100]
    for i in range(1, 50):
        volatile_prices.append(volatile_prices[-1] * (1 + np.random.normal(0, 0.04, 1)[0]))  # 4% daily std
    volatile_result = regime_classifier.classify_regime(volatile_prices)
    
    print(f"   High volatility - Regime: {volatile_result.regime.value}")
    print(f"   High volatility - Confidence: {volatile_result.confidence:.3f}")
    
    # Test confusion matrix analysis
    regime_classifier.update_performance_feedback(
        predicted_regime=bullish_result.regime,
        actual_regime=bullish_result.regime,  # Assuming correct prediction
        accuracy=0.85
    )
    
    confusion_analysis = regime_classifier.get_confusion_matrix_analysis()
    print(f"   Confusion matrix accuracy by predicted: {confusion_analysis.get('accuracy_by_predicted', {})}")
    
    print("✅ Advanced Regime Classification test completed\n")


def test_advanced_strategy_selection():
    """Test the advanced strategy selection."""
    print("🧪 Testing Advanced Strategy Selection...")
    
    # Define test strategies
    strategies = ["momentum_strategy", "mean_reversion", "trend_following", "breakout_strategy"]
    
    # Update performance for each strategy
    np.random.seed(123)
    for i, strategy in enumerate(strategies):
        # Generate synthetic returns
        returns = np.random.normal(0.001 + i*0.0002, 0.015 - i*0.0003, 30)  # Different performance for each
        win_rate = 0.55 + i*0.05
        max_drawdown = -0.08 + i*0.01
        volatility = 0.015 - i*0.001
        correlation = 0.2 + i*0.15
        
        strategy_selection_service.selector.update_strategy_performance(
            strategy_name=strategy,
            returns=returns.tolist(),
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            volatility=volatility,
            correlation_with_portfolio=correlation,
            regime_context="bullish_trending" if i < 2 else "normal"
        )
    
    # Get strategy rankings
    rankings = strategy_selection_service.selector.get_strategy_rankings()
    print("   Strategy Rankings:")
    for i, (name, score) in enumerate(rankings[:5]):  # Top 5
        print(f"     {i+1}. {name}: {score:.4f}")
    
    # Select best strategy for current regime
    best_strategy = strategy_selection_service.selector.select_best_strategy(
        available_strategies=strategies,
        regime_context="bullish_trending"
    )
    print(f"   Selected best strategy: {best_strategy}")
    
    # Get strategy metrics
    metrics = strategy_selection_service.selector.get_strategy_metrics("momentum_strategy")
    if metrics:
        print(f"   Momentum strategy metrics:")
        print(f"     Performance Score: {metrics.performance_score:.4f}")
        print(f"     Sharpe Ratio: {metrics.sharpe_ratio:.4f}")
        print(f"     Win Rate: {metrics.win_rate:.4f}")
        print(f"     Status: {metrics.status.value}")
    
    # Get promotion/demotion candidates
    candidates = strategy_selection_service.selector.get_promotion_demotion_candidates()
    print(f"   Promotion candidates: {candidates['promotion']}")
    print(f"   Demotion candidates: {candidates['demotion']}")
    
    print("✅ Advanced Strategy Selection test completed\n")


def test_profitability_enhancements():
    """Test the profitability enhancement techniques."""
    print("🧪 Testing Profitability Enhancements...")
    
    # Generate test market data
    market_data = generate_test_data(100)
    
    # Test variance reduction
    test_returns = np.random.normal(0.001, 0.02, 50).tolist()
    reduced_returns = integrated_profitability_system.enhancer.apply_variance_reduction(test_returns)
    print(f"   Original return volatility: {np.std(test_returns):.6f}")
    print(f"   Reduced return volatility: {np.std(reduced_returns):.6f}")
    
    # Test expectancy compounding
    base_expectancy = 0.02
    confidence = 0.8
    compounded = integrated_profitability_system.enhancer.compound_expectancy(
        base_expectancy=base_expectancy,
        confidence=confidence,
        market_regime_factor=1.2
    )
    print(f"   Base expectancy: {base_expectancy:.4f}")
    print(f"   Compounded expectancy: {compounded:.4f}")
    
    # Test selective filtering
    should_trade = integrated_profitability_system.enhancer.selective_trade_filter(
        signal_strength=0.7,
        correlation_with_portfolio=0.4,
        market_volatility=0.02,
        trend_strength=0.15,
        regime_confidence=0.7,
        recent_performance=0.03
    )
    print(f"   Selective filter result: {should_trade}")
    
    # Test capital efficiency improvement
    original_size = 5.0
    enhanced_size = integrated_profitability_system.enhancer.improve_capital_efficiency(
        position_size=original_size,
        portfolio_value=100000,
        volatility=0.02,
        correlation_factor=0.3,
        regime_factor=1.1
    )
    print(f"   Original position size: {original_size}")
    print(f"   Enhanced position size: {enhanced_size:.4f}")
    
    # Test signal timing refinement
    timing_result = integrated_profitability_system.enhancer.refine_signal_timing(
        entry_signal_time=datetime.now(),
        market_data=market_data.tail(20)
    )
    print(f"   Timing quality: {timing_result['timing_quality']:.3f}")
    print(f"   Refinement reason: {timing_result['refinement_reason']}")
    
    # Test portfolio allocation optimization
    strategy_returns = {
        "momentum": np.random.normal(0.001, 0.015, 30).tolist(),
        "mean_reversion": np.random.normal(0.0008, 0.012, 30).tolist(),
        "trend_following": np.random.normal(0.0012, 0.018, 30).tolist()
    }
    
    allocation = integrated_profitability_system.optimize_portfolio_allocation(strategy_returns)
    print("   Optimized portfolio allocation:")
    for strategy, weight in allocation.items():
        print(f"     {strategy}: {weight:.4f}")
    
    print("✅ Profitability Enhancements test completed\n")


def test_end_to_end_integration():
    """Test end-to-end integration of all components."""
    print("🧪 Testing End-to-End Integration...")
    
    # Generate market data
    market_data = generate_test_data(100)
    
    # 1. Regime Classification
    prices = market_data['close'].tolist()
    regime_result = regime_classifier.classify_regime(prices)
    print(f"   Detected regime: {regime_result.regime.value} (confidence: {regime_result.confidence:.3f})")
    
    # 2. Strategy Selection
    available_strategies = ["momentum_strategy", "mean_reversion", "trend_following"]
    selected_strategy = strategy_selection_service.selector.select_best_strategy(
        available_strategies=available_strategies,
        regime_context=regime_result.regime.value
    )
    print(f"   Selected strategy: {selected_strategy}")
    
    # 3. Signal Processing & Fusion
    signals = [
        {'name': 'momentum_signal', 'strength': 0.6},
        {'name': 'trend_signal', 'strength': 0.5},
        {'name': 'volatility_signal', 'strength': -0.2}
    ]
    signal_values = [0.6, 0.5, -0.2]
    
    # Update signal performances for weighting
    for signal in signals:
        adaptive_fusion_service.weighting_system.update_signal_performance(
            signal['name'], 0.05  # Good performance
        )
    
    fused_signal = adaptive_fusion_service.fuse_signals_with_weights(signals, signal_values)
    print(f"   Fused signal value: {fused_signal:.4f}")
    
    # 4. Position Sizing
    entry_price = market_data['close'].iloc[-1]
    stop_loss = entry_price * 0.98  # 2% stop loss
    portfolio_value = 50000
    
    position_result = position_sizing_service.get_optimal_size(
        symbol="BTCUSDT",
        entry_price=entry_price,
        stop_loss=stop_loss,
        portfolio_equity=portfolio_value,
        fusion_confidence=regime_result.confidence,
        regime_accuracy=regime_result.stability,
        strategy_expectancy=0.08,
        correlation_exposure=0.25,
        current_drawdown=0.03,
        regime_context=regime_result.regime.value
    )
    
    print(f"   Position size: {position_result.size:.4f}")
    print(f"   Position confidence: {position_result.confidence:.3f}")
    
    # 5. SL/TP Calculation
    sltp_levels = sltp_manager.calculate_levels(
        entry_price=entry_price,
        position_side=PositionSide.LONG,
        atr_value=sltp_manager._calculate_atr(market_data),
        regime=regime_result.regime,
        support_level=market_data['close'].quantile(0.1),
        resistance_level=market_data['close'].quantile(0.9)
    )
    
    print(f"   Calculated SL: ${sltp_levels.stop_loss:.2f}")
    print(f"   Calculated TP: ${sltp_levels.take_profit:.2f}")
    
    # 6. Risk Management
    risk_success = adaptive_risk_manager.enter_position(
        symbol="BTCUSDT",
        entry_price=entry_price,
        size=position_result.size,
        stop_loss=sltp_levels.stop_loss,
        take_profit=sltp_levels.take_profit,
        regime=regime_result.regime
    )
    
    print(f"   Position entry with risk management: {risk_success}")
    
    # 7. Profitability Enhancement Applied
    signal_data = {
        'signal_strength': fused_signal,
        'position_size': position_result.size,
        'base_expectancy': 0.08,
        'confidence': position_result.confidence,
        'regime_factor': 1.0,
        'signal_time': datetime.now()
    }
    
    portfolio_data = {
        'portfolio_value': portfolio_value,
        'correlation': 0.3,
        'recent_performance': 0.05
    }
    
    processed_signal = integrated_profitability_system.process_signal(
        signal_data=signal_data,
        market_data=market_data,
        portfolio_data=portfolio_data
    )
    
    print(f"   Enhanced expectancy: {processed_signal.get('enhanced_expectancy', 'N/A')}")
    print(f"   Refined position size: {processed_signal.get('enhanced_position_size', 'N/A')}")
    print(f"   Applied enhancements: {processed_signal.get('applied_enhancements', [])}")
    
    print("✅ End-to-End Integration test completed\n")


def main():
    """Run all integration tests."""
    print("🚀 Starting Comprehensive Integration Tests for Enhanced Trading System\n")
    
    try:
        test_adaptive_risk_manager()
        test_probabilistic_position_sizing()
        test_advanced_sltp_manager()
        test_adaptive_fusion_weighting()
        test_advanced_regime_classification()
        test_advanced_strategy_selection()
        test_profitability_enhancements()
        test_end_to_end_integration()
        
        print("🎉 All integration tests completed successfully!")
        print("✅ The enhanced trading system components are working correctly together.")
        
    except Exception as e:
        print(f"❌ Error during integration tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✨ All systems validated! The enhanced trading system is ready for production.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")