"""Tests for polymorphic momentum system."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.indicators import (
    calculate_tema,
    calculate_ema,
    calculate_double_ema,
    get_polymorphic_filter_bank
)
from src.polymorphic import (
    evaluate_single_filter,
    run_filter_bakeoff,
    PolymorphicMomentumStrategy
)


@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    dates = pd.date_range(start='2010-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    prices = pd.DataFrame({
        'STOCK_A': 100 * (1 + np.random.randn(len(dates)) * 0.02).cumprod(),
        'STOCK_B': 100 * (1 + np.random.randn(len(dates)) * 0.02).cumprod(),
        'STOCK_C': 100 * (1 + np.random.randn(len(dates)) * 0.02).cumprod(),
    }, index=dates)
    
    return prices


@pytest.fixture
def sample_rebalance_dates(sample_prices):
    """Generate monthly rebalance dates."""
    all_dates = sample_prices.index
    rebalance_dates = [all_dates[i] for i in range(0, len(all_dates), 21) if i < len(all_dates)]
    return rebalance_dates[:100]  # Limit to 100 for speed


class TestTEMAIndicator:
    """Test TEMA calculation."""
    
    def test_tema_basic(self, sample_prices):
        """Test TEMA returns correct shape and no NaN issues."""
        tema = calculate_tema(sample_prices, period=21)
        
        assert tema.shape == sample_prices.shape
        assert tema.columns.tolist() == sample_prices.columns.tolist()
        # TEMA has 3x the initial NaN period (3 * period - 2)
        assert tema.iloc[:59].isna().all().all()
    
    def test_tema_smoothness(self, sample_prices):
        """Test that TEMA is smoother than Double EMA."""
        double_ema = calculate_double_ema(sample_prices, period=21)
        tema = calculate_tema(sample_prices, period=21)
        
        # Calculate volatility (std dev) as proxy for smoothness
        double_ema_vol = double_ema.iloc[60:].std().mean()
        tema_vol = tema.iloc[60:].std().mean()
        
        # TEMA should be smoother (lower volatility)
        assert tema_vol < double_ema_vol
    
    def test_tema_different_periods(self, sample_prices):
        """Test TEMA with different periods."""
        tema_12 = calculate_tema(sample_prices, period=12)
        tema_63 = calculate_tema(sample_prices, period=63)
        
        # Longer period = more smoothing
        tema_12_vol = tema_12.iloc[100:].std().mean()
        tema_63_vol = tema_63.iloc[200:].std().mean()
        
        assert tema_63_vol < tema_12_vol


class TestFilterBank:
    """Test polymorphic filter bank generation."""
    
    def test_filter_bank_count(self):
        """Test that filter bank contains exactly 20 filters."""
        filters = get_polymorphic_filter_bank()
        assert len(filters) == 20
    
    def test_filter_bank_structure(self):
        """Test that all filters have correct structure."""
        filters = get_polymorphic_filter_bank()
        
        for f in filters:
            assert 'type' in f
            assert 'period' in f
            assert f['type'] in ['EMA', 'Double_EMA', 'TEMA']
            assert isinstance(f['period'], int)
            assert f['period'] > 0
    
    def test_filter_bank_composition(self):
        """Test filter bank has correct composition."""
        filters = get_polymorphic_filter_bank()
        
        # Count by type
        ema_count = sum(1 for f in filters if f['type'] == 'EMA')
        double_ema_count = sum(1 for f in filters if f['type'] == 'Double_EMA')
        tema_count = sum(1 for f in filters if f['type'] == 'TEMA')
        
        assert ema_count == 4
        assert double_ema_count == 8
        assert tema_count == 8


class TestSingleFilterEvaluation:
    """Test single filter evaluation."""
    
    def test_evaluate_single_filter_basic(self, sample_prices, sample_rebalance_dates):
        """Test that filter evaluation returns a score."""
        filter_config = {'type': 'EMA', 'period': 25}
        
        score = evaluate_single_filter(
            sample_prices,
            filter_config,
            sample_rebalance_dates,
            metric="Sharpe"
        )
        
        assert isinstance(score, float)
        assert not np.isnan(score)
    
    def test_evaluate_all_filter_types(self, sample_prices, sample_rebalance_dates):
        """Test evaluation works for all filter types."""
        filter_configs = [
            {'type': 'EMA', 'period': 25},
            {'type': 'Double_EMA', 'period': 45},
            {'type': 'TEMA', 'period': 63}
        ]
        
        for config in filter_configs:
            score = evaluate_single_filter(
                sample_prices,
                config,
                sample_rebalance_dates,
                metric="Sharpe"
            )
            assert isinstance(score, float)
    
    def test_evaluate_sharpe_vs_sortino(self, sample_prices, sample_rebalance_dates):
        """Test both Sharpe and Sortino metrics."""
        filter_config = {'type': 'EMA', 'period': 25}
        
        sharpe_score = evaluate_single_filter(
            sample_prices, filter_config, sample_rebalance_dates, metric="Sharpe"
        )
        sortino_score = evaluate_single_filter(
            sample_prices, filter_config, sample_rebalance_dates, metric="Sortino"
        )
        
        assert isinstance(sharpe_score, float)
        assert isinstance(sortino_score, float)


class TestFilterBakeoff:
    """Test filter bake-off system."""
    
    def test_bakeoff_returns_winner(self, sample_prices, sample_rebalance_dates):
        """Test that bake-off returns a valid winner."""
        winner = run_filter_bakeoff(
            sample_prices,
            sample_rebalance_dates,
            metric="Sharpe"
        )
        
        assert 'type' in winner
        assert 'period' in winner
        assert 'score' in winner
        assert 'all_scores' in winner
        
        assert winner['type'] in ['EMA', 'Double_EMA', 'TEMA']
        assert isinstance(winner['period'], int)
        assert isinstance(winner['score'], float)
    
    def test_bakeoff_all_scores_length(self, sample_prices, sample_rebalance_dates):
        """Test that all 20 filters are evaluated."""
        winner = run_filter_bakeoff(
            sample_prices,
            sample_rebalance_dates,
            metric="Sharpe"
        )
        
        assert len(winner['all_scores']) == 20
    
    def test_bakeoff_winner_is_best(self, sample_prices, sample_rebalance_dates):
        """Test that winner has highest score."""
        winner = run_filter_bakeoff(
            sample_prices,
            sample_rebalance_dates,
            metric="Sharpe"
        )
        
        all_scores = [s['score'] for s in winner['all_scores']]
        assert winner['score'] == max(all_scores)


class TestPolymorphicMomentumStrategy:
    """Test PolymorphicMomentumStrategy class."""
    
    def test_initialization(self):
        """Test strategy initialization."""
        strategy = PolymorphicMomentumStrategy(
            metric="Sharpe",
            initial_lookback_years=5,
            reeval_lookback_years=2
        )
        
        assert strategy.metric == "Sharpe"
        assert strategy.initial_lookback_years == 5
        assert strategy.reeval_lookback_years == 2
        assert not strategy.is_initialized
        assert strategy.active_filter is None
    
    def test_initial_bakeoff(self, sample_prices, sample_rebalance_dates):
        """Test initial filter selection."""
        strategy = PolymorphicMomentumStrategy(metric="Sharpe")
        
        current_date = sample_rebalance_dates[100]  # Use 100th rebalance
        
        strategy.initialize(sample_prices, sample_rebalance_dates, current_date)
        
        assert strategy.is_initialized
        assert strategy.active_filter is not None
        assert 'type' in strategy.active_filter
        assert 'period' in strategy.active_filter
        assert strategy.next_reeval_date is not None
    
    def test_should_reevaluate(self, sample_prices, sample_rebalance_dates):
        """Test re-evaluation timing."""
        strategy = PolymorphicMomentumStrategy(metric="Sharpe")
        
        # Initialize
        init_date = sample_rebalance_dates[100]
        strategy.initialize(sample_prices, sample_rebalance_dates, init_date)
        
        # Should not re-evaluate immediately
        assert not strategy.should_reevaluate(init_date)
        
        # Should re-evaluate after 3 months
        future_date = init_date + timedelta(days=95)
        assert strategy.should_reevaluate(future_date)
    
    def test_reevaluate(self, sample_prices, sample_rebalance_dates):
        """Test re-evaluation updates filter."""
        strategy = PolymorphicMomentumStrategy(metric="Sharpe")
        
        # Initialize
        init_date = sample_rebalance_dates[100]
        strategy.initialize(sample_prices, sample_rebalance_dates, init_date)
        
        original_filter = strategy.active_filter.copy()
        
        # Re-evaluate 3 months later
        reeval_date = init_date + timedelta(days=95)
        changed = strategy.reevaluate(sample_prices, sample_rebalance_dates, reeval_date)
        
        assert isinstance(changed, bool)
        assert strategy.active_filter is not None
    
    def test_filter_history(self, sample_prices, sample_rebalance_dates):
        """Test filter history tracking."""
        strategy = PolymorphicMomentumStrategy(metric="Sharpe")
        
        # Initialize
        init_date = sample_rebalance_dates[100]
        strategy.initialize(sample_prices, sample_rebalance_dates, init_date)
        
        # Check history has initial entry
        history = strategy.get_filter_history_df()
        assert len(history) == 1
        assert history.iloc[0]['is_reeval'] == False
        
        # Re-evaluate
        reeval_date = init_date + timedelta(days=95)
        strategy.reevaluate(sample_prices, sample_rebalance_dates, reeval_date)
        
        # Check history has two entries
        history = strategy.get_filter_history_df()
        assert len(history) == 2
        assert history.iloc[1]['is_reeval'] == True
    
    def test_get_current_filter(self, sample_prices, sample_rebalance_dates):
        """Test getting current active filter."""
        strategy = PolymorphicMomentumStrategy(metric="Sharpe")
        
        # Should raise error before initialization
        with pytest.raises(ValueError):
            strategy.get_current_filter()
        
        # Initialize
        init_date = sample_rebalance_dates[100]
        strategy.initialize(sample_prices, sample_rebalance_dates, init_date)
        
        # Should return valid filter
        current_filter = strategy.get_current_filter()
        assert 'type' in current_filter
        assert 'period' in current_filter
        assert 'score' in current_filter


class TestPolymorphicIntegration:
    """Integration tests for polymorphic system."""
    
    def test_full_workflow(self, sample_prices, sample_rebalance_dates):
        """Test complete polymorphic workflow."""
        strategy = PolymorphicMomentumStrategy(
            metric="Sharpe",
            initial_lookback_years=3,
            reeval_lookback_years=1
        )
        
        # Initialize
        init_date = sample_rebalance_dates[100]
        strategy.initialize(sample_prices, sample_rebalance_dates, init_date)
        
        # Simulate quarterly re-evaluations
        reeval_dates = [init_date + timedelta(days=95*i) for i in range(1, 4)]
        
        for reeval_date in reeval_dates:
            if strategy.should_reevaluate(reeval_date):
                strategy.reevaluate(sample_prices, sample_rebalance_dates, reeval_date)
        
        # Check history
        history = strategy.get_filter_history_df()
        assert len(history) >= 1  # At least initial selection
        
        # Verify all history entries are valid
        for _, row in history.iterrows():
            assert row['filter_type'] in ['EMA', 'Double_EMA', 'TEMA']
            assert row['filter_period'] > 0
            assert isinstance(row['score'], (int, float))
            assert isinstance(row['is_reeval'], bool)

