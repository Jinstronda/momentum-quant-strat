"""Benchmark comparison utilities."""

from typing import Dict, Tuple
import pandas as pd
import numpy as np


class BenchmarkRunner:
    """Run buy-and-hold benchmark strategies for comparison."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005
    ):
        """
        Initialize benchmark runner.
        
        Args:
            initial_capital: Starting capital
            commission_pct: Commission as percentage (0.001 = 0.1%)
            slippage_pct: Slippage as percentage (0.0005 = 0.05%)
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
    
    def run_buy_and_hold(
        self,
        prices: pd.Series,
        symbol: str = "Benchmark"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run a simple buy-and-hold strategy.
        
        Args:
            prices: Series with prices indexed by date
            symbol: Name of the benchmark
            
        Returns:
            Tuple of (equity_curve, trades)
        """
        if prices.empty:
            raise ValueError("Prices cannot be empty")
        
        # Calculate initial purchase
        entry_price = prices.iloc[0]
        transaction_cost = self.initial_capital * (self.commission_pct + self.slippage_pct)
        investable = self.initial_capital - transaction_cost
        shares = int(investable / entry_price)
        actual_cost = shares * entry_price
        cash = self.initial_capital - actual_cost - transaction_cost
        
        # Calculate equity for each day
        equity_data = []
        for date, price in prices.items():
            position_value = shares * price
            total_equity = cash + position_value
            
            equity_data.append({
                'date': date,
                'equity': total_equity,
                'cash': cash,
                'position_value': position_value,
                'position': symbol,
                'shares': shares
            })
        
        equity_df = pd.DataFrame(equity_data)
        equity_df.set_index('date', inplace=True)
        
        # Create trade record
        trades_df = pd.DataFrame([{
            'date': prices.index[0],
            'action': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': entry_price,
            'value': actual_cost,
            'cost': transaction_cost,
            'cash_after': cash
        }])
        
        return equity_df, trades_df
    
    def calculate_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate performance metrics from equity curve.
        
        Args:
            equity_curve: DataFrame with 'equity' column
            
        Returns:
            Dictionary of performance metrics
        """
        equity = equity_curve['equity']
        
        # Total return
        total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
        
        # Calculate daily returns
        daily_returns = equity.pct_change().dropna()
        
        # Annualized return (assuming 252 trading days)
        years = len(equity) / 252
        if years > 0:
            cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
            cagr_pct = cagr * 100
        else:
            cagr_pct = 0
        
        # Volatility (annualized)
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # Sharpe ratio (assuming 0% risk-free rate)
        if volatility > 0:
            sharpe = (cagr * 100) / volatility
        else:
            sharpe = 0
        
        # Maximum drawdown
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        if max_drawdown != 0:
            calmar = abs(cagr_pct / max_drawdown)
        else:
            calmar = 0
        
        # Win rate
        win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100 if len(daily_returns) > 0 else 0
        
        return {
            'Initial Capital': self.initial_capital,
            'Final Equity': equity.iloc[-1],
            'Total Return (%)': total_return,
            'CAGR (%)': cagr_pct,
            'Volatility (%)': volatility,
            'Sharpe Ratio': sharpe,
            'Max Drawdown (%)': max_drawdown,
            'Calmar Ratio': calmar,
            'Win Rate (%)': win_rate,
        }


def compare_strategies(
    strategy_equity: pd.DataFrame,
    benchmark_equity: pd.DataFrame,
    strategy_name: str = "Strategy",
    benchmark_name: str = "Benchmark"
) -> pd.DataFrame:
    """
    Compare two strategies side by side.
    
    Args:
        strategy_equity: Equity curve for main strategy
        benchmark_equity: Equity curve for benchmark
        strategy_name: Name of the strategy
        benchmark_name: Name of the benchmark
        
    Returns:
        DataFrame with comparative metrics
    """
    # Normalize both to start at 100
    strategy_normalized = strategy_equity['equity'] / strategy_equity['equity'].iloc[0] * 100
    benchmark_normalized = benchmark_equity['equity'] / benchmark_equity['equity'].iloc[0] * 100
    
    comparison = pd.DataFrame({
        strategy_name: strategy_normalized,
        benchmark_name: benchmark_normalized
    })
    
    # Calculate outperformance
    comparison['Outperformance'] = comparison[strategy_name] - comparison[benchmark_name]
    
    return comparison


def calculate_relative_metrics(
    strategy_metrics: Dict[str, float],
    benchmark_metrics: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate relative performance metrics.
    
    Args:
        strategy_metrics: Metrics for the strategy
        benchmark_metrics: Metrics for the benchmark
        
    Returns:
        Dictionary with comparative metrics
    """
    return {
        'Alpha (%)': strategy_metrics['CAGR (%)'] - benchmark_metrics['CAGR (%)'],
        'Relative Sharpe': strategy_metrics['Sharpe Ratio'] - benchmark_metrics['Sharpe Ratio'],
        'Relative Max DD (%)': strategy_metrics['Max Drawdown (%)'] - benchmark_metrics['Max Drawdown (%)'],
        'Relative Volatility (%)': strategy_metrics['Volatility (%)'] - benchmark_metrics['Volatility (%)'],
    }

