"""Three-state machine for StormGuard Velocity mode."""

from typing import Dict
from datetime import datetime
import pandas as pd
from .state_machine import StormGuardStateMachine


class StormGuardVelocityStateMachine(StormGuardStateMachine):
    """
    Enhanced state machine: BULL → WATCH → BEAR
    
    Adds velocity detection and WATCH state to original StormGuard.
    """
    
    def __init__(
        self,
        volatility_threshold: float = 40.0,
        volatility_watch_threshold: float = 25.0,
        false_alarm_days: int = 30,
        early_return_threshold: float = 0.75,
        bear_exit_price_threshold: float = 1.5,
        min_bear_duration: int = 20,
        bear_exit_require_breadth: bool = True,
        bear_exit_require_majority: bool = False,
        roc_period: int = 10,
        roc_zscore_threshold: float = -2.0,
        roc_volatility_window: int = 63,
        min_dwell_days: int = 10,
        min_watch_dwell: int = 5,
        watch_timeout_days: int = 20
    ):
        super().__init__(
            volatility_threshold,
            volatility_watch_threshold,
            false_alarm_days,
            early_return_threshold,
            bear_exit_price_threshold,
            min_bear_duration,
            bear_exit_require_breadth,
            bear_exit_require_majority
        )
        
        # Velocity settings
        self.roc_period = roc_period
        self.roc_zscore_threshold = roc_zscore_threshold
        self.roc_volatility_window = roc_volatility_window
        
        # Hysteresis settings
        self.min_dwell_days = min_dwell_days
        self.min_watch_dwell = min_watch_dwell
        self.watch_timeout_days = watch_timeout_days
        
        # State tracking
        self.current_state = "BULL"  # BULL, WATCH, or BEAR
        self.watch_entry_date = None
    
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
        Update three-state machine: BULL → WATCH → BEAR
        
        Uses two-tier volatility thresholds:
        - VIX > 25: BULL → WATCH (moderate concern)
        - VIX > 40: → BEAR (emergency)
        """
        # Check minimum dwell time (except for extreme emergencies)
        vix_current = vix_prices.loc[signal_date] if signal_date in vix_prices.index else 0
        is_extreme_panic = vix_current > 50  # Black Monday level
        
        if not is_extreme_panic and not self._can_change_state(signal_date):
            return self.current_state
        
        # Two-tier volatility check
        # Moderate volatility: BULL → WATCH
        if self.current_state == "BULL":
            if self._check_moderate_volatility(spy_prices, vix_prices, signal_date):
                self._transition_to("WATCH", signal_date, "moderate volatility (VIX > 25)")
                return self.current_state
        
        # Emergency circuit breaker: → BEAR (VIX > 40)
        if self._check_volatility_circuit_breaker(spy_prices, vix_prices, signal_date):
            if self.current_state != "BEAR":
                self._transition_to("BEAR", signal_date, "emergency circuit breaker (VIX > 40)")
            return self.current_state
        
        # All other checks only on rebalance days
        if not is_rebalance_day:
            return self.current_state
        
        # Compute velocity warnings
        velocity_warnings = self._check_velocity_deterioration(signal_date, metric_series)
        
        # State transitions
        if self.current_state == "BULL":
            self._handle_bull_state(signal_date, metric_values, spy_prices, velocity_warnings)
        elif self.current_state == "WATCH":
            self._handle_watch_state(signal_date, metric_values, velocity_warnings)
        elif self.current_state == "BEAR":
            self._handle_bear_state(signal_date, metric_values)
        
        return self.current_state
    
    def _can_change_state(self, signal_date: datetime) -> bool:
        """Check if minimum dwell time has passed."""
        if self.last_state_change_date is None:
            return True
        
        days_in_state = (signal_date - self.last_state_change_date).days
        return days_in_state >= self.min_dwell_days
    
    def _transition_to(self, new_state: str, signal_date: datetime, reason: str):
        """Handle state transition with logging."""
        old_state = self.current_state
        self.current_state = new_state
        self.last_state_change_date = signal_date
        
        if new_state == "WATCH":
            self.watch_entry_date = signal_date
        elif new_state == "BULL":
            self.watch_entry_date = None
        
        print(f"[STORMGUARD-V] {old_state}→{new_state} on {signal_date.date()} ({reason})")
    
    def _handle_bull_state(
        self,
        signal_date: datetime,
        metric_values: Dict[str, float],
        spy_prices: pd.Series,
        velocity_warnings: list
    ):
        """Handle transitions from BULL state."""
        price_trend = metric_values.get('price_trend', 0)
        credit_risk = metric_values.get('credit_risk', True)
        breadth = metric_values.get('internal_breadth', True)
        
        # BULL → BEAR (strong signal)
        if price_trend < 0 and ((not credit_risk) or (not breadth)):
            if not self._check_false_alarm(spy_prices, signal_date):
                self._transition_to("BEAR", signal_date, "price trend + leader bearish")
                return
        
        # BULL → WATCH (early warning)
        # Enter WATCH if velocity warnings detected
        if len(velocity_warnings) > 0:
            self._transition_to("WATCH", signal_date, f"velocity warnings: {velocity_warnings}")
            return
    
    def _handle_watch_state(
        self,
        signal_date: datetime,
        metric_values: Dict[str, float],
        velocity_warnings: list
    ):
        """Handle transitions from WATCH state."""
        price_trend = metric_values.get('price_trend', 0)
        credit_risk = metric_values.get('credit_risk', True)
        breadth = metric_values.get('internal_breadth', True)
        
        # Check minimum WATCH dwell time
        days_in_watch = (signal_date - self.watch_entry_date).days if self.watch_entry_date else 0
        if days_in_watch < self.min_watch_dwell:
            return  # Must stay in WATCH for minimum period
        
        # WATCH → BEAR (confirmation arrived)
        if price_trend < 0 and ((not credit_risk) or (not breadth)):
            self._transition_to("BEAR", signal_date, "WATCH confirmation")
            return
        
        # WATCH → BULL (timeout or recovery)
        if days_in_watch > self.watch_timeout_days:
            self._transition_to("BULL", signal_date, "WATCH timeout")
            return
        
        if price_trend > 1.0 and credit_risk and breadth:
            self._transition_to("BULL", signal_date, "WATCH recovery")
            return
    
    def _handle_bear_state(
        self,
        signal_date: datetime,
        metric_values: Dict[str, float]
    ):
        """Handle transitions from BEAR state."""
        price_trend = metric_values.get('price_trend', 0)
        credit_risk = metric_values.get('credit_risk', False)
        
        # BEAR → BULL (confirmed recovery)
        if price_trend > 0 and credit_risk:
            self._transition_to("BULL", signal_date, "confirmed recovery")
            return
    
    def _check_velocity_deterioration(
        self,
        signal_date: datetime,
        metric_series: Dict[str, pd.Series]
    ) -> list:
        """
        Check for velocity deterioration using z-scores.
        
        Returns list of metric names with warnings.
        """
        from .metrics import calculate_normalized_roc
        
        warnings = []
        metrics_to_check = ['credit_risk_spread', 'internal_breadth_spread', 'price_trend']
        
        for metric_name in metrics_to_check:
            if metric_name not in metric_series:
                continue
            
            series = metric_series[metric_name]
            
            # Calculate z-score ROC
            z_score_roc = calculate_normalized_roc(
                series,
                period=self.roc_period,
                volatility_window=self.roc_volatility_window
            )
            
            if signal_date not in z_score_roc.index:
                continue
            
            z_value = z_score_roc.loc[signal_date]
            
            # Trigger if z-score below threshold (e.g., -2.0)
            if not pd.isna(z_value) and z_value < self.roc_zscore_threshold:
                warnings.append(metric_name)
                print(f"[STORMGUARD-V ROC] {metric_name} z-score: {z_value:.2f}")
        
        return warnings
    
    def _check_moderate_volatility(
        self,
        spy_prices: pd.Series,
        vix_prices: pd.Series,
        signal_date: datetime
    ) -> bool:
        """
        Check moderate volatility (WATCH trigger).
        
        Triggers when: VIX > 25 AND SPY < SMA_20
        This is a warning signal, not an emergency.
        """
        if signal_date not in vix_prices.index or signal_date not in spy_prices.index:
            return False
        
        vix_value = vix_prices.loc[signal_date]
        if vix_value < self.volatility_watch_threshold:
            return False
        
        spy_sma_20 = spy_prices.rolling(window=20, min_periods=20).mean()
        if signal_date not in spy_sma_20.index:
            return False
        
        spy_value = spy_prices.loc[signal_date]
        sma_value = spy_sma_20.loc[signal_date]
        
        return spy_value < sma_value

