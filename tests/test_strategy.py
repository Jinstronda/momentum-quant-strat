"""Unit tests for strategy module."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.strategy import MomentumStrategy


@pytest.fixture
def sample_prices():
    """Create sample price data for testing."""
    dates = pd.date_range(start='2020-01-01', periods=50, freq='D')
    
    prices = pd.DataFrame({
        'SPY': np.linspace(100, 120, 50),  # Strong uptrend
        'QQQ': np.linspace(100, 110, 50),  # Moderate uptrend
        'DIA': np.linspace(100, 100, 50),  # Flat
    }, index=dates)
    
    return prices


@pytest.fixture
def sample_schedule(sample_prices):
    """Create sample rebalance schedule."""
    schedule = pd.DataFrame({
        'rebalance_date': sample_prices.index[::10],  # Every 10 days
        'signal_date': sample_prices.index[::10] - pd.Timedelta(days=1),
    })
    return schedule


def test_strategy_initialization():
    """Test strategy initialization with different parameters."""
    strategy = MomentumStrategy(roc_period=21, top_n=1)
    assert strategy.roc_period == 21
    assert strategy.top_n == 1
    
    strategy2 = MomentumStrategy(roc_period=10, top_n=3)
    assert strategy2.roc_period == 10
    assert strategy2.top_n == 3


def test_get_position_for_date(sample_prices):
    """Test single position selection."""
    strategy = MomentumStrategy(roc_period=10, top_n=1)
    
    # Get position for a date with enough history
    signal_date = sample_prices.index[30]
    position = strategy.get_position_for_date(sample_prices, signal_date)
    
    # Should return SPY (strongest momentum)
    assert position == 'SPY'


def test_get_position_insufficient_data(sample_prices):
    """Test position selection with insufficient data."""
    strategy = MomentumStrategy(roc_period=10, top_n=1)
    
    # Try to get position on day 5 (not enough data)
    signal_date = sample_prices.index[5]
    position = strategy.get_position_for_date(sample_prices, signal_date)
    
    # Should return None (not enough data)
    assert position is None


def test_generate_rebalance_positions(sample_prices):
    """Test position generation for rebalance schedule."""
    strategy = MomentumStrategy(roc_period=10, top_n=1)
    
    # Create a simple schedule
    schedule = pd.DataFrame({
        'rebalance_date': sample_prices.index[[20, 30, 40]],
        'signal_date': sample_prices.index[[19, 29, 39]],
    })
    
    positions = strategy.generate_rebalance_positions(sample_prices, schedule)
    
    # Check output structure
    assert isinstance(positions, pd.DataFrame)
    assert len(positions) == 3
    assert 'position' in positions.columns
    
    # All positions should be SPY (strongest momentum)
    assert (positions['position'] == 'SPY').all()


def test_calculate_position_roc(sample_prices):
    """Test ROC calculation for positions."""
    strategy = MomentumStrategy(roc_period=10, top_n=1)
    
    schedule = pd.DataFrame({
        'rebalance_date': sample_prices.index[[20, 30, 40]],
        'signal_date': sample_prices.index[[19, 29, 39]],
    })
    
    results = strategy.calculate_position_roc(sample_prices, schedule)
    
    # Check output structure
    assert isinstance(results, pd.DataFrame)
    assert 'position' in results.columns
    assert 'roc' in results.columns
    
    # ROC values should be positive for uptrend
    assert (results['roc'] > 0).all()


def test_top_n_error():
    """Test that get_position_for_date raises error for top_n != 1."""
    strategy = MomentumStrategy(roc_period=10, top_n=3)
    
    dates = pd.date_range(start='2020-01-01', periods=30, freq='D')
    prices = pd.DataFrame({'A': range(100, 130)}, index=dates)
    
    with pytest.raises(ValueError, match="only for top-1 strategies"):
        strategy.get_position_for_date(prices, dates[20])

