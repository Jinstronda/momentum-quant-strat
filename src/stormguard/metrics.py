"""Pure metric calculation functions for StormGuard filter."""

import pandas as pd
import numpy as np


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def calculate_dema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Double Exponential Moving Average (Book's version)."""
    ema1 = calculate_ema(series, period)
    dema = calculate_ema(ema1, period)
    return dema


def calculate_obv(prices: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume (OBV)."""
    price_change = prices.diff()
    obv = pd.Series(index=prices.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(prices)):
        if price_change.iloc[i] > 0:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif price_change.iloc[i] < 0:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def calculate_price_trend(spy_prices: pd.Series) -> pd.Series:
    """
    Metric 1: Price-Trend.
    Formula: 21 × DEMA_50(SPY_Daily_Returns) × 100 + 0.5%
    
    Args:
        spy_prices: SPY price series
        
    Returns:
        Price-Trend series (in percentage points)
    """
    daily_returns = spy_prices.pct_change()
    dema_50_returns = calculate_dema(daily_returns, 50)
    price_trend = (21 * dema_50_returns) * 100 + 0.5
    return price_trend


def calculate_money_flow(spy_prices: pd.Series, spy_volume: pd.Series) -> pd.Series:
    """
    Metric 2: Money Flow (OBV proxy).
    Formula: OBV - SMA_50(OBV)
    Bullish when > 0 (OBV above its trend)
    
    Args:
        spy_prices: SPY price series
        spy_volume: SPY volume series
        
    Returns:
        Money Flow series (positive = bullish)
    """
    obv = calculate_obv(spy_prices, spy_volume)
    obv_sma_50 = calculate_sma(obv, 50)
    money_flow = obv - obv_sma_50
    return money_flow


def calculate_sentiment(vix_prices: pd.Series) -> pd.Series:
    """
    Metric 3: Sentiment (VIX proxy).
    Formula: SMA_50(VIX) - VIX
    Bullish when > 0 (VIX below its average = low fear)
    
    Args:
        vix_prices: VIX price series
        
    Returns:
        Sentiment series (positive = bullish, low fear)
    """
    vix_sma_50 = calculate_sma(vix_prices, 50)
    sentiment = vix_sma_50 - vix_prices
    return sentiment


def calculate_market_volatility(vix_prices: pd.Series) -> pd.Series:
    """
    Calculate Market Volatility metric.
    Formula: (2/3) × EMA_4(VIX)
    
    Args:
        vix_prices: VIX price series
        
    Returns:
        Market Volatility series
    """
    ema_4_vix = calculate_ema(vix_prices, 4)
    market_volatility = (2.0 / 3.0) * ema_4_vix
    return market_volatility


def calculate_credit_risk_appetite(
    hyg_prices: pd.Series,
    ief_prices: pd.Series,
    fast_period: int = 20,
    slow_period: int = 50
) -> pd.Series:
    """
    Metric 4: Credit Risk Appetite (NEW LEADING INDICATOR).
    
    Measures whether bond traders are seeking risk (HYG) or safety (IEF).
    This is a leading indicator that often changes weeks before SPY rolls over.
    
    Formula: HYG:IEF ratio momentum
    - risk_ratio = HYG / IEF
    - risk_ratio_fast = SMA_20(risk_ratio)
    - risk_ratio_slow = SMA_50(risk_ratio)
    - Bullish when fast > slow (credit markets seeking risk)
    
    Args:
        hyg_prices: HYG (High Yield Corporate Bonds) price series
        ief_prices: IEF (7-10 Year Treasuries) price series
        fast_period: Fast SMA period (default 20)
        slow_period: Slow SMA period (default 50)
        
    Returns:
        Boolean series (True = Bullish credit appetite, False = Risk-off)
    """
    # Align both series to common index before calculation
    hyg_aligned, ief_aligned = hyg_prices.align(ief_prices, join='inner')
    
    risk_ratio = hyg_aligned / ief_aligned
    fast = calculate_sma(risk_ratio, fast_period)
    slow = calculate_sma(risk_ratio, slow_period)
    return fast > slow


def calculate_internal_breadth(
    spy_prices: pd.Series,
    rsp_prices: pd.Series,
    period: int = 63
) -> pd.Series:
    """
    Metric 5: Internal Breadth (NEW LEADING INDICATOR).
    
    Compares S&P 500 (SPY - the "generals") to S&P 500 Equal Weight (RSP - the "troops").
    If generals are advancing but troops are not, internal strength is weak.
    
    Formula: RSP vs SPY momentum comparison
    - SPY_ROC = 63-day rate of change for SPY
    - RSP_ROC = 63-day rate of change for RSP
    - Bullish when RSP_ROC > SPY_ROC (troops keeping up with generals)
    
    Args:
        spy_prices: SPY (S&P 500) price series
        rsp_prices: RSP (S&P 500 Equal Weight) price series
        period: ROC calculation period (default 63 days)
        
    Returns:
        Boolean series (True = Bullish breadth, False = Weak breadth)
    """
    # Align both series to common index before calculation
    spy_aligned, rsp_aligned = spy_prices.align(rsp_prices, join='inner')
    
    spy_roc = spy_aligned.pct_change(period) * 100
    rsp_roc = rsp_aligned.pct_change(period) * 100
    
    return rsp_roc > spy_roc


def calculate_normalized_roc(
    metric_series: pd.Series,
    period: int = 10,
    volatility_window: int = 63
) -> pd.Series:
    """
    Calculate normalized rate-of-change using z-scores.
    
    Prevents exploding on near-zero values by normalizing change
    by the metric's own recent volatility.
    
    Formula: z-score = (current_change - mean_change) / std_change
    
    Args:
        metric_series: The metric values over time
        period: Lookback period for ROC calculation
        volatility_window: Window for calculating mean/std of changes
        
    Returns:
        Z-score series (negative values = deterioration)
    """
    # Calculate raw changes over period
    changes = metric_series.diff(periods=period)
    
    # Calculate rolling mean and std of changes
    mean_change = changes.rolling(window=volatility_window, min_periods=volatility_window).mean()
    std_change = changes.rolling(window=volatility_window, min_periods=volatility_window).std()
    
    # Avoid division by zero
    std_change = std_change.replace(0, np.nan)
    
    # Calculate z-score
    z_score = (changes - mean_change) / std_change
    
    return z_score


def get_credit_risk_spread_value(
    hyg_prices: pd.Series,
    ief_prices: pd.Series,
    fast_period: int = 20,
    slow_period: int = 50
) -> pd.Series:
    """
    Get the spread value (not boolean) for ROC tracking.
    
    Returns normalized spread: (fast_sma - slow_sma) / slow_sma
    This can be used for velocity detection.
    """
    hyg_aligned, ief_aligned = hyg_prices.align(ief_prices, join='inner')
    risk_ratio = hyg_aligned / ief_aligned
    fast = calculate_sma(risk_ratio, fast_period)
    slow = calculate_sma(risk_ratio, slow_period)
    
    # Normalized spread (avoid division by zero)
    spread = (fast - slow) / slow.replace(0, np.nan)
    
    return spread


def get_breadth_spread_value(
    spy_prices: pd.Series,
    rsp_prices: pd.Series,
    period: int = 63
) -> pd.Series:
    """
    Get the breadth spread value (not boolean) for ROC tracking.
    
    Returns: RSP_ROC - SPY_ROC (difference in momentum)
    Positive = healthy breadth, negative = weak breadth
    """
    spy_aligned, rsp_aligned = spy_prices.align(rsp_prices, join='inner')
    
    spy_roc = spy_aligned.pct_change(period) * 100
    rsp_roc = rsp_aligned.pct_change(period) * 100
    
    # Spread is the difference
    spread = rsp_roc - spy_roc
    
    return spread

