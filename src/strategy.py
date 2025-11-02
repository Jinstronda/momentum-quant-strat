"""Strategy logic for momentum-based stock selection."""

from typing import Dict, Optional, List, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.indicators import (
    calculate_roc,
    calculate_momentum,
    apply_dual_ema_filter_to_momentum,
    check_market_safety,
    check_dema_price_trend,
    check_obv_money_flow,
    check_vix_sentiment,
    apply_volatility_adjustment,
    apply_popndrop_filter_to_momentum,
    check_ema20_low_entry,
    check_ema20_defended_entry,
    select_best_safe_asset
)
from src.polymorphic import PolymorphicMomentumStrategy
from src.stormguard import StormGuardCalculator


class MomentumStrategy:
    """Pure momentum strategy - select top N stocks by ROC with optional MA filter."""
    
    def __init__(
        self,
        momentum_type: str = "ROC",
        momentum_period: int = 21,
        top_n: int = 1,
        filter_type: str = "NONE",
        ema_short: int = 20,
        ema_long: int = 50,
        ema_derivative_lookback: int = 10,
        safety_sma_short: int = 50,
        safety_sma_long: int = 200,
        stormguard_dema_fast: int = 50,
        stormguard_dema_slow: int = 100,
        stormguard_obv_sma: int = 50,
        stormguard_vix_sma: int = 50,
        polymorphic_metric: str = "Sharpe",
        polymorphic_initial_years: int = 5,
        polymorphic_reeval_years: int = 2,
        initial_capital: float = 100000.0,
        enable_momentum_persistence: bool = False,
        momentum_persistence_min_diff: float = 0.02,
        momentum_persistence_periods: int = 2,
        enable_popndrop_filter: bool = False,
        popndrop_max_return: float = 0.15,
        enable_volatility_adjustment: bool = False,
        volatility_adjustment_period: int = 63,
        volatility_max_threshold: float = 0.25,
        volatility_adjustment_mult: float = 0.8,
        enable_price_action_filter: bool = False,
        price_action_filter_type: str = "EMA20_LOW",
        price_action_lookback_days: int = 21,
        price_action_relative_close_threshold: float = 0.5
    ):
        """
        Initialize momentum strategy.
        
        Args:
            momentum_type: "ROC", "EMA", "Double_EMA", "DEMA", "TEMA", or "POLYMORPHIC"
            momentum_period: Lookback period (trading days)
            top_n: Number of top stocks to select
            filter_type: "DUAL_EMA", "SAFETY_SWITCH", "STORMGUARD", or "NONE"
            ema_short: Short-term EMA period
            ema_long: Long-term EMA period
            ema_derivative_lookback: Days for 50 EMA derivative
            safety_sma_short: SPY SMA short period
            safety_sma_long: SPY SMA long period
            stormguard_dema_fast: Fast DEMA for price trend
            stormguard_dema_slow: Slow DEMA for price trend
            stormguard_obv_sma: OBV smoothing period
            stormguard_vix_sma: VIX smoothing period
            polymorphic_metric: "Sharpe" or "Sortino" for filter evaluation
            polymorphic_initial_years: Years for initial bake-off
            polymorphic_reeval_years: Years for quarterly re-evaluation
            initial_capital: Capital for polymorphic evaluation
            enable_momentum_persistence: Enable momentum persistence filter
            momentum_persistence_min_diff: Minimum momentum difference to trigger trade
            momentum_persistence_periods: Periods leader must be top before trading
            enable_popndrop_filter: Enable PopNDrop overbought filter
            popndrop_max_return: Maximum 21-day return before excluding ETF
            enable_volatility_adjustment: Enable volatility-adjusted momentum
            volatility_adjustment_period: Period for volatility calculation
            volatility_max_threshold: Maximum volatility before penalization
            volatility_adjustment_mult: Multiplier for high volatility scores
            enable_price_action_filter: Enable price action entry filter (only on asset switches)
            price_action_filter_type: Type of price action filter (e.g., "EMA20_LOW")
            price_action_lookback_days: Days to look back for valid entry signal
        """
        self.momentum_type = momentum_type
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.filter_type = filter_type
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.ema_derivative_lookback = ema_derivative_lookback
        self.safety_sma_short = safety_sma_short
        self.safety_sma_long = safety_sma_long
        self.initial_capital = initial_capital
        
        # Advanced trade filters
        self.enable_momentum_persistence = enable_momentum_persistence
        self.momentum_persistence_min_diff = momentum_persistence_min_diff
        self.momentum_persistence_periods = momentum_persistence_periods
        self.enable_popndrop_filter = enable_popndrop_filter
        self.popndrop_max_return = popndrop_max_return
        self.enable_volatility_adjustment = enable_volatility_adjustment
        self.volatility_adjustment_period = volatility_adjustment_period
        self.volatility_max_threshold = volatility_max_threshold
        self.volatility_adjustment_mult = volatility_adjustment_mult
        self.enable_price_action_filter = enable_price_action_filter
        self.price_action_filter_type = price_action_filter_type
        self.price_action_lookback_days = price_action_lookback_days
        self.price_action_relative_close_threshold = price_action_relative_close_threshold
        
        # Track current position and momentum history for persistence filter
        self.current_position: Optional[str] = None
        self.momentum_history: Dict[str, List[float]] = {}
        
        # Polymorphic momentum setup for risk assets
        self.polymorphic_manager: Optional[PolymorphicMomentumStrategy] = None
        if momentum_type == "POLYMORPHIC":
            self.polymorphic_manager = PolymorphicMomentumStrategy(
                metric=polymorphic_metric,
                initial_lookback_years=polymorphic_initial_years,
                reeval_lookback_years=polymorphic_reeval_years,
                initial_capital=initial_capital
            )
        
        # Separate polymorphic manager for safe assets (bonds/gold have different characteristics)
        self.polymorphic_safe_manager: Optional[PolymorphicMomentumStrategy] = None
        if momentum_type == "POLYMORPHIC":
            self.polymorphic_safe_manager = PolymorphicMomentumStrategy(
                metric=polymorphic_metric,
                initial_lookback_years=polymorphic_initial_years,
                reeval_lookback_years=polymorphic_reeval_years,
                initial_capital=initial_capital
            )
        
        # StormGuard setup (real algorithm)
        self.stormguard: Optional[StormGuardCalculator] = None
        self.regime_history: List[Dict] = []  # Track bull/bear regime history
        if filter_type == "STORMGUARD":
            # Original StormGuard with hardened bear exit
            # Note: We need config dict passed in, but for now using defaults
            self.stormguard = StormGuardCalculator(
                volatility_threshold=40,  # Emergency only (was 20)
                volatility_watch_threshold=25,  # Not used in 2-state mode
                false_alarm_days=10,
                early_return_threshold=0.05,
                bear_exit_price_threshold=1.5,  # Hardened: was just > 0
                min_bear_duration=20,  # Minimum 20 days in BEAR
                bear_exit_require_breadth=True,  # Require breadth confirmation
                bear_exit_require_majority=False,  # Standard mode
                use_velocity_mode=False
            )
        elif filter_type == "STORMGUARD_VELOCITY":
            # Enhanced StormGuard with velocity detection and WATCH state
            self.stormguard = StormGuardCalculator(
                volatility_threshold=40,  # Emergency BEAR trigger (VIX > 40)
                volatility_watch_threshold=25,  # WATCH trigger (VIX > 25)
                false_alarm_days=10,
                early_return_threshold=0.05,
                bear_exit_price_threshold=1.5,  # Hardened exit
                min_bear_duration=20,  # Minimum 20 days in BEAR
                bear_exit_require_breadth=True,  # Require breadth confirmation
                bear_exit_require_majority=False,  # Standard mode
                use_velocity_mode=True,
                velocity_roc_period=10,
                velocity_zscore_threshold=-2.0,
                velocity_volatility_window=63,
                velocity_min_dwell_days=10,
                velocity_min_watch_dwell=5,  # Minimum 5 days in WATCH
                velocity_watch_timeout_days=20
            )
    
    def _determine_momentum_settings(
        self,
        prices: pd.DataFrame,
        signal_date: datetime,
        all_rebalance_dates: Optional[List[datetime]]
    ) -> Tuple[str, int]:
        """Determine momentum type and period (polymorphic or fixed)."""
        if self.momentum_type != "POLYMORPHIC":
            return self.momentum_type, self.momentum_period
        
        if self.polymorphic_manager is None:
            raise ValueError("Polymorphic manager not initialized")
        
        prices_up_to_date = prices[prices.index <= signal_date]
        
        if not self.polymorphic_manager.is_initialized:
            if all_rebalance_dates is None:
                raise ValueError("all_rebalance_dates required for polymorphic")
            self.polymorphic_manager.initialize(
                prices_up_to_date, all_rebalance_dates, signal_date
            )
        elif self.polymorphic_manager.should_reevaluate(signal_date):
            if all_rebalance_dates is None:
                raise ValueError("all_rebalance_dates required for polymorphic")
            self.polymorphic_manager.reevaluate(
                prices_up_to_date, all_rebalance_dates, signal_date
            )
        
        active_filter = self.polymorphic_manager.get_current_filter()
        return active_filter['type'], active_filter['period']
    
    def _determine_safe_momentum_settings(
        self,
        safe_prices: pd.DataFrame,
        signal_date: datetime,
        all_rebalance_dates: Optional[List[datetime]],
        momentum_type: str,
        momentum_period: int
    ) -> Tuple[str, int]:
        """Determine momentum settings for safe assets (POLYMORPHIC uses separate manager)."""
        if momentum_type != "POLYMORPHIC" or self.polymorphic_safe_manager is None:
            return momentum_type, momentum_period
        
        safe_up_to_date = safe_prices[safe_prices.index <= signal_date]
        
        if not self.polymorphic_safe_manager.is_initialized:
            if all_rebalance_dates is not None:
                self.polymorphic_safe_manager.initialize(
                    safe_up_to_date, all_rebalance_dates, signal_date
                )
        elif self.polymorphic_safe_manager.should_reevaluate(signal_date):
            if all_rebalance_dates is not None:
                self.polymorphic_safe_manager.reevaluate(
                    safe_up_to_date, all_rebalance_dates, signal_date
                )
        
        safe_filter = self.polymorphic_safe_manager.get_current_filter()
        return safe_filter['type'], safe_filter['period']
    
    def _check_market_regime_filter(
        self,
        signal_date: datetime,
        spy_prices: Optional[pd.Series],
        safe_prices: Optional[pd.DataFrame],
        spy_volume: Optional[pd.Series],
        vix_prices: Optional[pd.Series],
        hyg_prices: Optional[pd.Series],
        ief_prices: Optional[pd.Series],
        rsp_prices: Optional[pd.Series],
        schedule: Optional[pd.DataFrame],
        safe_momentum_type: str,
        safe_momentum_period: int
    ) -> Optional[str]:
        """
        Check market regime filters (SAFETY_SWITCH, STORMGUARD).
        Returns safe asset symbol if in BEAR, None if BULL.
        """
        if self.filter_type == "SAFETY_SWITCH":
            if spy_prices is None:
                raise ValueError("SPY prices required for SAFETY_SWITCH")
            spy_up_to_date = spy_prices[spy_prices.index <= signal_date]
            is_safe = check_market_safety(spy_up_to_date, self.safety_sma_short, self.safety_sma_long)
            
            if signal_date in is_safe.index and not is_safe.loc[signal_date]:
                if safe_prices is None or safe_prices.empty:
                    raise ValueError("Safe assets required for SAFETY_SWITCH")
                return select_best_safe_asset(
                    safe_prices, signal_date, safe_momentum_type, safe_momentum_period
                )
        
        if self.filter_type in ["STORMGUARD", "STORMGUARD_VELOCITY"]:
            required_data = [spy_prices, spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices]
            if any(x is None for x in required_data):
                raise ValueError("All STORMGUARD data required")
            if schedule is None:
                raise ValueError("Schedule required for STORMGUARD")
            
            market_state = self.stormguard.get_market_state(
                spy_prices[spy_prices.index <= signal_date],
                spy_volume[spy_volume.index <= signal_date],
                vix_prices[vix_prices.index <= signal_date],
                hyg_prices[hyg_prices.index <= signal_date],
                ief_prices[ief_prices.index <= signal_date],
                rsp_prices[rsp_prices.index <= signal_date],
                signal_date,
                schedule
            )
            
            self.regime_history.append({'date': signal_date, 'regime': market_state})
            
            if market_state == "BEAR":
                if safe_prices is None or safe_prices.empty:
                    raise ValueError("Safe assets required for STORMGUARD")
                return select_best_safe_asset(
                    safe_prices, signal_date, safe_momentum_type, safe_momentum_period
                )
        
        return None  # BULL regime or no regime filter
    
    def _calculate_filtered_momentum(
        self,
        prices: pd.DataFrame,
        signal_date: datetime,
        momentum_type: str,
        momentum_period: int
    ) -> pd.DataFrame:
        """Calculate momentum with DUAL_EMA filter if enabled."""
        prices_up_to_date = prices[prices.index <= signal_date]
        
        if self.filter_type == "DUAL_EMA":
            min_required = max(self.ema_short, self.ema_long) + self.ema_derivative_lookback
            if len(prices_up_to_date) < min_required:
                return calculate_momentum(prices_up_to_date, momentum_type, momentum_period)
            return apply_dual_ema_filter_to_momentum(
                prices_up_to_date, momentum_type, momentum_period,
                self.ema_short, self.ema_long, self.ema_derivative_lookback
            )
        
        return calculate_momentum(prices_up_to_date, momentum_type, momentum_period)
    
    def _apply_momentum_adjustments(
        self,
        momentum: pd.DataFrame,
        prices: pd.DataFrame,
        signal_date: datetime
    ) -> pd.DataFrame:
        """Apply volatility and PopNDrop adjustments to momentum scores."""
        prices_up_to_date = prices[prices.index <= signal_date]
        
        if self.enable_volatility_adjustment:
            if len(prices_up_to_date) >= self.volatility_adjustment_period + 1:
                momentum = apply_volatility_adjustment(
                    momentum, prices_up_to_date,
                    self.volatility_adjustment_period,
                    self.volatility_max_threshold,
                    self.volatility_adjustment_mult
                )
        
        if self.enable_popndrop_filter:
            if len(prices_up_to_date) >= 22:
                momentum = apply_popndrop_filter_to_momentum(
                    momentum, prices_up_to_date, self.popndrop_max_return, 21
                )
        
        return momentum
    
    def _apply_entry_filters(
        self,
        momentum_values: pd.Series,
        signal_date: datetime,
        prices_ohlc: Optional[pd.DataFrame]
    ) -> Optional[str]:
        """
        Apply entry filters (price action, persistence) to find valid position.
        Returns symbol or None for CASH.
        """
        new_leader = momentum_values.idxmax()
        
        # Price action filter (only when switching assets)
        if self.enable_price_action_filter and self.current_position != new_leader:
            if self.current_position is not None:
                if prices_ohlc:
                    sorted_candidates = momentum_values.sort_values(ascending=False)
                    
                    for candidate in sorted_candidates.index:
                        passes_filter = False
                        
                        if self.price_action_filter_type == "EMA20_LOW":
                            passes_filter = check_ema20_low_entry(
                                candidate, prices_ohlc, signal_date,
                                self.price_action_lookback_days
                            )
                        elif self.price_action_filter_type == "EMA20_DEFENDED":
                            passes_filter = check_ema20_defended_entry(
                                candidate, prices_ohlc, signal_date,
                                self.price_action_lookback_days,
                                self.price_action_relative_close_threshold
                            )
                        
                        if passes_filter:
                            filter_name = self.price_action_filter_type
                            print(f"[PRICE ACTION] {signal_date.date()}: {candidate} passed {filter_name}")
                            new_leader = candidate
                            break
                    else:
                        print(f"[PRICE ACTION] {signal_date.date()}: No assets passed {self.price_action_filter_type} → CASH")
                        return None
        
        # Momentum persistence filter
        if self.enable_momentum_persistence and self.current_position:
            if new_leader != self.current_position:
                if self.current_position in momentum_values.index:
                    mom_diff = abs(momentum_values[new_leader] - momentum_values[self.current_position])
                    if mom_diff < self.momentum_persistence_min_diff * 100:
                        return self.current_position
                    
                    if self.current_position not in self.momentum_history:
                        self.momentum_history[self.current_position] = []
                    self.momentum_history[self.current_position].append(
                        momentum_values[self.current_position]
                    )
                    
                    if len(self.momentum_history[self.current_position]) >= 2:
                        recent = self.momentum_history[self.current_position][-2:]
                        if recent[-1] > recent[0]:
                            return self.current_position
                    
                    if len(self.momentum_history) < self.momentum_persistence_periods:
                        return self.current_position
                else:
                    self.momentum_history.clear()
        
        if self.enable_momentum_persistence:
            self.current_position = new_leader
            for symbol in list(self.momentum_history.keys()):
                if len(self.momentum_history[symbol]) > 10:
                    self.momentum_history[symbol] = self.momentum_history[symbol][-5:]
        
        return new_leader
    
    def generate_signals(
        self,
        prices: pd.DataFrame,
        rebalance_dates: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        Generate trading signals for rebalance dates.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            rebalance_dates: Dates on which to generate signals
            
        Returns:
            DataFrame with rebalance dates as index, symbols as columns,
            1 where position should be held, 0 otherwise
        """
        # Calculate momentum for all dates
        roc = calculate_roc(prices, self.momentum_period)
        
        # For each rebalance date, select top N
        signals = []
        
        for date in rebalance_dates:
            if date not in roc.index:
                # Skip if no data available
                continue
            
            # Get ROC values for this date
            roc_values = roc.loc[date]
            
            # Remove NaN values
            roc_values = roc_values.dropna()
            
            if len(roc_values) == 0:
                # No valid signals
                continue
            
            # Select top N symbols
            top_symbols = roc_values.nlargest(self.top_n).index.tolist()
            
            # Create signal row
            signal_row = pd.Series(0, index=prices.columns, name=date)
            signal_row[top_symbols] = 1
            
            signals.append(signal_row)
        
        if not signals:
            raise ValueError("No valid signals generated")
        
        signals_df = pd.DataFrame(signals)
        signals_df.index.name = 'date'
        
        return signals_df
    
    def get_position_for_date(
        self,
        prices: pd.DataFrame,
        signal_date: datetime,
        spy_prices: Optional[pd.Series] = None,
        safe_prices: Optional[pd.DataFrame] = None,
        all_rebalance_dates: Optional[List[datetime]] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None,
        hyg_prices: Optional[pd.Series] = None,
        ief_prices: Optional[pd.Series] = None,
        rsp_prices: Optional[pd.Series] = None,
        nyse_data: Optional[Dict[str, pd.Series]] = None,
        schedule: Optional[pd.DataFrame] = None,
        prices_ohlc: Optional[pd.DataFrame] = None
    ) -> Optional[str]:
        """
        Get the single position to hold based on data up to signal_date.
        
        Orchestrates: momentum calculation → regime filters → entry filters → selection
        
        Returns:
            Symbol name to hold, or None if no valid signal (go to cash)
        """
        if self.top_n != 1:
            raise ValueError("This method is only for top-1 strategies")
        
        # Step 1: Determine momentum settings (polymorphic or fixed)
        momentum_type, momentum_period = self._determine_momentum_settings(
            prices, signal_date, all_rebalance_dates
        )
        
        # Step 2: Check data sufficiency
        prices_up_to_date = prices[prices.index <= signal_date]
        if len(prices_up_to_date) < momentum_period + 1:
            raise ValueError(
                f"Insufficient data on {signal_date.date()}: "
                f"Have {len(prices_up_to_date)} days, need {momentum_period + 1}"
            )
        
        # Step 3: Determine safe asset momentum settings
        safe_momentum_type, safe_momentum_period = self._determine_safe_momentum_settings(
            safe_prices, signal_date, all_rebalance_dates, momentum_type, momentum_period
        )
        
        # Step 4: Check market regime filters (returns safe asset if BEAR, None if BULL)
        safe_asset = self._check_market_regime_filter(
            signal_date, spy_prices, safe_prices, spy_volume, vix_prices,
            hyg_prices, ief_prices, rsp_prices, schedule,
            safe_momentum_type, safe_momentum_period
        )
        if safe_asset is not None:
            return safe_asset
        
        # Step 5: Calculate filtered momentum for risk assets
        momentum = self._calculate_filtered_momentum(
            prices, signal_date, momentum_type, momentum_period
        )
        
        # Step 6: Apply momentum adjustments (volatility, PopNDrop)
        momentum = self._apply_momentum_adjustments(momentum, prices, signal_date)
        
        # Step 7: Validate momentum results
        if signal_date not in momentum.index:
            raise ValueError(f"BUG: Momentum missing {signal_date.date()}")
        
        momentum_values = momentum.loc[signal_date].dropna()
        
        # Step 8: Handle DUAL_EMA edge case (all filtered out)
        if len(momentum_values) == 0:
            if self.filter_type == "DUAL_EMA":
                momentum_unfiltered = calculate_momentum(
                    prices_up_to_date, momentum_type, momentum_period
                )
                if signal_date in momentum_unfiltered.index:
                    momentum_values = momentum_unfiltered.loc[signal_date].dropna()
                    if len(momentum_values) > 0:
                        print(f"[INFO] DUAL_EMA filtered all → unfiltered: {momentum_values.idxmax()}")
                        return momentum_values.idxmax()
            raise ValueError(f"BUG: All assets have NaN momentum on {signal_date.date()}")
        
        # Step 9: Apply entry filters (price action, persistence)
        return self._apply_entry_filters(momentum_values, signal_date, prices_ohlc)
    
    def generate_rebalance_positions(
        self,
        prices: pd.DataFrame,
        schedule: pd.DataFrame,
        spy_prices: Optional[pd.Series] = None,
        safe_prices: Optional[pd.DataFrame] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None,
        hyg_prices: Optional[pd.Series] = None,
        ief_prices: Optional[pd.Series] = None,
        rsp_prices: Optional[pd.Series] = None,
        nyse_data: Optional[Dict[str, pd.Series]] = None,
        prices_ohlc: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Generate positions for each rebalance date using no-lookahead approach.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            schedule: DataFrame with rebalance_date and signal_date columns
            spy_prices: Optional SPY prices for safety switch / stormguard filter
            safe_prices: Optional safe assets prices for bear market rotation
            spy_volume: Optional SPY volume for stormguard OBV component
            vix_prices: Optional VIX prices for stormguard sentiment component
            prices_ohlc: Optional OHLC data for price action filters
            
        Returns:
            DataFrame with rebalance_date as index and 'position' column
        """
        positions = []
        
        # Collect all signal dates for polymorphic
        all_signal_dates = schedule['signal_date'].tolist()
        
        for _, row in schedule.iterrows():
            rebalance_date = row['rebalance_date']
            signal_date = row['signal_date']
            
            # Get position based on data available only up to signal_date
            position = self.get_position_for_date(
                prices, signal_date, spy_prices, safe_prices, all_signal_dates,
                spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices, 
                nyse_data, schedule, prices_ohlc
            )
            
            positions.append({
                'rebalance_date': rebalance_date,
                'signal_date': signal_date,
                'position': position,
            })
        
        positions_df = pd.DataFrame(positions)
        positions_df.set_index('rebalance_date', inplace=True)
        
        return positions_df
    
    def get_filter_history(self) -> Optional[pd.DataFrame]:
        """
        Get filter history from polymorphic manager.
        
        Returns:
            DataFrame with filter history, or None if not using polymorphic
        """
        if self.momentum_type == "POLYMORPHIC" and self.polymorphic_manager is not None:
            return self.polymorphic_manager.get_filter_history_df()
        return None
    
    def get_regime_history(self) -> Optional[pd.DataFrame]:
        """
        Get regime history (bull/bear states) from STORMGUARD.
        
        Returns:
            DataFrame with regime history, or None if not using STORMGUARD
        """
        if (self.filter_type == "STORMGUARD" or self.filter_type == "STORMGUARD_VELOCITY") and self.regime_history:
            return pd.DataFrame(self.regime_history)
        return None
    
    def generate_multi_bucket_positions(
        self,
        buckets: List[tuple],
        prices_dict: Dict[str, pd.DataFrame],
        schedule: pd.DataFrame,
        spy_prices: Optional[pd.Series] = None,
        safe_prices: Optional[pd.DataFrame] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None,
        hyg_prices: Optional[pd.Series] = None,
        ief_prices: Optional[pd.Series] = None,
        rsp_prices: Optional[pd.Series] = None,
        nyse_data: Optional[Dict[str, pd.Series]] = None,
        prices_ohlc_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        Generate positions for multi-bucket portfolio.
        
        Each bucket independently selects top-1 ETF using same momentum/filter settings.
        Positions are combined with fixed allocation weights.
        
        Args:
            buckets: List of (universe_name, allocation) tuples
            prices_dict: Dictionary mapping universe_name to price DataFrame
            schedule: Rebalance schedule
            spy_prices: SPY prices for filters
            safe_prices: Safe assets for bear market rotation
            (... all filter data ...)
            
        Returns:
            DataFrame with columns for each bucket's position and allocation
        """
        all_signal_dates = schedule['signal_date'].tolist()
        multi_bucket_positions = []
        
        for _, row in schedule.iterrows():
            rebalance_date = row['rebalance_date']
            signal_date = row['signal_date']
            
            position_row = {
                'rebalance_date': rebalance_date,
                'signal_date': signal_date,
            }
            
            # Generate position for each bucket independently
            for bucket_name, allocation in buckets:
                bucket_prices = prices_dict[bucket_name]
                bucket_ohlc = prices_ohlc_dict.get(bucket_name) if prices_ohlc_dict else None
                
                # Get position for this bucket
                position = self.get_position_for_date(
                    bucket_prices, signal_date, spy_prices, safe_prices,
                    all_signal_dates, spy_volume, vix_prices, hyg_prices,
                    ief_prices, rsp_prices, nyse_data, schedule, bucket_ohlc
                )
                
                position_row[f'{bucket_name}_position'] = position
                position_row[f'{bucket_name}_allocation'] = allocation
            
            multi_bucket_positions.append(position_row)
        
        positions_df = pd.DataFrame(multi_bucket_positions)
        positions_df.set_index('rebalance_date', inplace=True)
        
        return positions_df
    
    def calculate_position_roc(
        self,
        prices: pd.DataFrame,
        schedule: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate ROC values for selected positions.
        
        Useful for analysis and debugging.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            schedule: DataFrame with rebalance_date and signal_date columns
            
        Returns:
            DataFrame with rebalance_date as index, position, and ROC columns
        """
        results = []
        
        for _, row in schedule.iterrows():
            rebalance_date = row['rebalance_date']
            signal_date = row['signal_date']
            
            # Get prices up to signal date
            prices_up_to_date = prices[prices.index <= signal_date]
            
            if len(prices_up_to_date) < self.momentum_period + 1:
                continue
            
            # Calculate momentum
            roc = calculate_roc(prices_up_to_date, self.momentum_period)
            
            if signal_date not in roc.index:
                continue
            
            roc_values = roc.loc[signal_date].dropna()
            
            if len(roc_values) == 0:
                continue
            
            # Get top symbol and its ROC
            top_symbol = roc_values.idxmax()
            top_roc = roc_values[top_symbol]
            
            results.append({
                'rebalance_date': rebalance_date,
                'signal_date': signal_date,
                'position': top_symbol,
                'roc': top_roc,
            })
        
        results_df = pd.DataFrame(results)
        if not results_df.empty:
            results_df.set_index('rebalance_date', inplace=True)
        
        return results_df
