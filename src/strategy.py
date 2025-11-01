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
        self.stormguard_dema_fast = stormguard_dema_fast
        self.stormguard_dema_slow = stormguard_dema_slow
        self.stormguard_obv_sma = stormguard_obv_sma
        self.stormguard_vix_sma = stormguard_vix_sma
        
        # Polymorphic momentum setup
        self.polymorphic_manager: Optional[PolymorphicMomentumStrategy] = None
        if momentum_type == "POLYMORPHIC":
            self.polymorphic_manager = PolymorphicMomentumStrategy(
                metric=polymorphic_metric,
                initial_lookback_years=polymorphic_initial_years,
                reeval_lookback_years=polymorphic_reeval_years,
                initial_capital=initial_capital
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
        vix_prices: Optional[pd.Series] = None
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
        
        # Check minimum data requirement
        if len(prices_up_to_date) < momentum_period + 1:
            return None
        
        # Apply Safety Switch filter first (market regime)
        if self.filter_type == "SAFETY_SWITCH":
            if spy_prices is None:
                raise ValueError("SPY prices required for SAFETY_SWITCH filter")
            spy_up_to_date = spy_prices[spy_prices.index <= signal_date]
            is_safe = check_market_safety(spy_up_to_date, self.safety_sma_short, self.safety_sma_long)
            
            # If bear market, rotate to safe assets
            if signal_date in is_safe.index and not is_safe.loc[signal_date]:
                if safe_prices is None or safe_prices.empty:
                    return None  # No safe assets available, go to cash
                
                # Select best safe asset using active momentum logic
                safe_up_to_date = safe_prices[safe_prices.index <= signal_date]
                if len(safe_up_to_date) < momentum_period + 1:
                    return None
                
                safe_momentum = calculate_momentum(safe_up_to_date, momentum_type, momentum_period)
                if signal_date not in safe_momentum.index:
                    return None
                
                safe_values = safe_momentum.loc[signal_date].dropna()
                return safe_values.idxmax() if len(safe_values) > 0 else None
        
        # Apply STORMGUARD filter (3-component system)
        if self.filter_type == "STORMGUARD":
            if spy_prices is None or spy_volume is None or vix_prices is None:
                raise ValueError("SPY prices, SPY volume, and VIX prices required for STORMGUARD filter")
            
            # Filter data up to signal date
            spy_up_to_date = spy_prices[spy_prices.index <= signal_date]
            spy_vol_up_to_date = spy_volume[spy_volume.index <= signal_date]
            vix_up_to_date = vix_prices[vix_prices.index <= signal_date]
            
            # Check all 3 components
            dema_trend = check_dema_price_trend(
                spy_up_to_date, self.stormguard_dema_fast, self.stormguard_dema_slow
            )
            obv_flow = check_obv_money_flow(
                spy_up_to_date, spy_vol_up_to_date, self.stormguard_obv_sma
            )
            vix_sentiment = check_vix_sentiment(
                vix_up_to_date, self.stormguard_vix_sma
            )
            
            # All 3 components must be bullish
            is_bullish = dema_trend & obv_flow & vix_sentiment
            
            # If any component is bearish, rotate to safe assets
            if signal_date in is_bullish.index and not is_bullish.loc[signal_date]:
                if safe_prices is None or safe_prices.empty:
                    return None  # No safe assets available, go to cash
                
                # Select best safe asset using active momentum logic
                safe_up_to_date = safe_prices[safe_prices.index <= signal_date]
                if len(safe_up_to_date) < momentum_period + 1:
                    return None
                
                safe_momentum = calculate_momentum(safe_up_to_date, momentum_type, momentum_period)
                if signal_date not in safe_momentum.index:
                    return None
                
                safe_values = safe_momentum.loc[signal_date].dropna()
                return safe_values.idxmax() if len(safe_values) > 0 else None
        
        # Calculate momentum with optional per-stock filter
        if self.filter_type == "DUAL_EMA":
            if len(prices_up_to_date) < max(self.ema_short, self.ema_long) + self.ema_derivative_lookback:
                return None
            momentum = apply_dual_ema_filter_to_momentum(
                prices_up_to_date, momentum_type, momentum_period,
                self.ema_short, self.ema_long, self.ema_derivative_lookback
            )
        else:
            momentum = calculate_momentum(prices_up_to_date, momentum_type, momentum_period)
        
        if signal_date not in momentum.index:
            return None
        
        momentum_values = momentum.loc[signal_date].dropna()
        return momentum_values.idxmax() if len(momentum_values) > 0 else None
    
    def generate_rebalance_positions(
        self,
        prices: pd.DataFrame,
        schedule: pd.DataFrame,
        spy_prices: Optional[pd.Series] = None,
        safe_prices: Optional[pd.DataFrame] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None
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
                spy_volume, vix_prices
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
