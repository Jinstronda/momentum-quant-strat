"""Technical indicators for momentum strategy."""

import pandas as pd
import numpy as np


def calculate_roc(prices: pd.DataFrame, period: int = 21) -> pd.DataFrame:
    """
    Calculate Rate of Change (ROC) indicator.
    
    ROC measures the percentage change in price over a specified period.
    Formula: ROC = (Price_today - Price_N_days_ago) / Price_N_days_ago * 100
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: Number of periods to look back (default 21 trading days ≈ 1 month)
        
    Returns:
        DataFrame with ROC values, same shape as input
    """
    # Calculate percentage change over the period
    roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
    
    return roc


def calculate_momentum_rank(
    prices: pd.DataFrame,
    period: int = 21,
    ascending: bool = False
) -> pd.DataFrame:
    """
    Calculate momentum rank across symbols for each date.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: Number of periods for ROC calculation
        ascending: If True, rank in ascending order (lowest = 1)
        
    Returns:
        DataFrame with ranks (1 = best momentum)
    """
    roc = calculate_roc(prices, period)
    
    # Rank across columns (symbols) for each row (date)
    # rank(ascending=False) means highest value gets rank 1
    ranks = roc.rank(axis=1, method='first', ascending=ascending)
    
    return ranks


def get_top_n_symbols(
    prices: pd.DataFrame,
    period: int = 21,
    top_n: int = 1
) -> pd.DataFrame:
    """
    Get top N symbols by momentum for each date.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: Number of periods for ROC calculation
        top_n: Number of top symbols to select
        
    Returns:
        DataFrame with 1 where symbol is in top N, 0 otherwise
    """
    ranks = calculate_momentum_rank(prices, period, ascending=False)
    
    # Create boolean mask for top N
    top_mask = ranks <= top_n
    
    return top_mask.astype(int)


def get_top_symbol_per_date(
    prices: pd.DataFrame,
    period: int = 21
) -> pd.Series:
    """
    Get the single best symbol by momentum for each date.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: Number of periods for ROC calculation
        
    Returns:
        Series with symbol names indexed by date
    """
    roc = calculate_roc(prices, period)
    
    # Get the column (symbol) with max ROC for each row (date)
    top_symbols = roc.idxmax(axis=1)
    
    return top_symbols
