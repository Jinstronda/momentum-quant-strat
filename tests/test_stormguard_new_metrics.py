"""Unit tests for new StormGuard leading indicators."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.stormguard.metrics import (
    calculate_credit_risk_appetite,
    calculate_internal_breadth
)


class TestCreditRiskAppetite:
    """Test Credit Risk Appetite metric (HYG:IEF ratio)."""
    
    def test_credit_risk_bullish(self):
        """Test bullish credit risk (HYG outperforming IEF)."""
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        
        # HYG rising faster than IEF
        hyg = pd.Series(np.linspace(100, 150, 100), index=dates)
        ief = pd.Series(np.linspace(100, 110, 100), index=dates)
        
        credit_risk = calculate_credit_risk_appetite(hyg, ief)
        
        # Should be bullish in later period (fast > slow)
        assert credit_risk.iloc[70:].mean() > 0.5
    
    def test_credit_risk_bearish(self):
        """Test bearish credit risk (IEF outperforming HYG)."""
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        
        # IEF rising, HYG falling (flight to safety)
        hyg = pd.Series(np.linspace(100, 80, 100), index=dates)
        ief = pd.Series(np.linspace(100, 120, 100), index=dates)
        
        credit_risk = calculate_credit_risk_appetite(hyg, ief)
        
        # Should be bearish in later period (fast < slow)
        assert credit_risk.iloc[70:].mean() < 0.5


class TestInternalBreadth:
    """Test Internal Breadth metric (RSP vs SPY)."""
    
    def test_breadth_strong(self):
        """Test strong breadth (RSP outperforming SPY)."""
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        
        # RSP rising faster than SPY (strong breadth)
        spy = pd.Series(np.linspace(100, 120, 100), index=dates)
        rsp = pd.Series(np.linspace(100, 140, 100), index=dates)
        
        breadth = calculate_internal_breadth(spy, rsp, period=21)
        
        # Should be bullish (RSP ROC > SPY ROC)
        assert breadth.iloc[30:].mean() > 0.8
    
    def test_breadth_weak(self):
        """Test weak breadth (SPY outperforming RSP)."""
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        
        # SPY rising, RSP lagging (weak breadth - only large caps leading)
        spy = pd.Series(np.linspace(100, 150, 100), index=dates)
        rsp = pd.Series(np.linspace(100, 110, 100), index=dates)
        
        breadth = calculate_internal_breadth(spy, rsp, period=21)
        
        # Should be bearish (RSP ROC < SPY ROC)
        assert breadth.iloc[30:].mean() < 0.2


class TestStormGuardNewCalculator:
    """Test the new StormGuard calculator with 5 components."""
    
    def test_calculator_initialization(self):
        """Test calculator can be initialized."""
        from src.stormguard import StormGuardCalculator
        
        calc = StormGuardCalculator(
            volatility_threshold=40.0,
            false_alarm_days=10,
            early_return_threshold=0.75
        )
        
        assert calc.volatility_threshold == 40.0
        assert calc.state_machine.current_state == "BULL"
    
    def test_all_metrics_calculation(self):
        """Test that all 5 metrics can be calculated."""
        from src.stormguard import StormGuardCalculator
        
        dates = pd.date_range(start='2020-01-01', periods=100, freq='D')
        spy = pd.Series(np.linspace(100, 120, 100), index=dates)
        spy_vol = pd.Series([1000000] * 100, index=dates)
        vix = pd.Series([20] * 100, index=dates)
        hyg = pd.Series(np.linspace(100, 110, 100), index=dates)
        ief = pd.Series(np.linspace(100, 105, 100), index=dates)
        rsp = pd.Series(np.linspace(100, 115, 100), index=dates)
        
        calc = StormGuardCalculator()
        metrics = calc.calculate_all_metrics(spy, spy_vol, vix, hyg, ief, rsp)
        
        # Should have all 6 metrics (5 main + market_volatility)
        assert 'price_trend' in metrics
        assert 'money_flow' in metrics
        assert 'sentiment' in metrics
        assert 'credit_risk' in metrics
        assert 'internal_breadth' in metrics
        assert 'market_volatility' in metrics
        
        # Credit risk and breadth should be boolean series
        assert metrics['credit_risk'].dtype == bool
        assert metrics['internal_breadth'].dtype == bool

