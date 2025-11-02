"""Main StormGuard calculator - orchestrates metric calculations and state machine."""

from typing import Dict
from datetime import datetime
import pandas as pd
import numpy as np

from src.stormguard.metrics import (
    calculate_price_trend,
    calculate_money_flow,
    calculate_sentiment,
    calculate_market_volatility,
    calculate_credit_risk_appetite,
    calculate_internal_breadth,
)
from src.stormguard.state_machine import StormGuardStateMachine


class StormGuardCalculator:
    """
    Main StormGuard calculator - orchestrates metric calculations and state machine.
    
    This class provides the main interface for the StormGuard filter system.
    It calculates all 5 market health metrics and uses them to determine
    whether the market is in a BULL or BEAR regime.
    """
    
    def __init__(
        self,
        volatility_threshold: float = 40.0,
        volatility_watch_threshold: float = 25.0,
        false_alarm_days: int = 10,
        early_return_threshold: float = 0.75,
        bear_exit_price_threshold: float = 1.5,
        min_bear_duration: int = 20,
        bear_exit_require_breadth: bool = True,
        bear_exit_require_majority: bool = False,
        use_velocity_mode: bool = False,
        velocity_roc_period: int = 10,
        velocity_zscore_threshold: float = -2.0,
        velocity_volatility_window: int = 63,
        velocity_min_dwell_days: int = 10,
        velocity_min_watch_dwell: int = 5,
        velocity_watch_timeout_days: int = 20
    ):
        """
        Initialize StormGuard calculator.
        
        Args:
            volatility_threshold: VIX threshold for circuit breaker (default 40)
            false_alarm_days: Days to check for false alarm validation (default 10)
            early_return_threshold: Rebound threshold for early return (default 0.75 = 75%)
            bear_exit_price_threshold: Minimum price_trend for Bear→Bull (default 1.5)
            min_bear_duration: Minimum days in BEAR before exit (default 20)
            bear_exit_require_breadth: Require breadth for Bear→Bull (default True)
            bear_exit_require_majority: Require 4/5 metrics for Bear→Bull (default False)
            use_velocity_mode: If True, use three-state machine with velocity detection
            velocity_*: Parameters for velocity mode (ignored if use_velocity_mode=False)
        """
        self.volatility_threshold = volatility_threshold
        self.false_alarm_days = false_alarm_days
        self.early_return_threshold = early_return_threshold
        self.use_velocity_mode = use_velocity_mode
        
        if use_velocity_mode:
            from src.stormguard.state_machine_velocity import StormGuardVelocityStateMachine
            self.state_machine = StormGuardVelocityStateMachine(
                volatility_threshold=volatility_threshold,
                volatility_watch_threshold=volatility_watch_threshold,
                false_alarm_days=false_alarm_days,
                early_return_threshold=early_return_threshold,
                bear_exit_price_threshold=bear_exit_price_threshold,
                min_bear_duration=min_bear_duration,
                bear_exit_require_breadth=bear_exit_require_breadth,
                bear_exit_require_majority=bear_exit_require_majority,
                roc_period=velocity_roc_period,
                roc_zscore_threshold=velocity_zscore_threshold,
                roc_volatility_window=velocity_volatility_window,
                min_dwell_days=velocity_min_dwell_days,
                min_watch_dwell=velocity_min_watch_dwell,
                watch_timeout_days=velocity_watch_timeout_days
            )
        else:
            self.state_machine = StormGuardStateMachine(
                volatility_threshold=volatility_threshold,
                false_alarm_days=false_alarm_days,
                early_return_threshold=early_return_threshold,
                bear_exit_price_threshold=bear_exit_price_threshold,
                min_bear_duration=min_bear_duration,
                bear_exit_require_breadth=bear_exit_require_breadth,
                bear_exit_require_majority=bear_exit_require_majority
            )
    
    def calculate_all_metrics(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        hyg_prices: pd.Series,
        ief_prices: pd.Series,
        rsp_prices: pd.Series
    ) -> Dict[str, pd.Series]:
        """
        Calculate all 5 StormGuard metrics.
        
        Metrics:
        1. Price-Trend: 21 × DEMA_50(SPY Returns) + 0.5%
        2. Money-Flow: OBV - SMA_50(OBV) using SPY volume
        3. Sentiment: SMA_50(VIX) - VIX (adaptive fear gauge)
        4. Credit Risk Appetite: HYG:IEF ratio momentum (LEADING)
        5. Internal Breadth: RSP vs SPY momentum (LEADING)
        
        Args:
            spy_prices: SPY price series
            spy_volume: SPY volume series
            vix_prices: VIX price series
            hyg_prices: HYG (High Yield Bonds) price series
            ief_prices: IEF (Treasuries) price series
            rsp_prices: RSP (S&P 500 Equal Weight) price series
            
        Returns:
            Dictionary with all metric series
        """
        metrics = {
            'price_trend': calculate_price_trend(spy_prices),
            'money_flow': calculate_money_flow(spy_prices, spy_volume),
            'sentiment': calculate_sentiment(vix_prices),
            'market_volatility': calculate_market_volatility(vix_prices),
            'credit_risk': calculate_credit_risk_appetite(hyg_prices, ief_prices),
            'internal_breadth': calculate_internal_breadth(spy_prices, rsp_prices),
        }
        
        # Add spread values if using velocity mode
        if self.use_velocity_mode:
            from src.stormguard.metrics import get_credit_risk_spread_value, get_breadth_spread_value
            
            credit_risk_spread = get_credit_risk_spread_value(hyg_prices, ief_prices)
            breadth_spread = get_breadth_spread_value(spy_prices, rsp_prices)
            
            metrics['credit_risk_spread'] = credit_risk_spread
            metrics['internal_breadth_spread'] = breadth_spread
        
        return metrics
    
    def get_market_state(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        hyg_prices: pd.Series,
        ief_prices: pd.Series,
        rsp_prices: pd.Series,
        signal_date: datetime,
        schedule: pd.DataFrame
    ) -> str:
        """
        Determine market state (BULL or BEAR) for signal date.
        
        Args:
            spy_prices: SPY price series up to signal_date
            spy_volume: SPY volume series up to signal_date
            vix_prices: VIX price series up to signal_date
            hyg_prices: HYG price series up to signal_date
            ief_prices: IEF price series up to signal_date
            rsp_prices: RSP price series up to signal_date
            signal_date: Date to evaluate
            schedule: Rebalance schedule (for detecting rebalance days)
            
        Returns:
            "BULL" or "BEAR"
        """
        # Calculate all metrics
        metrics = self.calculate_all_metrics(
            spy_prices, spy_volume, vix_prices,
            hyg_prices, ief_prices, rsp_prices
        )
        
        # Determine if this is a rebalance day
        is_rebalance_day = self._is_rebalance_day(signal_date, schedule)
        
        # Get metric values for this date
        metric_values = {}
        for key, series in metrics.items():
            if signal_date in series.index:
                value = series.loc[signal_date]
                metric_values[key] = value
            else:
                metric_values[key] = None
        
        # Update state machine
        return self.state_machine.update_state(
            signal_date,
            metric_values,
            metrics,
            spy_prices,
            vix_prices,
            is_rebalance_day
        )
    
    def _is_rebalance_day(self, signal_date: datetime, schedule: pd.DataFrame) -> bool:
        """
        Check if signal_date is a rebalance day.
        
        This handles both weekly and monthly rebalancing based on what's in the schedule.
        """
        return signal_date in schedule['signal_date'].values
    
    def get_metrics_for_date(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        hyg_prices: pd.Series,
        ief_prices: pd.Series,
        rsp_prices: pd.Series,
        signal_date: datetime
    ) -> Dict[str, float]:
        """
        Get all metric values for a specific date.
        
        Useful for reporting and diagnostics.
        
        Args:
            spy_prices: SPY price series
            spy_volume: SPY volume series
            vix_prices: VIX price series
            hyg_prices: HYG price series
            ief_prices: IEF price series
            rsp_prices: RSP price series
            signal_date: Date to get metrics for
            
        Returns:
            Dictionary with metric values
        """
        metrics = self.calculate_all_metrics(
            spy_prices, spy_volume, vix_prices,
            hyg_prices, ief_prices, rsp_prices
        )
        
        result = {}
        for key, series in metrics.items():
            if signal_date in series.index:
                result[key] = series.loc[signal_date]
            else:
                result[key] = np.nan
        
        return result

