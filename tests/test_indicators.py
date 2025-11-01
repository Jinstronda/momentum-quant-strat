"""Unit tests for indicators module."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.indicators import (
    calculate_roc,
    calculate_momentum_rank,
    get_top_n_symbols,
    get_top_symbol_per_date
)


@pytest.fixture
def sample_prices():
    """Create sample price data for testing."""
    dates = pd.date_range(start='2020-01-01', periods=50, freq='D')
    
    # Create price series with known ROC
    prices = pd.DataFrame({
        'A': np.linspace(100, 120, 50),  # Uptrend
        'B': np.linspace(100, 110, 50),  # Moderate uptrend
        'C': np.linspace(100, 100, 50),  # Flat
        'D': np.linspace(100, 90, 50),   # Downtrend
    }, index=dates)
    
    return prices


def test_calculate_roc_basic(sample_prices):
    """Test basic ROC calculation."""
    roc = calculate_roc(sample_prices, period=10)
    
    # Check shape
    assert roc.shape == sample_prices.shape
    
    # First 10 periods should be NaN
    assert roc.iloc[:10].isna().all().all()
    
    # ROC should not be NaN after warmup period
    assert not roc.iloc[10:].isna().all().all()


def test_calculate_roc_values(sample_prices):
    """Test ROC calculation produces correct values."""
    roc = calculate_roc(sample_prices, period=10)
    
    # 'A' has strongest uptrend, so should have positive ROC
    assert (roc['A'].iloc[10:] > 0).all()
    
    # 'D' has downtrend, so should have negative ROC
    assert (roc['D'].iloc[10:] < 0).all()
    
    # 'A' ROC should be greater than 'B' ROC (stronger trend)
    assert (roc['A'].iloc[10:] > roc['B'].iloc[10:]).all()


def test_calculate_momentum_rank(sample_prices):
    """Test momentum ranking."""
    ranks = calculate_momentum_rank(sample_prices, period=10)
    
    # Check shape
    assert ranks.shape == sample_prices.shape
    
    # After warmup, 'A' should rank 1 (highest momentum)
    assert (ranks['A'].iloc[10:] == 1).all()
    
    # 'D' should rank last (lowest momentum)
    assert (ranks['D'].iloc[10:] == 4).all()


def test_get_top_n_symbols(sample_prices):
    """Test top N symbol selection."""
    top_2 = get_top_n_symbols(sample_prices, period=10, top_n=2)
    
    # Check shape
    assert top_2.shape == sample_prices.shape
    
    # After warmup, exactly 2 symbols should be selected per date
    assert (top_2.iloc[10:].sum(axis=1) == 2).all()
    
    # 'A' should always be selected (best momentum)
    assert (top_2['A'].iloc[10:] == 1).all()


def test_get_top_symbol_per_date(sample_prices):
    """Test single top symbol selection."""
    top_symbols = get_top_symbol_per_date(sample_prices, period=10)
    
    # Check type
    assert isinstance(top_symbols, pd.Series)
    
    # After warmup, 'A' should always be selected
    assert (top_symbols.iloc[10:] == 'A').all()


def test_roc_edge_cases():
    """Test ROC calculation edge cases."""
    # Test with single column
    dates = pd.date_range(start='2020-01-01', periods=30, freq='D')
    single_col = pd.DataFrame({'X': range(100, 130)}, index=dates)
    
    roc = calculate_roc(single_col, period=10)
    assert roc.shape == single_col.shape
    
    # Test with very short period
    roc_short = calculate_roc(single_col, period=1)
    assert not roc_short.iloc[1:].isna().all().all()


def test_roc_zero_division():
    """Test ROC handles zero prices correctly."""
    dates = pd.date_range(start='2020-01-01', periods=30, freq='D')
    
    # Prices that start at zero
    prices = pd.DataFrame({'X': [0] * 10 + list(range(10, 30))}, index=dates)
    
    roc = calculate_roc(prices, period=5)
    
    # Should handle zeros gracefully (inf or nan)
    assert roc.shape == prices.shape

