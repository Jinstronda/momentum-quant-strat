"""Tests for STORMGUARD filter components."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.indicators import (
    check_dema_price_trend,
    calculate_obv,
    check_obv_money_flow,
    check_vix_sentiment,
    calculate_double_ema
)


@pytest.fixture
def sample_spy_data():
    """Generate sample SPY price and volume data."""
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    # Generate trending prices
    trend = np.linspace(300, 450, len(dates))
    noise = np.random.randn(len(dates)) * 10
    prices = pd.Series(trend + noise, index=dates, name='SPY')
    
    # Generate volume (random around 80M)
    volume = pd.Series(
        80000000 + np.random.randn(len(dates)) * 10000000,
        index=dates,
        name='Volume'
    )
    volume = volume.abs()  # Ensure positive
    
    return prices, volume


@pytest.fixture
def sample_vix_data():
    """Generate sample VIX data."""
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
    np.random.seed(43)
    
    # VIX typically between 10-40
    vix = pd.Series(
        15 + np.abs(np.random.randn(len(dates)) * 5),
        index=dates,
        name='VIX'
    )
    
    return vix


class TestDEMAPriceTrend:
    """Test DEMA price trend component."""
    
    def test_dema_trend_basic(self, sample_spy_data):
        """Test DEMA trend returns boolean series."""
        prices, _ = sample_spy_data
        
        trend = check_dema_price_trend(prices, fast_period=50, slow_period=100)
        
        assert isinstance(trend, pd.Series)
        assert trend.dtype == bool
        assert len(trend) == len(prices)
    
    def test_dema_trend_uptrend(self):
        """Test DEMA detects uptrend."""
        dates = pd.date_range(start='2020-01-01', periods=200, freq='D')
        # Strong uptrend
        prices = pd.Series(range(100, 300), index=dates)
        
        trend = check_dema_price_trend(prices, fast_period=20, slow_period=50)
        
        # After enough data, should be mostly bullish in uptrend
        assert trend.iloc[100:].mean() > 0.5
    
    def test_dema_trend_downtrend(self):
        """Test DEMA detects downtrend."""
        dates = pd.date_range(start='2020-01-01', periods=200, freq='D')
        # Strong downtrend
        prices = pd.Series(range(300, 100, -1), index=dates)
        
        trend = check_dema_price_trend(prices, fast_period=20, slow_period=50)
        
        # After enough data, should be mostly bearish in downtrend
        assert trend.iloc[100:].mean() < 0.5


class TestOBVCalculation:
    """Test On-Balance Volume calculation."""
    
    def test_obv_basic(self, sample_spy_data):
        """Test OBV calculation returns series."""
        prices, volume = sample_spy_data
        
        obv = calculate_obv(prices, volume)
        
        assert isinstance(obv, pd.Series)
        assert len(obv) == len(prices)
        assert obv.iloc[0] == volume.iloc[0]
    
    def test_obv_up_days(self):
        """Test OBV increases on up days."""
        dates = pd.date_range(start='2020-01-01', periods=10, freq='D')
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], index=dates)
        volume = pd.Series([1000] * 10, index=dates)
        
        obv = calculate_obv(prices, volume)
        
        # OBV should be increasing (cumulative addition)
        assert obv.iloc[-1] > obv.iloc[0]
        assert obv.iloc[5] > obv.iloc[2]
    
    def test_obv_down_days(self):
        """Test OBV decreases on down days."""
        dates = pd.date_range(start='2020-01-01', periods=10, freq='D')
        prices = pd.Series([109, 108, 107, 106, 105, 104, 103, 102, 101, 100], index=dates)
        volume = pd.Series([1000] * 10, index=dates)
        
        obv = calculate_obv(prices, volume)
        
        # OBV should be decreasing (cumulative subtraction)
        assert obv.iloc[-1] < obv.iloc[0]
    
    def test_obv_mixed_days(self):
        """Test OBV handles mixed up/down days."""
        dates = pd.date_range(start='2020-01-01', periods=5, freq='D')
        prices = pd.Series([100, 101, 100, 102, 101], index=dates)
        volume = pd.Series([1000, 2000, 1500, 2500, 1000], index=dates)
        
        obv = calculate_obv(prices, volume)
        
        # OBV[1] = 1000 + 2000 = 3000 (up)
        # OBV[2] = 3000 - 1500 = 1500 (down)
        # OBV[3] = 1500 + 2500 = 4000 (up)
        # OBV[4] = 4000 - 1000 = 3000 (down)
        assert obv.iloc[0] == 1000
        assert obv.iloc[1] == 3000
        assert obv.iloc[2] == 1500
        assert obv.iloc[3] == 4000
        assert obv.iloc[4] == 3000


class TestOBVMoneyFlow:
    """Test OBV money flow signal."""
    
    def test_obv_flow_basic(self, sample_spy_data):
        """Test OBV flow returns boolean series."""
        prices, volume = sample_spy_data
        
        flow = check_obv_money_flow(prices, volume, sma_period=50)
        
        assert isinstance(flow, pd.Series)
        assert flow.dtype == bool
        assert len(flow) == len(prices)
    
    def test_obv_flow_bullish(self):
        """Test OBV flow detects accumulation."""
        dates = pd.date_range(start='2020-01-01', periods=150, freq='D')
        # Strong uptrend with increasing volume
        prices = pd.Series(range(100, 250), index=dates)
        volume = pd.Series(range(1000000, 1150000, 1000), index=dates)
        
        flow = check_obv_money_flow(prices, volume, sma_period=20)
        
        # Should be mostly bullish
        assert flow.iloc[50:].mean() > 0.5


class TestVIXSentiment:
    """Test VIX sentiment signal."""
    
    def test_vix_sentiment_basic(self, sample_vix_data):
        """Test VIX sentiment returns boolean series."""
        vix = sample_vix_data
        
        sentiment = check_vix_sentiment(vix, sma_period=50)
        
        assert isinstance(sentiment, pd.Series)
        assert sentiment.dtype == bool
        assert len(sentiment) == len(vix)
    
    def test_vix_adaptive_threshold(self):
        """Test VIX uses adaptive threshold."""
        dates = pd.date_range(start='2020-01-01', periods=200, freq='D')
        
        # Low vol regime (VIX ~15)
        vix_low = pd.Series([15] * 100 + [12] * 100, index=dates)
        sentiment_low = check_vix_sentiment(vix_low, sma_period=20)
        
        # In low vol regime, VIX=12 should be bullish (below avg of 15)
        assert sentiment_low.iloc[120:].mean() > 0.8
        
        # High vol regime (VIX ~30)
        vix_high = pd.Series([30] * 100 + [25] * 100, index=dates)
        sentiment_high = check_vix_sentiment(vix_high, sma_period=20)
        
        # In high vol regime, VIX=25 should be bullish (below avg of 30)
        assert sentiment_high.iloc[120:].mean() > 0.8
    
    def test_vix_fear_spike(self):
        """Test VIX detects fear spikes."""
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        
        # Normal VIX then spike
        vix_values = [15] * 50 + [35] * 50
        vix = pd.Series(vix_values, index=dates)
        
        sentiment = check_vix_sentiment(vix, sma_period=10)
        
        # After spike, should detect bearish sentiment
        assert sentiment.iloc[60:].mean() < 0.5


class TestStormGuardIntegration:
    """Integration tests for STORMGUARD system."""
    
    def test_all_components_together(self, sample_spy_data, sample_vix_data):
        """Test all 3 components work together."""
        spy_prices, spy_volume = sample_spy_data
        vix = sample_vix_data
        
        # Check all components
        price_trend = check_dema_price_trend(spy_prices, 50, 100)
        money_flow = check_obv_money_flow(spy_prices, spy_volume, 50)
        sentiment = check_vix_sentiment(vix, 50)
        
        # All should return boolean series of same length
        assert len(price_trend) == len(spy_prices)
        assert len(money_flow) == len(spy_prices)
        assert len(sentiment) == len(vix)
        
        # Combine (ALL must be true for bullish)
        is_bullish = price_trend & money_flow & sentiment
        
        assert isinstance(is_bullish, pd.Series)
        assert is_bullish.dtype == bool
    
    def test_any_bearish_triggers_rotation(self, sample_spy_data, sample_vix_data):
        """Test that ANY bearish component triggers rotation."""
        spy_prices, spy_volume = sample_spy_data
        vix = sample_vix_data
        
        price_trend = check_dema_price_trend(spy_prices, 50, 100)
        money_flow = check_obv_money_flow(spy_prices, spy_volume, 50)
        sentiment = check_vix_sentiment(vix, 50)
        
        # Create scenario where only 1 is bearish
        # (This is testing the logic, not specific market conditions)
        combined = price_trend & money_flow & sentiment
        
        # If any is False, combined should be False
        for i in range(len(combined)):
            if not price_trend.iloc[i]:
                assert not combined.iloc[i]
            if not money_flow.iloc[i]:
                assert not combined.iloc[i]
            if not sentiment.iloc[i]:
                assert not combined.iloc[i]

