"""Technical indicators for momentum strategy."""

import pandas as pd
import numpy as np
from typing import Optional


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


def calculate_moving_average(prices: pd.DataFrame, period: int = 200) -> pd.DataFrame:
    """Calculate simple moving average (only used in tests for comparison)."""
    return prices.rolling(window=period, min_periods=period).mean()


def calculate_ema(prices: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Calculate exponential moving average for prices.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: EMA period (default 20 days)
        
    Returns:
        DataFrame with EMA values, same shape as input
    """
    return prices.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_double_ema(prices: pd.DataFrame, period: int = 21) -> pd.DataFrame:
    """
    Calculate Double EMA (smoothed) - EMA of EMA.
    
    Purpose: Maximum smoothing, noise reduction, slow trend-following.
    Very smooth and far from price. Only catches major multi-month trends.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: EMA period (default 21 days)
        
    Returns:
        DataFrame with Double EMA values
    """
    ema1 = calculate_ema(prices, period)
    ema2 = calculate_ema(ema1, period)
    return ema2


def calculate_dema(prices: pd.DataFrame, period: int = 21) -> pd.DataFrame:
    """
    Calculate DEMA (technical) - reduces lag while smoothing.
    Formula: 2*EMA - EMA(EMA)
    
    Purpose: Faster response than EMA, less lag, moderate smoothing.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: DEMA period (default 21 days)
        
    Returns:
        DataFrame with DEMA values
    """
    ema1 = calculate_ema(prices, period)
    ema2 = calculate_ema(ema1, period)
    return 2 * ema1 - ema2


def calculate_momentum(
    prices: pd.DataFrame,
    method: str = "ROC",
    period: int = 21
) -> pd.DataFrame:
    """
    Calculate momentum using specified method.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        method: "ROC", "Double_EMA", or "DEMA"
        period: Lookback period in days
        
    Returns:
        DataFrame with momentum values
    """
    if method == "ROC":
        return calculate_roc(prices, period)
    elif method == "Double_EMA":
        return calculate_double_ema(prices, period)
    elif method == "DEMA":
        return calculate_dema(prices, period)
    else:
        raise ValueError(f"Unknown momentum method: {method}. Use 'ROC', 'Double_EMA', or 'DEMA'")


def calculate_ema_derivative(ema: pd.DataFrame, lookback: int = 1) -> pd.DataFrame:
    """
    Calculate derivative (slope) of EMA.
    
    Positive derivative = EMA trending up
    Negative derivative = EMA trending down
    
    Args:
        ema: DataFrame with EMA values
        lookback: Number of periods for derivative calculation (default 1 = day-to-day change)
        
    Returns:
        DataFrame with derivative values (change per period)
    """
    return ema.diff(lookback)


def get_dual_ema_filter(
    prices: pd.DataFrame,
    ema_short: int = 20,
    ema_long: int = 50,
    derivative_lookback: int = 1
) -> pd.DataFrame:
    """
    Create eligibility filter based on dual EMA system.
    
    Eligibility Rules (ALL must be true):
    1. Price > 20 EMA
    2. 20 EMA > 50 EMA
    3. 50 EMA derivative > 0 (trending up)
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        ema_short: Short EMA period (default 20)
        ema_long: Long EMA period (default 50)
        derivative_lookback: Periods for derivative calculation (default 1)
        
    Returns:
        DataFrame with True where eligible, False otherwise
    """
    # Calculate EMAs
    ema_20 = calculate_ema(prices, ema_short)
    ema_50 = calculate_ema(prices, ema_long)
    
    # Calculate 50 EMA derivative (slope)
    ema_50_derivative = calculate_ema_derivative(ema_50, derivative_lookback)
    
    # Apply all three conditions
    condition_1 = prices > ema_20                    # Price above 20 EMA
    condition_2 = ema_20 > ema_50                    # 20 EMA above 50 EMA
    condition_3 = ema_50_derivative > 0              # 50 EMA trending up
    
    # All conditions must be True
    eligible = condition_1 & condition_2 & condition_3
    
    return eligible


def apply_dual_ema_filter_to_momentum(
    prices: pd.DataFrame,
    momentum_type: str = "ROC",
    momentum_period: int = 21,
    ema_short: int = 20,
    ema_long: int = 50,
    derivative_lookback: int = 10
) -> pd.DataFrame:
    """
    Calculate momentum but set to NaN for symbols that don't pass dual EMA filter.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        momentum_type: "ROC" or "DEMA"
        momentum_period: Momentum lookback period
        ema_short: Short EMA period
        ema_long: Long EMA period
        derivative_lookback: Days to look back for 50 EMA derivative (slope)
        
    Returns:
        DataFrame with momentum values (NaN where not eligible)
    """
    momentum = calculate_momentum(prices, momentum_type, momentum_period)
    ema_filter = get_dual_ema_filter(prices, ema_short, ema_long, derivative_lookback)
    return momentum.where(ema_filter, np.nan)


# Legacy alias for backward compatibility with tests
def apply_dual_ema_filter_to_roc(
    prices: pd.DataFrame,
    roc_period: int = 21,
    ema_short: int = 20,
    ema_long: int = 50,
    derivative_lookback: int = 10
) -> pd.DataFrame:
    """Legacy wrapper - use apply_dual_ema_filter_to_momentum instead."""
    return apply_dual_ema_filter_to_momentum(
        prices, "ROC", roc_period, ema_short, ema_long, derivative_lookback
    )
