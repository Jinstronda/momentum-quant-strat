"""Adapted StormGuard-Armor Algorithm using SPY + VIX only.

This module implements an adapted version of StormGuard-Armor that maintains
the sophisticated state machine logic but uses free Yahoo Finance data (SPY + VIX).
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class StormGuardCalculator:
    """
    Adapted StormGuard calculator using only SPY and VIX data.
    
    Implements StormGuard philosophy with 3 metrics + volatility circuit breaker:
    1. Price-Trend: 21 × DEMA_50(SPY Returns) + 0.5%
    2. Money Flow (OBV Proxy): OBV - SMA_50(OBV)
    3. Sentiment (VIX Proxy): SMA_50(VIX) - VIX
    4. Volatility Circuit Breaker: (VIX > 40) AND (SPY < SMA_20)
    
    State machine tracks Bull/Bear transitions with asymmetric rules.
    """
    
    def __init__(
        self,
        volatility_threshold: float = 40.0,
        false_alarm_days: int = 10,
        early_return_threshold: float = 0.75
    ):
        """
        Initialize adapted StormGuard calculator.
        
        Args:
            volatility_threshold: VIX threshold for volatility circuit breaker (default 40)
            false_alarm_days: Days to check for false alarm validation (default 10)
            early_return_threshold: Rebound threshold for early return (default 0.75 = 75%)
        """
        self.volatility_threshold = volatility_threshold
        self.false_alarm_days = false_alarm_days
        self.early_return_threshold = early_return_threshold
        
        # State tracking
        self.current_state = "BULL"  # Start in bull market
        self.last_state_change_date = None
        self.prolonged_bear_ema = None
        
    def calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()
    
    def calculate_sma(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return series.rolling(window=period, min_periods=period).mean()
    
    def calculate_dema(self, series: pd.Series, period: int) -> pd.Series:
        """
        Calculate Double Exponential Moving Average (Book's version).
        DEMA = EMA(EMA(series))
        """
        ema1 = self.calculate_ema(series, period)
        dema = self.calculate_ema(ema1, period)
        return dema
    
    def calculate_obv(self, prices: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate On-Balance Volume (OBV).
        OBV adds volume on up days, subtracts on down days.
        """
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
    
    def calculate_price_trend(self, spy_prices: pd.Series) -> pd.Series:
        """
        Calculate Price-Trend metric.
        Formula: 21 × DEMA_50(SPY_Daily_Returns) + 0.5%
        
        Args:
            spy_prices: SPY price series
            
        Returns:
            Price-Trend series
        """
        # Calculate daily returns
        daily_returns = spy_prices.pct_change()
        
        # Apply 50-day DEMA to returns
        dema_50_returns = self.calculate_dema(daily_returns, 50)
        
        # Scale by 21 (monthly factor) and add 0.5% bias
        price_trend = 21 * dema_50_returns + 0.005
        
        return price_trend
    
    def calculate_money_flow(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series
    ) -> pd.Series:
        """
        Calculate Money Flow metric (OBV proxy).
        Formula: OBV - SMA_50(OBV)
        Bullish when > 0 (OBV above its trend)
        
        Args:
            spy_prices: SPY price series
            spy_volume: SPY volume series
            
        Returns:
            Money Flow series (positive = bullish)
        """
        # Calculate On-Balance Volume
        obv = self.calculate_obv(spy_prices, spy_volume)
        
        # Calculate 50-day SMA of OBV
        obv_sma_50 = self.calculate_sma(obv, 50)
        
        # Money Flow = OBV - SMA(OBV)
        # Positive when OBV is above its trend (bullish)
        money_flow = obv - obv_sma_50
        
        return money_flow
    
    def calculate_sentiment(
        self,
        vix_prices: pd.Series
    ) -> pd.Series:
        """
        Calculate Sentiment metric (VIX proxy).
        Formula: SMA_50(VIX) - VIX
        Bullish when > 0 (VIX below its average = low fear)
        
        Args:
            vix_prices: VIX price series
            
        Returns:
            Sentiment series (positive = bullish, low fear)
        """
        # Calculate 50-day SMA of VIX
        vix_sma_50 = self.calculate_sma(vix_prices, 50)
        
        # Sentiment = SMA(VIX) - VIX
        # Positive when VIX is below average (bullish)
        sentiment = vix_sma_50 - vix_prices
        
        return sentiment
    
    def calculate_market_volatility(self, vix_prices: pd.Series) -> pd.Series:
        """
        Calculate Market Volatility metric.
        Formula: (2/3) × EMA_4(VIX)
        
        Args:
            vix_prices: VIX price series
            
        Returns:
            Market Volatility series
        """
        # Apply 4-day EMA to VIX
        ema_4_vix = self.calculate_ema(vix_prices, 4)
        
        # Scale by 2/3
        market_volatility = (2.0 / 3.0) * ema_4_vix
        
        return market_volatility
    
    def calculate_all_metrics(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series
    ) -> Dict[str, pd.Series]:
        """
        Calculate all adapted StormGuard metrics.
        
        Args:
            spy_prices: SPY price series
            spy_volume: SPY volume series
            vix_prices: VIX price series
                
        Returns:
            Dictionary with all metrics as series
        """
        metrics = {}
        
        # Metric 1: Price-Trend
        metrics['price_trend'] = self.calculate_price_trend(spy_prices)
        
        # Metric 2: Money Flow (OBV proxy)
        metrics['money_flow'] = self.calculate_money_flow(spy_prices, spy_volume)
        
        # Metric 3: Sentiment (VIX proxy)
        metrics['sentiment'] = self.calculate_sentiment(vix_prices)
        
        # Metric 4: Market Volatility
        metrics['market_volatility'] = self.calculate_market_volatility(vix_prices)
        
        return metrics
    
    def is_metric_declining(self, metric_series: pd.Series, signal_date: datetime, lookback: int = 5) -> bool:
        """
        Check if a metric is declining (trend is negative).
        
        Args:
            metric_series: Metric time series
            signal_date: Date to check
            lookback: Days to look back (default 5)
            
        Returns:
            True if metric is declining
        """
        if signal_date not in metric_series.index:
            return False
        
        idx = metric_series.index.get_loc(signal_date)
        if idx < lookback:
            return False
        
        # Simple trend: compare current to average of recent past
        current_value = metric_series.iloc[idx]
        past_avg = metric_series.iloc[idx-lookback:idx].mean()
        
        return current_value < past_avg
    
    def check_false_alarm(
        self,
        spy_prices: pd.Series,
        signal_date: datetime
    ) -> bool:
        """
        False Alarm validation test.
        Prevents false bear signals at market highs.
        
        Checks if SPY hit a new high within last X days.
        
        Args:
            spy_prices: SPY price series
            signal_date: Date to check
            
        Returns:
            True if false alarm detected (should NOT trigger bear)
        """
        if signal_date not in spy_prices.index:
            return False
        
        idx = spy_prices.index.get_loc(signal_date)
        if idx < self.false_alarm_days:
            return False
        
        # Check if any recent days had new highs
        recent_prices = spy_prices.iloc[idx - self.false_alarm_days:idx+1]
        max_recent = recent_prices.max()
        current_price = spy_prices.iloc[idx]
        
        # If current price is near recent high (within 2%), it's a false alarm
        if current_price >= max_recent * 0.98:
            return True  # False alarm - at market highs
        
        return False
    
    def check_early_return(
        self,
        spy_prices: pd.Series,
        signal_date: datetime,
        lookback: int = 7
    ) -> bool:
        """
        Early Return validation test.
        Allows mid-month bull re-entry on sharp rebounds.
        
        Checks if SPY rebounded > 75% of its recent drop.
        
        Args:
            spy_prices: SPY price series
            signal_date: Date to check
            lookback: Days to measure drop (default 7)
            
        Returns:
            True if early return conditions met (should switch to bull)
        """
        if signal_date not in spy_prices.index:
            return False
        
        idx = spy_prices.index.get_loc(signal_date)
        if idx < lookback + 1:
            return False
        
        # Measure the drop from peak
        recent_prices = spy_prices.iloc[idx - lookback:idx+1]
        peak_price = recent_prices.max()
        trough_price = recent_prices.min()
        current_price = spy_prices.iloc[idx]
        
        if peak_price == trough_price:
            return False
        
        # Calculate rebound percentage
        drop = peak_price - trough_price
        rebound = current_price - trough_price
        rebound_pct = rebound / drop if drop > 0 else 0
        
        # Early return if rebounded > 75% of the drop
        return rebound_pct > self.early_return_threshold
    
    def update_prolonged_bear(
        self,
        spy_prices: pd.Series
    ):
        """
        Update Prolonged Bear indicator (90-day EMA of SPY returns).
        
        This indicator determines which exit rules to use when transitioning
        from Bear to Bull.
        
        Args:
            spy_prices: SPY price series
        """
        # Calculate daily returns
        daily_returns = spy_prices.pct_change()
        
        # Calculate 90-day EMA of returns
        self.prolonged_bear_ema = self.calculate_ema(daily_returns, 90)
    
    def is_month_end(self, signal_date: datetime, schedule: pd.DataFrame) -> bool:
        """
        Check if signal_date is a month-end (last trading day of month).
        
        Args:
            signal_date: Date to check
            schedule: Rebalance schedule DataFrame with dates
            
        Returns:
            True if month-end trading day
        """
        # Get month and year
        current_month = signal_date.month
        current_year = signal_date.year
        
        # Find next trading day
        dates_index = pd.DatetimeIndex(schedule['signal_date'])
        try:
            current_loc = dates_index.get_loc(signal_date, method='nearest')
        except:
            return False
        
        if current_loc + 1 < len(dates_index):
            next_date = dates_index[current_loc + 1]
            # If next date is in different month, this is month-end
            return next_date.month != current_month or next_date.year != current_year
        
        return False
    
    def check_volatility_circuit_breaker(
        self,
        spy_prices: pd.Series,
        vix_prices: pd.Series,
        signal_date: datetime
    ) -> bool:
        """
        Check volatility circuit breaker (mid-month panic detector).
        Triggers when: (VIX > 40) AND (SPY < SMA_20)
        
        Args:
            spy_prices: SPY price series
            vix_prices: VIX price series
            signal_date: Date to check
            
        Returns:
            True if circuit breaker should trigger (go to BEAR)
        """
        if signal_date not in vix_prices.index or signal_date not in spy_prices.index:
            return False
        
        # Check VIX threshold
        vix_value = vix_prices.loc[signal_date]
        if vix_value < self.volatility_threshold:
            return False
        
        # Check if SPY below SMA(20)
        spy_sma_20 = self.calculate_sma(spy_prices, 20)
        if signal_date not in spy_sma_20.index:
            return False
        
        spy_value = spy_prices.loc[signal_date]
        sma_value = spy_sma_20.loc[signal_date]
        
        # Trigger if VIX > 40 AND SPY < SMA(20)
        return spy_value < sma_value
    
    def get_market_state(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        signal_date: datetime,
        schedule: pd.DataFrame
    ) -> str:
        """
        Determine market state (BULL or BEAR) using adapted StormGuard logic.
        
        Implements the state machine with asymmetric transitions.
        
        Args:
            spy_prices: SPY price series up to signal_date
            spy_volume: SPY volume series up to signal_date
            vix_prices: VIX price series up to signal_date
            signal_date: Date to evaluate
            schedule: Rebalance schedule (for month-end detection)
            
        Returns:
            "BULL" or "BEAR"
        """
        # Calculate all metrics
        metrics = self.calculate_all_metrics(spy_prices, spy_volume, vix_prices)
        
        # Update Prolonged Bear indicator
        self.update_prolonged_bear(spy_prices)
        
        # Get current metric values
        if signal_date not in metrics['price_trend'].index:
            return self.current_state  # Keep current state if no data
        
        price_trend = metrics['price_trend'].loc[signal_date]
        money_flow = metrics['money_flow'].loc[signal_date]
        sentiment = metrics['sentiment'].loc[signal_date]
        
        is_month_end_day = self.is_month_end(signal_date, schedule)
        
        # BULL → BEAR Transitions
        if self.current_state == "BULL":
            # Month-end check: ANY metric < 0 AND declining
            if is_month_end_day:
                price_declining = self.is_metric_declining(metrics['price_trend'], signal_date)
                flow_declining = self.is_metric_declining(metrics['money_flow'], signal_date)
                sentiment_declining = self.is_metric_declining(metrics['sentiment'], signal_date)
                
                trigger_bear = False
                if price_trend < 0 and price_declining:
                    trigger_bear = True
                elif money_flow < 0 and flow_declining:
                    trigger_bear = True
                elif sentiment < 0 and sentiment_declining:
                    trigger_bear = True
                
                if trigger_bear:
                    # Check for False Alarm
                    if not self.check_false_alarm(spy_prices, signal_date):
                        self.current_state = "BEAR"
                        self.last_state_change_date = signal_date
                        print(f"[STORMGUARD] Bull->Bear on {signal_date.date()} (month-end)")
            
            # Any day: Volatility circuit breaker
            else:
                if self.check_volatility_circuit_breaker(spy_prices, vix_prices, signal_date):
                    self.current_state = "BEAR"
                    self.last_state_change_date = signal_date
                    print(f"[STORMGUARD] Bull->Bear on {signal_date.date()} (volatility spike)")
        
        # BEAR → BULL Transitions (depends on Prolonged Bear)
        elif self.current_state == "BEAR":
            prolonged_bear_value = (
                self.prolonged_bear_ema.loc[signal_date]
                if signal_date in self.prolonged_bear_ema.index
                else 0
            )
            
            # If Prolonged Bear > 0 (shallow bear): ANY metric > 0 (month-end) OR Early Return (any day)
            if prolonged_bear_value > 0:
                if is_month_end_day:
                    if price_trend > 0 or money_flow > 0 or sentiment > 0:
                        self.current_state = "BULL"
                        self.last_state_change_date = signal_date
                        print(f"[STORMGUARD] Bear->Bull on {signal_date.date()} (month-end, shallow bear)")
                else:
                    # Check Early Return
                    if self.check_early_return(spy_prices, signal_date):
                        self.current_state = "BULL"
                        self.last_state_change_date = signal_date
                        print(f"[STORMGUARD] Bear->Bull on {signal_date.date()} (early return)")
            
            # If Prolonged Bear < 0 (deep bear): BOTH Price-Trend AND Money Flow > 0 (month-end only)
            else:
                if is_month_end_day:
                    if price_trend > 0 and money_flow > 0:
                        self.current_state = "BULL"
                        self.last_state_change_date = signal_date
                        print(f"[STORMGUARD] Bear->Bull on {signal_date.date()} (month-end, deep bear recovery)")
        
        return self.current_state
    
    def get_metrics_for_date(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        signal_date: datetime
    ) -> Dict[str, float]:
        """
        Get all metric values for a specific date.
        
        Useful for reporting and diagnostics.
        
        Args:
            spy_prices: SPY price series
            spy_volume: SPY volume series
            vix_prices: VIX price series
            signal_date: Date to get metrics for
            
        Returns:
            Dictionary with metric values
        """
        metrics = self.calculate_all_metrics(spy_prices, spy_volume, vix_prices)
        
        result = {}
        for key, series in metrics.items():
            if signal_date in series.index:
                result[key] = series.loc[signal_date]
            else:
                result[key] = np.nan
        
        return result
