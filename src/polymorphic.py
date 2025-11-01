"""Polymorphic momentum system - automated filter selection."""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.indicators import calculate_momentum, get_polymorphic_filter_bank
from src.metrics import calculate_performance_metrics


def evaluate_single_filter(
    prices: pd.DataFrame,
    filter_config: Dict[str, any],
    rebalance_dates: List[datetime],
    metric: str = "Sharpe",
    initial_capital: float = 100000.0
) -> float:
    """
    Evaluate a single momentum filter over historical data.
    
    Runs simplified backtest: calculates momentum, selects top-1,
    simulates equity curve, returns performance metric.
    
    Args:
        prices: Historical price DataFrame
        filter_config: Dict with 'type' and 'period' keys
        rebalance_dates: List of rebalance dates
        metric: "Sharpe" or "Sortino"
        initial_capital: Starting capital
        
    Returns:
        Performance metric score (higher is better)
    """
    momentum_type = filter_config['type']
    momentum_period = filter_config['period']
    
    # Calculate momentum using this filter
    momentum = calculate_momentum(prices, momentum_type, momentum_period)
    
    # Simulate simple equity curve
    equity = initial_capital
    equity_curve = []
    dates = []
    current_position = None
    current_shares = 0
    
    for date in rebalance_dates:
        if date not in momentum.index or date not in prices.index:
            continue
            
        # Get momentum values for this date
        mom_values = momentum.loc[date].dropna()
        
        if len(mom_values) == 0:
            # No valid signals, go to cash
            new_position = None
        else:
            # Select top momentum asset
            new_position = mom_values.idxmax()
        
        # Handle position change
        if current_position != new_position:
            # Sell current position (if any)
            if current_position is not None and current_position in prices.columns:
                if date in prices.index:
                    exit_price = prices.loc[date, current_position]
                    equity = current_shares * exit_price
            
            # Buy new position (if any)
            if new_position is not None and new_position in prices.columns:
                if date in prices.index:
                    entry_price = prices.loc[date, new_position]
                    current_shares = equity / entry_price
            else:
                current_shares = 0
            
            current_position = new_position
        
        # Mark to market
        if current_position is not None and current_position in prices.columns:
            if date in prices.index:
                current_price = prices.loc[date, current_position]
                equity = current_shares * current_price
        
        equity_curve.append(equity)
        dates.append(date)
    
    # Convert to DataFrame for metrics calculation
    if len(equity_curve) < 2:
        return 0.0
    
    equity_df = pd.DataFrame({
        'equity': equity_curve
    }, index=dates)
    
    # Calculate metrics
    metrics = calculate_performance_metrics(equity_df, initial_capital)
    
    # Return requested metric
    if metric == "Sharpe":
        return metrics['Sharpe Ratio']
    elif metric == "Sortino":
        return metrics['Sortino Ratio']
    else:
        raise ValueError(f"Unknown metric: {metric}. Use 'Sharpe' or 'Sortino'")


def run_filter_bakeoff(
    prices: pd.DataFrame,
    rebalance_dates: List[datetime],
    metric: str = "Sharpe",
    initial_capital: float = 100000.0
) -> Dict[str, any]:
    """
    Run bake-off competition among all 20 filters.
    
    Evaluates each filter and returns the best performer.
    
    Args:
        prices: Historical price DataFrame
        rebalance_dates: List of rebalance dates
        metric: "Sharpe" or "Sortino"
        initial_capital: Starting capital for evaluation
        
    Returns:
        Dict with winner: {'type': 'Double_EMA', 'period': 63, 'score': 1.85}
    """
    filter_bank = get_polymorphic_filter_bank()
    
    best_filter = None
    best_score = -np.inf
    all_scores = []
    
    for filter_config in filter_bank:
        score = evaluate_single_filter(
            prices, filter_config, rebalance_dates, metric, initial_capital
        )
        
        all_scores.append({
            'type': filter_config['type'],
            'period': filter_config['period'],
            'score': score
        })
        
        if score > best_score:
            best_score = score
            best_filter = filter_config.copy()
    
    # Add score to winner
    best_filter['score'] = best_score
    best_filter['all_scores'] = all_scores  # For debugging/analysis
    
    return best_filter


