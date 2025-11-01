"""Strategy logic for momentum-based stock selection."""

from typing import Dict, Optional, List
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
    check_vix_sentiment
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
        initial_capital: float = 100000.0
    ):
        """
        Initialize momentum strategy.
        
        Args:
            momentum_type: "ROC", "EMA", "Double_EMA", "DEMA", "TEMA", or "POLYMORPHIC"
            momentum_period: Lookback period (trading days)
            top_n: Number of top stocks to select
            filter_type: "DUAL_EMA", "SAFETY_SWITCH", or "NONE"
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
        
        # Polymorphic momentum setup
        self.polymorphic_manager: Optional[PolymorphicMomentumStrategy] = None
        if momentum_type == "POLYMORPHIC":
            self.polymorphic_manager = PolymorphicMomentumStrategy(
                metric=polymorphic_metric,
                initial_lookback_years=polymorphic_initial_years,
                reeval_lookback_years=polymorphic_reeval_years,
                initial_capital=initial_capital
            )
        
        # StormGuard setup (real algorithm)
        self.stormguard: Optional[StormGuardCalculator] = None
        if filter_type == "STORMGUARD":
            # Use passed parameters or defaults from config
            self.stormguard = StormGuardCalculator(
                volatility_threshold=stormguard_dema_fast if stormguard_dema_fast else 20.0,  # Reuse param temporarily
                false_alarm_days=10,
                early_return_threshold=0.05
            )
    
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
        nyse_data: Optional[Dict[str, pd.Series]] = None,
        schedule: Optional[pd.DataFrame] = None
    ) -> Optional[str]:
        """
        Get the single position to hold based on data up to signal_date.
        
        Applies configured filter (Dual EMA, Safety Switch, or None).
        With Safety Switch: rotates to safe assets during bear markets.
        With Polymorphic: uses auto-selected momentum filter.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            signal_date: Date to calculate signal (using data up to this date)
            spy_prices: Optional SPY prices for safety switch / stormguard filter
            safe_prices: Optional safe assets prices for bear market rotation
            all_rebalance_dates: All rebalance dates (for polymorphic re-eval)
            spy_volume: Optional SPY volume for stormguard OBV component
            vix_prices: Optional VIX prices for stormguard sentiment component
            
        Returns:
            Symbol name to hold, or None if no valid signal (go to cash)
        """
        if self.top_n != 1:
            raise ValueError("This method is only for top-1 strategies")
        
        # Get prices up to signal date
        prices_up_to_date = prices[prices.index <= signal_date]
        
        # Determine momentum type and period (polymorphic or fixed)
        if self.momentum_type == "POLYMORPHIC":
            if self.polymorphic_manager is None:
                raise ValueError("Polymorphic manager not initialized")
            
            # Initialize on first call
            if not self.polymorphic_manager.is_initialized:
                if all_rebalance_dates is None:
                    raise ValueError("all_rebalance_dates required for polymorphic initialization")
                self.polymorphic_manager.initialize(
                    prices_up_to_date, all_rebalance_dates, signal_date
                )
            
            # Check if quarterly re-evaluation needed
            elif self.polymorphic_manager.should_reevaluate(signal_date):
                if all_rebalance_dates is None:
                    raise ValueError("all_rebalance_dates required for polymorphic re-evaluation")
                self.polymorphic_manager.reevaluate(
                    prices_up_to_date, all_rebalance_dates, signal_date
                )
            
            # Get active filter
            active_filter = self.polymorphic_manager.get_current_filter()
            momentum_type = active_filter['type']
            momentum_period = active_filter['period']
        else:
            momentum_type = self.momentum_type
            momentum_period = self.momentum_period
        
        # This should NEVER happen if schedule was created correctly with lookback_periods
        # If it does happen, it's a configuration error, not a data issue
        if len(prices_up_to_date) < momentum_period + 1:
            raise ValueError(
                f"Insufficient data on {signal_date.date()}: "
                f"Have {len(prices_up_to_date)} days, need {momentum_period + 1}. "
                f"Check that schedule lookback_periods >= momentum_period. "
                f"This should be caught earlier by adjusting actual_start_date."
            )
        
        # Helper function to always select a safe asset (never fails)
        def select_safe_asset(safe_prices_df: pd.DataFrame, momentum_type: str, momentum_period: int) -> str:
            """
            Always return a safe asset. Uses momentum if possible, falls back to simple ROC,
            or just picks the asset with most recent valid price data.
            Logs all fallback attempts for debugging.
            """
            if safe_prices_df is None or safe_prices_df.empty:
                raise ValueError("Safe assets must be available")
            
            safe_up_to_date = safe_prices_df[safe_prices_df.index <= signal_date]
            
            # Try full momentum calculation first
            if len(safe_up_to_date) >= momentum_period + 1:
                try:
                    safe_momentum = calculate_momentum(safe_up_to_date, momentum_type, momentum_period)
                    if signal_date in safe_momentum.index:
                        safe_values = safe_momentum.loc[signal_date].dropna()
                        if len(safe_values) > 0:
                            selected = safe_values.idxmax()
                            return selected
                except Exception as e:
                    print(f"[WARNING] Safe asset {momentum_type}({momentum_period}d) failed on {signal_date.date()}: {e}")
            
            # Fallback 1: Try ROC with shorter period (21 days minimum)
            fallback_period = min(momentum_period, max(21, len(safe_up_to_date) - 1))
            if fallback_period >= 21 and len(safe_up_to_date) >= fallback_period + 1:
                try:
                    safe_momentum_roc = calculate_momentum(safe_up_to_date, "ROC", fallback_period)
                    if signal_date in safe_momentum_roc.index:
                        safe_values = safe_momentum_roc.loc[signal_date].dropna()
                        if len(safe_values) > 0:
                            selected = safe_values.idxmax()
                            print(f"[WARNING] Safe asset fallback to ROC({fallback_period}d): {selected} on {signal_date.date()} (primary {momentum_type} failed)")
                            return selected
                except Exception as e:
                    print(f"[WARNING] Safe asset ROC({fallback_period}d) fallback failed on {signal_date.date()}: {e}")
            
            # Fallback 2: Use most recent price change (simple 1-day ROC if available)
            if len(safe_up_to_date) >= 2:
                try:
                    recent_returns = safe_up_to_date.pct_change().iloc[-1].dropna()
                    if len(recent_returns) > 0:
                        selected = recent_returns.idxmax()
                        print(f"[WARNING] Safe asset fallback to 1-day return: {selected} on {signal_date.date()} (all momentum calculations failed)")
                        return selected
                except Exception as e:
                    print(f"[WARNING] Safe asset 1-day return fallback failed on {signal_date.date()}: {e}")
            
            # Fallback 3: Just pick the first asset with valid price on signal date
            if signal_date in safe_up_to_date.index:
                valid_on_date = safe_up_to_date.loc[signal_date].dropna()
                if len(valid_on_date) > 0:
                    selected = valid_on_date.index[0]
                    print(f"[WARNING] Safe asset fallback to first valid price: {selected} on {signal_date.date()} (all momentum methods failed)")
                    return selected
            
            # Fallback 4: Pick any asset with valid data
            for col in safe_up_to_date.columns:
                if not safe_up_to_date[col].isna().all():
                    print(f"[ERROR] Safe asset emergency fallback to first available: {col} on {signal_date.date()} (minimal data available)")
                    return col
            
            raise ValueError(f"No safe assets have valid data on {signal_date.date()}")
        
        # Apply Safety Switch filter first (market regime)
        if self.filter_type == "SAFETY_SWITCH":
            if spy_prices is None:
                raise ValueError("SPY prices required for SAFETY_SWITCH filter")
            spy_up_to_date = spy_prices[spy_prices.index <= signal_date]
            is_safe = check_market_safety(spy_up_to_date, self.safety_sma_short, self.safety_sma_long)
            
            # If bear market, ALWAYS rotate to safe assets (never fails)
            if signal_date in is_safe.index and not is_safe.loc[signal_date]:
                if safe_prices is None or safe_prices.empty:
                    raise ValueError("Safe assets must be configured for SAFETY_SWITCH filter")
                
                safe_asset_selected = select_safe_asset(safe_prices, momentum_type, momentum_period)
                return safe_asset_selected
        
        # Apply STORMGUARD filter (Adapted StormGuard-Armor Algorithm)
        if self.filter_type == "STORMGUARD":
            if spy_prices is None or spy_volume is None or vix_prices is None:
                raise ValueError("SPY prices, SPY volume, and VIX prices required for STORMGUARD filter")
            if schedule is None:
                raise ValueError("Schedule required for STORMGUARD filter (month-end detection)")
            
            # Filter all data up to signal date
            spy_up_to_date = spy_prices[spy_prices.index <= signal_date]
            spy_vol_up_to_date = spy_volume[spy_volume.index <= signal_date]
            vix_up_to_date = vix_prices[vix_prices.index <= signal_date]
            
            # Get market state from adapted StormGuard algorithm
            market_state = self.stormguard.get_market_state(
                spy_up_to_date,
                spy_vol_up_to_date,
                vix_up_to_date,
                signal_date,
                schedule
            )
            
            # If BEAR market, ALWAYS rotate to safe assets (never fails)
            if market_state == "BEAR":
                if safe_prices is None or safe_prices.empty:
                    raise ValueError("Safe assets must be configured for STORMGUARD filter")
                
                safe_asset_selected = select_safe_asset(safe_prices, momentum_type, momentum_period)
                return safe_asset_selected
        
        # Calculate momentum for primary universe (fallback if safe assets failed or normal selection)
        # Always try to select from primary universe - never go to cash
        if self.filter_type == "DUAL_EMA":
            if len(prices_up_to_date) < max(self.ema_short, self.ema_long) + self.ema_derivative_lookback:
                # Not enough data for filter, use unfiltered momentum
                momentum = calculate_momentum(prices_up_to_date, momentum_type, momentum_period)
            else:
                momentum = apply_dual_ema_filter_to_momentum(
                    prices_up_to_date, momentum_type, momentum_period,
                    self.ema_short, self.ema_long, self.ema_derivative_lookback
                )
        else:
            momentum = calculate_momentum(prices_up_to_date, momentum_type, momentum_period)
        
        # Momentum calculation should ALWAYS have data for signal_date if we have enough history
        if signal_date not in momentum.index:
            raise ValueError(
                f"BUG: Momentum index missing {signal_date.date()}. "
                f"Momentum has {len(momentum)} rows, prices have {len(prices_up_to_date)}. "
                f"This indicates a bug in calculate_momentum()."
            )
        
        momentum_values = momentum.loc[signal_date].dropna()
        
        # If NO valid momentum values, this is a data quality issue, not normal behavior
        if len(momentum_values) == 0:
            # For DUAL_EMA filter: all assets might be filtered out (design choice)
            if self.filter_type == "DUAL_EMA":
                # Remove filter and retry (design: prefer some asset over none)
                momentum_unfiltered = calculate_momentum(prices_up_to_date, momentum_type, momentum_period)
                if signal_date in momentum_unfiltered.index:
                    momentum_values = momentum_unfiltered.loc[signal_date].dropna()
                    if len(momentum_values) > 0:
                        print(f"[INFO] DUAL_EMA filtered all assets on {signal_date.date()}, selected from unfiltered: {momentum_values.idxmax()}")
                        return momentum_values.idxmax()
            
            # If we get here, all assets have NaN momentum - this is a DATA QUALITY issue
            raise ValueError(
                f"BUG: All assets have NaN momentum on {signal_date.date()}. "
                f"Assets: {list(prices_up_to_date.columns)}. "
                f"This indicates bad price data or a bug in calculate_momentum()."
            )
        
        # Normal case: return best momentum asset
        return momentum_values.idxmax()
    
    def generate_rebalance_positions(
        self,
        prices: pd.DataFrame,
        schedule: pd.DataFrame,
        spy_prices: Optional[pd.Series] = None,
        safe_prices: Optional[pd.DataFrame] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None,
        nyse_data: Optional[Dict[str, pd.Series]] = None
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
                spy_volume, vix_prices, nyse_data, schedule
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
