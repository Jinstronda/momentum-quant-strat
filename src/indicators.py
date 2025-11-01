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
    """Calculate simple moving average."""
    return prices.rolling(window=period, min_periods=period).mean()


def check_market_safety(
    spy_prices: pd.Series,
    sma_short: int = 50,
    sma_long: int = 200
) -> pd.Series:
    """
    Safety Switch: Check if market is in bull regime.
    
    Logic: SMA(50) > SMA(200) → Bull (safe to trade)
           SMA(50) < SMA(200) → Bear (go to cash)
    
    Args:
        spy_prices: SPY price series
        sma_short: Short SMA period (default 50)
        sma_long: Long SMA period (default 200)
        
    Returns:
        Boolean series: True = Bull (safe), False = Bear (cash)
    """
    sma_50 = spy_prices.rolling(window=sma_short, min_periods=sma_short).mean()
    sma_200 = spy_prices.rolling(window=sma_long, min_periods=sma_long).mean()
    return sma_50 > sma_200


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


def calculate_tema(prices: pd.DataFrame, period: int = 21) -> pd.DataFrame:
    """
    Calculate TEMA (book's triple smoothing) - EMA(EMA(EMA)).
    
    Purpose: Maximum smoothing with triple filtering. Extremely slow response,
    captures only major long-term trends with minimal noise.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        period: EMA period (default 21 days)
        
    Returns:
        DataFrame with TEMA values (triple smoothed)
    """
    ema1 = calculate_ema(prices, period)
    ema2 = calculate_ema(ema1, period)
    ema3 = calculate_ema(ema2, period)
    return ema3


def calculate_momentum(
    prices: pd.DataFrame,
    method: str = "ROC",
    period: int = 21
) -> pd.DataFrame:
    """
    Calculate momentum using specified method.
    
    All methods return NORMALIZED percentage values for cross-asset comparison.
    EMA-based methods calculate percentage change of smoothed prices.
    
    Args:
        prices: DataFrame with symbols as columns, dates as index
        method: "ROC", "EMA", "Double_EMA", "DEMA", or "TEMA"
        period: Lookback period in days
        
    Returns:
        DataFrame with momentum values (percentages, normalized across assets)
    """
    if method == "ROC":
        # Already normalized (percentage change)
        return calculate_roc(prices, period)
    elif method == "EMA":
        # Normalize: percentage change of EMA over period
        ema = calculate_ema(prices, period)
        return ((ema - ema.shift(period)) / ema.shift(period)) * 100
    elif method == "Double_EMA":
        # Normalize: percentage change of Double EMA over period
        double_ema = calculate_double_ema(prices, period)
        return ((double_ema - double_ema.shift(period)) / double_ema.shift(period)) * 100
    elif method == "DEMA":
        # Normalize: percentage change of DEMA over period
        dema = calculate_dema(prices, period)
        return ((dema - dema.shift(period)) / dema.shift(period)) * 100
    elif method == "TEMA":
        # Normalize: percentage change of TEMA over period
        tema = calculate_tema(prices, period)
        return ((tema - tema.shift(period)) / tema.shift(period)) * 100
    else:
        raise ValueError(f"Unknown momentum method: {method}. Use 'ROC', 'EMA', 'Double_EMA', 'DEMA', or 'TEMA'")


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


def get_polymorphic_filter_bank() -> list:
    """
    Generate the 20-filter bank for polymorphic momentum.
    
    Returns list of dicts with 'type' and 'period' keys:
    - 4 EMA filters: periods [12, 25, 45, 63]
    - 8 DEMA (Double_EMA) filters: periods [12, 25, 45, 63, 75, 90, 105, 120]
    - 8 TEMA filters: periods [12, 25, 45, 63, 75, 90, 105, 120]
    
    Total: 20 filters for automated quarterly selection.
    """
    filters = []
    
    # 4 EMA filters
    for period in [12, 25, 45, 63]:
        filters.append({'type': 'EMA', 'period': period})
    
    # 8 DEMA (Double_EMA) filters
    for period in [12, 25, 45, 63, 75, 90, 105, 120]:
        filters.append({'type': 'Double_EMA', 'period': period})
    
    # 8 TEMA (Triple EMA) filters
    for period in [12, 25, 45, 63, 75, 90, 105, 120]:
        filters.append({'type': 'TEMA', 'period': period})
    
    return filters


# ============================================================================
# STORMGUARD FILTER COMPONENTS
# ============================================================================

def check_dema_price_trend(
    spy_prices: pd.Series,
    fast_period: int = 50,
    slow_period: int = 100
) -> pd.Series:
    """
    DEMA-based price trend (smoother than SMA crossover).
    
    Uses book's Double EMA for noise reduction.
    Returns True when DEMA(50) > DEMA(100) → Bullish price trend
    
    Args:
        spy_prices: SPY price series
        fast_period: Fast DEMA period (default 50)
        slow_period: Slow DEMA period (default 100)
        
    Returns:
        Boolean series: True = Bullish trend, False = Bearish trend
    """
    prices_df = spy_prices.to_frame()
    
    dema_fast = calculate_double_ema(prices_df, fast_period).iloc[:, 0]
    dema_slow = calculate_double_ema(prices_df, slow_period).iloc[:, 0]
    
    return dema_fast > dema_slow


def calculate_obv(prices: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV).
    
    OBV is a cumulative indicator that adds volume on up days
    and subtracts volume on down days. Measures money flow.
    
    Formula:
    - If Close > Previous_Close: OBV = Previous_OBV + Volume
    - If Close < Previous_Close: OBV = Previous_OBV - Volume
    - If Close == Previous_Close: OBV = Previous_OBV
    
    Args:
        prices: Price series
        volume: Volume series
        
    Returns:
        OBV series (cumulative volume flow)
    """
    price_change = prices.diff()
    obv = pd.Series(0.0, index=prices.index, dtype=float)
    
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(prices)):
        if price_change.iloc[i] > 0:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif price_change.iloc[i] < 0:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def check_obv_money_flow(
    spy_prices: pd.Series,
    spy_volume: pd.Series,
    sma_period: int = 50
) -> pd.Series:
    """
    OBV-based money flow check.
    
    Returns True when OBV > OBV_SMA(50) → Money flowing into market
    
    Args:
        spy_prices: SPY price series
        spy_volume: SPY volume series
        sma_period: SMA period for OBV smoothing (default 50)
        
    Returns:
        Boolean series: True = Money flowing in (bullish), False = Flowing out (bearish)
    """
    obv = calculate_obv(spy_prices, spy_volume)
    obv_sma = obv.rolling(window=sma_period, min_periods=sma_period).mean()
    
    return obv > obv_sma


def check_vix_sentiment(
    vix_prices: pd.Series,
    sma_period: int = 50
) -> pd.Series:
    """
    VIX-based market sentiment with ADAPTIVE threshold.
    
    Compares VIX to its own moving average (adapts to volatility regime).
    Returns True when VIX < VIX_SMA(50) → Fear below recent average (bullish)
    
    Why adaptive:
    - 2017: VIX averaged ~10-12 (low vol regime)
    - 2020-2022: VIX averaged ~25-30 (high vol regime)
    - Fixed threshold would miss rallies in high-vol periods
    - Adaptive detects fear RELATIVE to recent normal
    
    Args:
        vix_prices: VIX price series
        sma_period: SMA period for adaptive threshold (default 50)
        
    Returns:
        Boolean series: True = Low fear (bullish), False = Elevated fear (bearish)
    """
    vix_sma = vix_prices.rolling(window=sma_period, min_periods=sma_period).mean()
    return vix_prices < vix_sma