class PolymorphicMomentumStrategy:
    """
    Manages polymorphic momentum filter selection.
    
    Tracks active filter, performs quarterly re-evaluation,
    and maintains filter history.
    """
    
    def __init__(
        self,
        metric: str = "Sharpe",
        initial_lookback_years: int = 5,
        reeval_lookback_years: int = 2,
        initial_capital: float = 100000.0
    ):
        """
        Initialize polymorphic momentum manager.
        
        Args:
            metric: "Sharpe" or "Sortino" for filter evaluation
            initial_lookback_years: Years of data for initial bake-off
            reeval_lookback_years: Years of data for quarterly re-evaluation
            initial_capital: Capital for filter evaluation
        """
        self.metric = metric
        self.initial_lookback_years = initial_lookback_years
        self.reeval_lookback_years = reeval_lookback_years
        self.initial_capital = initial_capital
        
        self.active_filter: Optional[Dict] = None
        self.next_reeval_date: Optional[datetime] = None
        self.filter_history: List[Dict] = []
        self.is_initialized = False
    
    def initialize(
        self,
        prices: pd.DataFrame,
        rebalance_dates: List[datetime],
        current_date: datetime
    ) -> None:
        """
        Run initial bake-off to select starting filter.
        
        Uses initial_lookback_years of history.
        
        Args:
            prices: Historical price DataFrame
            rebalance_dates: All rebalance dates
            current_date: Current date (start of forward trading)
        """
        # Get lookback window
        lookback_start = current_date - timedelta(days=self.initial_lookback_years * 365)
        
        # Filter prices and dates to lookback window
        eval_prices = prices[prices.index >= lookback_start]
        eval_prices = eval_prices[eval_prices.index <= current_date]
        
        eval_dates = [d for d in rebalance_dates if lookback_start <= d <= current_date]
        
        # Run bake-off
        winner = run_filter_bakeoff(
            eval_prices, eval_dates, self.metric, self.initial_capital
        )
        
        self.active_filter = {
            'type': winner['type'],
            'period': winner['period'],
            'score': winner['score']
        }
        
        # Schedule next re-evaluation (3 months)
        self.next_reeval_date = current_date + timedelta(days=90)
        
        # Record in history
        self.filter_history.append({
            'date': current_date,
            'filter_type': winner['type'],
            'filter_period': winner['period'],
            'score': winner['score'],
            'is_reeval': False
        })
        
        self.is_initialized = True
    
    def should_reevaluate(self, current_date: datetime) -> bool:
        """Check if it's time for quarterly re-evaluation."""
        if not self.is_initialized or self.next_reeval_date is None:
            return False
        return current_date >= self.next_reeval_date
    
    def reevaluate(
        self,
        prices: pd.DataFrame,
        rebalance_dates: List[datetime],
        current_date: datetime
    ) -> bool:
        """
        Run quarterly re-evaluation bake-off.
        
        Uses reeval_lookback_years of history.
        Returns True if filter changed.
        
        Args:
            prices: Historical price DataFrame
            rebalance_dates: All rebalance dates
            current_date: Current date
            
        Returns:
            True if filter changed, False otherwise
        """
        # Get lookback window
        lookback_start = current_date - timedelta(days=self.reeval_lookback_years * 365)
        
        # Filter prices and dates to lookback window
        eval_prices = prices[prices.index >= lookback_start]
        eval_prices = eval_prices[eval_prices.index <= current_date]
        
        eval_dates = [d for d in rebalance_dates if lookback_start <= d <= current_date]
        
        # Run bake-off
        winner = run_filter_bakeoff(
            eval_prices, eval_dates, self.metric, self.initial_capital
        )
        
        # Check if filter changed
        filter_changed = (
            winner['type'] != self.active_filter['type'] or
            winner['period'] != self.active_filter['period']
        )
        
        # Update active filter
        self.active_filter = {
            'type': winner['type'],
            'period': winner['period'],
            'score': winner['score']
        }
        
        # Schedule next re-evaluation (3 months)
        self.next_reeval_date = current_date + timedelta(days=90)
        
        # Record in history
        self.filter_history.append({
            'date': current_date,
            'filter_type': winner['type'],
            'filter_period': winner['period'],
            'score': winner['score'],
            'is_reeval': True
        })
        
        return filter_changed
    
    def get_current_filter(self) -> Dict[str, any]:
        """Get currently active filter configuration."""
        if not self.is_initialized:
            raise ValueError("Polymorphic strategy not initialized. Call initialize() first.")
        return self.active_filter
    
    def get_filter_history_df(self) -> pd.DataFrame:
        """Get filter history as DataFrame for reporting."""
        return pd.DataFrame(self.filter_history)

