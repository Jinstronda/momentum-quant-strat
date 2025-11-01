"""Unit tests for dual EMA filter system."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.indicators import (
    calculate_ema,
    calculate_ema_derivative,
    get_dual_ema_filter,
    apply_dual_ema_filter_to_roc
)
from src.strategy import MomentumStrategy


@pytest.fixture
def uptrend_prices():
    """Create strong uptrend data."""
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'UP': np.linspace(100, 150, 100)
    }, index=dates)


@pytest.fixture
def downtrend_prices():
    """Create downtrend data."""
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'DOWN': np.linspace(150, 100, 100)
    }, index=dates)


@pytest.fixture
def mixed_prices():
    """Create mixed scenario with up and downtrends."""
    dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
    return pd.DataFrame({
        'STRONG_UP': np.linspace(100, 150, 100),
        'WEAK_UP': np.linspace(100, 110, 100),
        'DOWNTREND': np.linspace(150, 100, 100),
    }, index=dates)


def test_calculate_ema_basic(uptrend_prices):
    """Test basic EMA calculation."""
    ema = calculate_ema(uptrend_prices, period=20)
    
    # Check shape
    assert ema.shape == uptrend_prices.shape
    
    # First 19 periods should be NaN (indices 0-18)
    assert ema.iloc[:19].isna().all().all()
    
    # After warmup (index 19+), should have values
    assert not ema.iloc[19:].isna().all().all()


def test_ema_responds_faster_than_sma(uptrend_prices):
    """Test that EMA responds faster to price changes than SMA."""
    from src.indicators import calculate_moving_average
    
    ema = calculate_ema(uptrend_prices, period=20)
    sma = calculate_moving_average(uptrend_prices, period=20)
    
    # In an uptrend, EMA should be higher than SMA (responds faster)
    # Check last value where both are valid
    assert ema['UP'].iloc[-1] > sma['UP'].iloc[-1]


def test_ema_derivative_positive_in_uptrend(uptrend_prices):
    """Test that EMA derivative is positive in uptrend."""
    ema = calculate_ema(uptrend_prices, period=50)
    derivative = calculate_ema_derivative(ema, lookback=1)
    
    # In uptrend, derivative should be positive
    valid_derivatives = derivative.iloc[51:].dropna()  # Skip warmup
    assert (valid_derivatives > 0).all().all()


def test_ema_derivative_negative_in_downtrend(downtrend_prices):
    """Test that EMA derivative is negative in downtrend."""
    ema = calculate_ema(downtrend_prices, period=50)
    derivative = calculate_ema_derivative(ema, lookback=1)
    
    # In downtrend, derivative should be negative
    valid_derivatives = derivative.iloc[51:].dropna()
    assert (valid_derivatives < 0).all().all()


def test_dual_ema_filter_uptrend(uptrend_prices):
    """Test that uptrend passes dual EMA filter."""
    ema_filter = get_dual_ema_filter(uptrend_prices, ema_short=20, ema_long=50)
    
    # After warmup, uptrend should pass all conditions
    # Check last 20 days (well past warmup)
    assert ema_filter['UP'].iloc[-20:].all()


def test_dual_ema_filter_downtrend(downtrend_prices):
    """Test that downtrend fails dual EMA filter."""
    ema_filter = get_dual_ema_filter(downtrend_prices, ema_short=20, ema_long=50)
    
    # After warmup, downtrend should fail (negative derivative)
    assert not ema_filter['DOWN'].iloc[-20:].any()


def test_dual_ema_filter_mixed(mixed_prices):
    """Test filter on mixed scenarios."""
    ema_filter = get_dual_ema_filter(mixed_prices, ema_short=20, ema_long=50)
    
    # Check last row
    last_row = ema_filter.iloc[-1]
    
    # STRONG_UP should pass
    assert last_row['STRONG_UP'] == True
    
    # DOWNTREND should fail
    assert last_row['DOWNTREND'] == False


def test_apply_dual_ema_filter_to_roc(mixed_prices):
    """Test that ROC is filtered correctly."""
    filtered_roc = apply_dual_ema_filter_to_roc(
        mixed_prices,
        roc_period=21,
        ema_short=20,
        ema_long=50
    )
    
    # Check last row
    last_roc = filtered_roc.iloc[-1]
    
    # STRONG_UP should have ROC value (not NaN)
    assert not pd.isna(last_roc['STRONG_UP'])
    
    # DOWNTREND should be NaN (filtered out)
    assert pd.isna(last_roc['DOWNTREND'])


def test_strategy_with_dual_ema_cash_fallback(downtrend_prices):
    """Test that strategy goes to cash when nothing passes filter."""
    strategy = MomentumStrategy(
        momentum_period=21,
        top_n=1,
        use_ma_filter=True,
        ema_short=20,
        ema_long=50
    )
    
    signal_date = downtrend_prices.index[-1]
    position = strategy.get_position_for_date(downtrend_prices, signal_date)
    
    # Should return None (cash) when nothing passes filter
    assert position is None


def test_strategy_with_dual_ema_selects_eligible(mixed_prices):
    """Test that strategy selects from eligible symbols only."""
    strategy = MomentumStrategy(
        momentum_period=21,
        top_n=1,
        use_ma_filter=True,
        ema_short=20,
        ema_long=50
    )
    
    signal_date = mixed_prices.index[-1]
    position = strategy.get_position_for_date(mixed_prices, signal_date)
    
    # Should select an eligible symbol (not DOWNTREND)
    assert position is not None
    assert position != 'DOWNTREND'


def test_strategy_without_filter_selects_all(mixed_prices):
    """Test that strategy without filter can select any symbol."""
    strategy_no_filter = MomentumStrategy(
        momentum_period=21,
        top_n=1,
        use_ma_filter=False
    )
    
    signal_date = mixed_prices.index[-1]
    position = strategy_no_filter.get_position_for_date(mixed_prices, signal_date)
    
    # Should select something (not restricted by filter)
    assert position is not None


def test_ema_calculations_match_expected():
    """Test EMA values match expected calculations."""
    dates = pd.date_range(start='2020-01-01', periods=50, freq='D')
    # Flat prices to make calculation verification easier
    prices = pd.DataFrame({'FLAT': [100.0] * 50}, index=dates)
    
    ema = calculate_ema(prices, period=20)
    
    # For flat prices, EMA should converge to the price
    # Check last value (should be very close to 100)
    assert abs(ema['FLAT'].iloc[-1] - 100.0) < 1.0

