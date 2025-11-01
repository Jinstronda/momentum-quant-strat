"""Shared performance metrics calculations."""

from typing import Dict
import pandas as pd
import numpy as np


def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    initial_capital: float
) -> Dict[str, float]:
    """
    Calculate performance metrics from equity curve.
    
    Used by both BacktestEngine and BenchmarkRunner to ensure consistency.
    
    Args:
        equity_curve: DataFrame with 'equity' column
        initial_capital: Initial capital amount
        
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
    
    # Calmar ratio (CAGR / abs(max drawdown))
    if max_drawdown != 0:
        calmar = abs(cagr_pct / max_drawdown)
    else:
        calmar = 0
    
    # Win rate (percentage of positive daily returns)
    win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100 if len(daily_returns) > 0 else 0
    
    # Average win/loss
    winning_days = daily_returns[daily_returns > 0]
    losing_days = daily_returns[daily_returns < 0]
    
    avg_win = winning_days.mean() * 100 if len(winning_days) > 0 else 0
    avg_loss = losing_days.mean() * 100 if len(losing_days) > 0 else 0
    
    # Final equity
    final_equity = equity.iloc[-1]
    
    return {
        'Initial Capital': initial_capital,
        'Final Equity': final_equity,
        'Total Return (%)': total_return,
        'CAGR (%)': cagr_pct,
        'Volatility (%)': volatility,
        'Sharpe Ratio': sharpe,
        'Max Drawdown (%)': max_drawdown,
        'Calmar Ratio': calmar,
        'Win Rate (%)': win_rate,
        'Avg Win (%)': avg_win,
        'Avg Loss (%)': avg_loss,
        'Total Trades': len(equity),
    }

