"""Unit tests for backtest engine."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest import BacktestEngine


@pytest.fixture
def sample_prices():
    """Create sample price data."""
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
    
    prices = pd.DataFrame({
        'SPY': np.linspace(100, 150, 100),  # 50% gain
        'QQQ': np.linspace(100, 120, 100),  # 20% gain
        'DIA': np.linspace(100, 100, 100),  # Flat
    }, index=dates)
    
    return prices


@pytest.fixture
def sample_positions(sample_prices):
    """Create sample position schedule."""
    # Hold SPY for first half, QQQ for second half
    positions = pd.DataFrame({
        'position': ['SPY', 'QQQ']
    }, index=[sample_prices.index[0], sample_prices.index[50]])
    
    return positions


def test_engine_initialization():
    """Test backtest engine initialization."""
    engine = BacktestEngine(
        initial_capital=100000,
        commission_pct=0.001,
        slippage_pct=0.0005
    )
    
    assert engine.initial_capital == 100000
    assert engine.commission_pct == 0.001
    assert engine.slippage_pct == 0.0005


def test_calculate_trade_cost():
    """Test transaction cost calculation."""
    engine = BacktestEngine(commission_pct=0.001, slippage_pct=0.0005)
    
    trade_value = 10000
    cost = engine.calculate_trade_cost(trade_value)
    
    # Cost should be commission + slippage = 0.15%
    expected_cost = 10000 * (0.001 + 0.0005)
    assert cost == expected_cost


def test_run_backtest_basic(sample_prices, sample_positions):
    """Test basic backtest execution."""
    engine = BacktestEngine(initial_capital=100000)
    
    equity_curve, trades = engine.run_backtest(sample_prices, sample_positions)
    
    # Check equity curve structure
    assert isinstance(equity_curve, pd.DataFrame)
    assert 'equity' in equity_curve.columns
    assert 'cash' in equity_curve.columns
    assert 'position_value' in equity_curve.columns
    assert len(equity_curve) == len(sample_prices)
    
    # Check trades structure
    assert isinstance(trades, pd.DataFrame)
    assert 'action' in trades.columns
    assert 'symbol' in trades.columns
    assert 'shares' in trades.columns
    assert 'price' in trades.columns


def test_backtest_equity_growth(sample_prices, sample_positions):
    """Test that equity grows with profitable positions."""
    engine = BacktestEngine(initial_capital=100000, commission_pct=0, slippage_pct=0)
    
    equity_curve, trades = engine.run_backtest(sample_prices, sample_positions)
    
    # Final equity should be greater than initial (prices went up)
    assert equity_curve['equity'].iloc[-1] > engine.initial_capital


def test_backtest_transactions(sample_prices, sample_positions):
    """Test that trades are executed correctly."""
    engine = BacktestEngine(initial_capital=100000)
    
    equity_curve, trades = engine.run_backtest(sample_prices, sample_positions)
    
    # Should have trades (2 rebalances = buy SPY, sell SPY + buy QQQ)
    assert len(trades) >= 2
    
    # First trade should be a BUY
    assert trades.iloc[0]['action'] == 'BUY'
    
    # Check that shares are positive
    assert all(trades['shares'] > 0)


def test_calculate_metrics():
    """Test performance metrics calculation."""
    # Create simple equity curve
    dates = pd.date_range(start='2020-01-01', periods=252, freq='D')
    equity = pd.DataFrame({
        'equity': np.linspace(100000, 150000, 252)  # 50% gain over 1 year
    }, index=dates)
    
    engine = BacktestEngine(initial_capital=100000)
    metrics = engine.calculate_metrics(equity)
    
    # Check that all expected metrics are present
    expected_metrics = [
        'Initial Capital',
        'Final Equity',
        'Total Return (%)',
        'CAGR (%)',
        'Volatility (%)',
        'Sharpe Ratio',
        'Max Drawdown (%)',
        'Calmar Ratio',
        'Win Rate (%)',
    ]
    
    for metric in expected_metrics:
        assert metric in metrics
    
    # Total return should be approximately 50%
    assert 45 < metrics['Total Return (%)'] < 55


def test_calculate_drawdown_series():
    """Test drawdown calculation."""
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
    
    # Create equity with a drawdown
    equity_values = [100000] * 50 + list(np.linspace(100000, 80000, 25)) + [80000] * 25
    equity = pd.DataFrame({'equity': equity_values}, index=dates)
    
    engine = BacktestEngine()
    drawdown = engine.calculate_drawdown_series(equity)
    
    # Drawdown should be 0 at peak
    assert drawdown.iloc[49] == 0
    
    # Drawdown should be -20% at trough
    assert abs(drawdown.iloc[-1] - (-20.0)) < 0.1


def test_empty_positions():
    """Test backtest with no positions."""
    dates = pd.date_range(start='2020-01-01', periods=50, freq='D')
    prices = pd.DataFrame({'SPY': range(100, 150)}, index=dates)
    
    # Empty positions
    positions = pd.DataFrame({'position': [None]}, index=[dates[0]])
    
    engine = BacktestEngine(initial_capital=100000)
    equity_curve, trades = engine.run_backtest(prices, positions)
    
    # Equity should remain constant (no positions held)
    assert equity_curve['equity'].iloc[-1] == pytest.approx(100000, abs=100)

