"""State machine for Bull/Bear market regime transitions."""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class StormGuardStateMachine:
    """
    Manages Bull/Bear market state transitions with asymmetric rules.
    
    Implements sophisticated state machine with:
    - Asymmetric Bull→Bear and Bear→Bull transitions
    - False Alarm test (prevents triggers at market highs)
    - Early Return test (allows quick re-entry on rebounds)
    - Robust Bear→Bull rule requiring both Price-Trend AND Credit-Risk-Appetite
    """
    
    def __init__(
        self,
        volatility_threshold: float = 40.0,
        false_alarm_days: int = 10,
        early_return_threshold: float = 0.75,
        bear_exit_price_threshold: float = 1.5,
        min_bear_duration: int = 20,
        bear_exit_require_breadth: bool = True,
        bear_exit_require_majority: bool = False
    ):
        """
        Initialize state machine.
        
        Args:
            volatility_threshold: VIX threshold for circuit breaker
            false_alarm_days: Days to check for false alarm validation
            early_return_threshold: Rebound threshold for early return (0.75 = 75%)
            bear_exit_price_threshold: Minimum price_trend value to exit BEAR (default 1.5)
            min_bear_duration: Minimum days to stay in BEAR before allowing exit
            bear_exit_require_breadth: Require breadth confirmation for Bear→Bull
            bear_exit_require_majority: Require 4/5 metrics for Bear→Bull (very conservative)
        """
        self.volatility_threshold = volatility_threshold
        self.false_alarm_days = false_alarm_days
        self.early_return_threshold = early_return_threshold
        self.bear_exit_price_threshold = bear_exit_price_threshold
        self.min_bear_duration = min_bear_duration
        self.bear_exit_require_breadth = bear_exit_require_breadth
        self.bear_exit_require_majority = bear_exit_require_majority
        
        self.current_state = "BULL"
        self.last_state_change_date = None
    
    def update_state(
        self,
        signal_date: datetime,
        metric_values: Dict[str, float],
        metric_series: Dict[str, pd.Series],
        spy_prices: pd.Series,
        vix_prices: pd.Series,
        is_rebalance_day: bool
    ) -> str:
        """
        Update market state (BULL or BEAR).
        
        BULL → BEAR Transitions (NEW ROBUST LOGIC):
        - On rebalance day: Requires BOTH conditions to be true:
          * Metric 1 (Price-Trend) < 0 (primary trend is broken)
          * At least ONE leading indicator confirms weakness:
            - Metric 4 (Credit-Risk) is FALSE (smart money fleeing), OR
            - Metric 5 (Internal-Breadth) is FALSE (weak internals)
        - Any day: Volatility circuit breaker (VIX > 40 AND SPY < SMA_20)
        - Apply False Alarm test before triggering
        - This prevents whipsawing from brief dips in individual metrics
        
        BEAR → BULL Transitions (NEW ROBUST LOGIC):
        - On rebalance day only: Requires BOTH conditions to be true:
          * Metric 1 (Price-Trend) > 0 (primary trend is positive)
          * Metric 4 (Credit-Risk-Appetite) is bullish (smart money confirms)
        - Any day: Early Return test (75% rebound from recent drop)
        - This prevents "sucker's rallies" by requiring confirmation
          from both equities (Price-Trend) and credit markets (Credit-Risk-Appetite)
        
        Args:
            signal_date: Date to evaluate
            metric_values: Current values for all 5 metrics
            metric_series: Full series for trend analysis
            spy_prices: SPY price series
            vix_prices: VIX price series
            is_rebalance_day: Whether this is a rebalance day
            
        Returns:
            "BULL" or "BEAR"
        """
        # BULL → BEAR Transitions
        if self.current_state == "BULL":
            # Check rebalance day conditions
            if is_rebalance_day:
                trigger_bear = self._check_bear_triggers(
                    signal_date, metric_values, metric_series
                )
                
                if trigger_bear:
                    # Check for False Alarm
                    if not self._check_false_alarm(spy_prices, signal_date):
                        self.current_state = "BEAR"
                        self.last_state_change_date = signal_date
                        print(f"[STORMGUARD] Bull→Bear on {signal_date.date()} (rebalance day)")
            
            # Check volatility circuit breaker (any day)
            else:
                if self._check_volatility_circuit_breaker(spy_prices, vix_prices, signal_date):
                    self.current_state = "BEAR"
                    self.last_state_change_date = signal_date
                    print(f"[STORMGUARD] Bull→Bear on {signal_date.date()} (volatility spike)")
        
        # BEAR → BULL Transitions
        elif self.current_state == "BEAR":
            # Check minimum bear duration first
            if self.last_state_change_date is not None:
                days_in_bear = (signal_date - self.last_state_change_date).days
                if days_in_bear < self.min_bear_duration:
                    # Too soon to exit BEAR, stay defensive
                    return self.current_state
            
            # Check on rebalance days: Enhanced Bull triggers
            if is_rebalance_day:
                if self._check_bull_triggers(metric_values):
                    self.current_state = "BULL"
                    self.last_state_change_date = signal_date
                    print(f"[STORMGUARD] Bear→Bull on {signal_date.date()} (rebalance: confirmed recovery)")
            else:
                # Check Early Return (any day) - allows quick re-entry on sharp rebounds
                if self._check_early_return(spy_prices, signal_date):
                    self.current_state = "BULL"
                    self.last_state_change_date = signal_date
                    print(f"[STORMGUARD] Bear→Bull on {signal_date.date()} (early return)")
        
        return self.current_state
    
    def _check_bear_triggers(
        self,
        signal_date: datetime,
        metric_values: Dict[str, float],
        metric_series: Dict[str, pd.Series]
    ) -> bool:
        """
        Check if bear market conditions are met.
        
        NEW ROBUST RULE: Requires BOTH conditions:
        1. Price-Trend < 0 (primary trend is broken)
        2. At least ONE leading indicator confirms:
           - Credit-Risk is FALSE (smart money fleeing to safety), OR
           - Internal-Breadth is FALSE (weak market internals)
        
        This prevents whipsawing from brief dips in individual metrics.
        """
        # Metric 1: Price-Trend must be negative
        price_trend = metric_values.get('price_trend')
        if price_trend is None or price_trend >= 0:
            return False
        
        # Price trend is negative - now check for confirmation from leading indicators
        credit_risk = metric_values.get('credit_risk', True)
        breadth = metric_values.get('internal_breadth', True)
        
        # Trigger if at least ONE leading indicator confirms weakness
        leading_indicator_confirms = (not credit_risk) or (not breadth)
        
        return leading_indicator_confirms
    
    def _check_bull_triggers(self, metric_values: Dict[str, float]) -> bool:
        """
        Check if Bear→Bull exit conditions are met (HARDENED).
        
        Robust rule requires:
        1. Price-Trend > THRESHOLD (not just > 0, must be STRONG uptrend)
        2. Credit-Risk-Appetite is True (bond market confirms)
        3. Internal-Breadth is True (if require_breadth enabled - troops keeping up)
        4. OR: 4/5 metrics bullish (if require_majority enabled - very conservative)
        
        This prevents false signals from "sucker's rallies" and dead-cat bounces.
        """
        price_trend = metric_values.get('price_trend', 0)
        credit_risk = metric_values.get('credit_risk', False)
        internal_breadth = metric_values.get('internal_breadth', False)
        money_flow = metric_values.get('money_flow', 0)
        sentiment = metric_values.get('sentiment', 0)
        
        # Check if minimum bear duration has passed
        if self.last_state_change_date is not None:
            days_in_bear = (datetime.now() - self.last_state_change_date).days
            # Note: This is checked in update_state with actual signal_date
        
        # Majority vote mode (very conservative)
        if self.bear_exit_require_majority:
            bullish_count = sum([
                price_trend > self.bear_exit_price_threshold,
                credit_risk,
                internal_breadth,
                money_flow > 0,
                sentiment > 0
            ])
            return bullish_count >= 4  # 4 of 5 metrics must be bullish
        
        # Standard mode (recommended)
        # Require: Strong price trend + credit risk + breadth (if enabled)
        if price_trend <= self.bear_exit_price_threshold:
            return False
        
        if not credit_risk:
            return False
        
        if self.bear_exit_require_breadth and not internal_breadth:
            return False
        
        return True
    
    def _is_metric_declining(
        self,
        metric_series: pd.Series,
        signal_date: datetime,
        lookback: int = 5
    ) -> bool:
        """Check if a metric is declining (trend is negative)."""
        if signal_date not in metric_series.index:
            return False
        
        idx = metric_series.index.get_loc(signal_date)
        if idx < lookback:
            return False
        
        current_value = metric_series.iloc[idx]
        past_avg = metric_series.iloc[idx-lookback:idx].mean()
        
        return current_value < past_avg
    
    def _check_false_alarm(self, spy_prices: pd.Series, signal_date: datetime) -> bool:
        """
        False Alarm validation test.
        Prevents false bear signals at market highs.
        
        Returns True if false alarm detected (should NOT trigger bear).
        """
        if signal_date not in spy_prices.index:
            return False
        
        idx = spy_prices.index.get_loc(signal_date)
        if idx < self.false_alarm_days:
            return False
        
        recent_prices = spy_prices.iloc[idx - self.false_alarm_days:idx+1]
        max_recent = recent_prices.max()
        current_price = spy_prices.iloc[idx]
        
        # If within 2% of recent high, it's a false alarm
        return current_price >= max_recent * 0.98
    
    def _check_early_return(
        self,
        spy_prices: pd.Series,
        signal_date: datetime,
        lookback: int = 7
    ) -> bool:
        """
        Early Return validation test.
        Allows mid-period bull re-entry on sharp rebounds.
        
        Returns True if SPY rebounded > 75% of its recent drop.
        """
        if signal_date not in spy_prices.index:
            return False
        
        idx = spy_prices.index.get_loc(signal_date)
        if idx < lookback + 1:
            return False
        
        recent_prices = spy_prices.iloc[idx - lookback:idx+1]
        peak_price = recent_prices.max()
        trough_price = recent_prices.min()
        current_price = spy_prices.iloc[idx]
        
        if peak_price == trough_price:
            return False
        
        drop = peak_price - trough_price
        rebound = current_price - trough_price
        rebound_pct = rebound / drop if drop > 0 else 0
        
        return rebound_pct > self.early_return_threshold
    
    def _check_volatility_circuit_breaker(
        self,
        spy_prices: pd.Series,
        vix_prices: pd.Series,
        signal_date: datetime
    ) -> bool:
        """
        Check volatility circuit breaker (mid-period panic detector).
        Triggers when: (VIX > threshold) AND (SPY < SMA_20)
        """
        if signal_date not in vix_prices.index or signal_date not in spy_prices.index:
            return False
        
        vix_value = vix_prices.loc[signal_date]
        if vix_value < self.volatility_threshold:
            return False
        
        spy_sma_20 = spy_prices.rolling(window=20, min_periods=20).mean()
        if signal_date not in spy_sma_20.index:
            return False
        
        spy_value = spy_prices.loc[signal_date]
        sma_value = spy_sma_20.loc[signal_date]
        
        return spy_value < sma_value

