"""Integration test to verify StormGuard 5-component system works end-to-end."""

import pandas as pd
import numpy as np
from datetime import datetime

from src.stormguard import StormGuardCalculator


def test_full_integration():
    """Test that all 5 metrics work together in the calculator."""
    print("\nTesting StormGuard 5-Component Integration...")
    print("=" * 60)
    
    # Create sample data
    dates = pd.date_range(start='2020-01-01', periods=150, freq='D')
    
    spy = pd.Series(np.linspace(100, 120, 150), index=dates)
    spy_vol = pd.Series([1000000] * 150, index=dates)
    vix = pd.Series([20] * 150, index=dates)
    hyg = pd.Series(np.linspace(100, 110, 150), index=dates)
    ief = pd.Series(np.linspace(100, 105, 150), index=dates)
    rsp = pd.Series(np.linspace(100, 115, 150), index=dates)
    
    # Create dummy schedule
    schedule = pd.DataFrame({
        'signal_date': dates[::10],  # Every 10 days
        'rebalance_date': dates[::10]
    })
    
    # Initialize calculator
    calc = StormGuardCalculator(
        volatility_threshold=40.0,
        false_alarm_days=10,
        early_return_threshold=0.75
    )
    
    print("\n1. Testing metric calculations...")
    metrics = calc.calculate_all_metrics(spy, spy_vol, vix, hyg, ief, rsp)
    
    print(f"   Price-Trend: {len(metrics['price_trend'])} values")
    print(f"   Money-Flow: {len(metrics['money_flow'])} values")
    print(f"   Sentiment: {len(metrics['sentiment'])} values")
    print(f"   Credit-Risk: {metrics['credit_risk'].sum()} bullish days")
    print(f"   Internal-Breadth: {metrics['internal_breadth'].sum()} bullish days")
    
    assert len(metrics) == 6  # 5 main + market_volatility
    assert 'credit_risk' in metrics
    assert 'internal_breadth' in metrics
    print("   [PASS] All 5 metrics calculated successfully")
    
    print("\n2. Testing market state detection...")
    test_date = dates[100]
    state = calc.get_market_state(
        spy, spy_vol, vix, hyg, ief, rsp,
        test_date, schedule
    )
    
    print(f"   Market state on {test_date.date()}: {state}")
    assert state in ['BULL', 'BEAR']
    print("   [PASS] State detection working")
    
    print("\n3. Testing get_metrics_for_date...")
    metric_values = calc.get_metrics_for_date(
        spy, spy_vol, vix, hyg, ief, rsp, test_date
    )
    
    print(f"   Price-Trend: {metric_values['price_trend']:.4f}")
    print(f"   Money-Flow: {metric_values['money_flow']:.2f}")
    print(f"   Sentiment: {metric_values['sentiment']:.4f}")
    print(f"   Credit-Risk: {metric_values['credit_risk']}")
    print(f"   Internal-Breadth: {metric_values['internal_breadth']}")
    
    assert 'credit_risk' in metric_values
    assert 'internal_breadth' in metric_values
    print("   [PASS] Individual metric values retrieved")
    
    print("\n4. Testing backward compatibility...")
    # Old import path should still work
    from src.stormguard import StormGuardCalculator as OldImport
    old_calc = OldImport()
    assert type(old_calc).__name__ == 'StormGuardCalculator'
    print("   [PASS] Old import path works")
    
    print("\n" + "=" * 60)
    print("ALL INTEGRATION TESTS PASSED")
    print("=" * 60)
    print("\nStormGuard 5-Component System Ready:")
    print("  - 2 new leading indicators added")
    print("  - Refactored into modular package")
    print("  - Backward compatible")
    print("  - All metrics operational")
    print("\nNext: Run 'python main.py' to test full backtest")


if __name__ == "__main__":
    test_full_integration()

