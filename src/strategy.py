"""Strategy logic for momentum-based stock selection."""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from src.indicators import (
    calculate_roc,
    calculate_momentum,
    apply_dual_ema_filter_to_momentum
)


class MomentumStrategy:
    """Pure momentum strategy - select top N stocks by ROC with optional MA filter."""
    
    def __init__(
        self,
        momentum_type: str = "ROC",
        momentum_period: int = 21,
        top_n: int = 1,
        use_ma_filter: bool = False,
        ema_short: int = 20,
        ema_long: int = 50,
        ema_derivative_lookback: int = 10
    ):
        """
        Initialize momentum strategy.
        
        Args:
            momentum_type: "ROC" or "DEMA"
            momentum_period: Lookback period (trading days)
            top_n: Number of top stocks to select
            use_ma_filter: Whether to filter by dual EMA system
            ema_short: Short-term EMA period (default 20)
            ema_long: Long-term EMA period (default 50)
            ema_derivative_lookback: Days to look back for 50 EMA derivative (default 10)
        """
        self.momentum_type = momentum_type
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.use_ma_filter = use_ma_filter
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.ema_derivative_lookback = ema_derivative_lookback
    
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
        signal_date: datetime
    ) -> Optional[str]:
        """
        Get the single position to hold based on data up to signal_date.
        
        With MA filter enabled:
        - Ranks all symbols by ROC
        - Filters out symbols below their MA
        - Selects highest ROC that passes filter
        - Returns None (cash) if no symbols pass filter
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            signal_date: Date to calculate signal (using data up to this date)
            
        Returns:
            Symbol name to hold, or None if no valid signal (go to cash)
        """
        if self.top_n != 1:
            raise ValueError("This method is only for top-1 strategies")
        
        # Get prices up to signal date
        prices_up_to_date = prices[prices.index <= signal_date]
        
        if len(prices_up_to_date) < self.momentum_period + 1:
            # Not enough data
            return None
        
        # Calculate momentum
        if self.use_ma_filter:
            # Apply dual EMA filter - momentum is NaN for symbols that don't meet all conditions
            if len(prices_up_to_date) < max(self.ema_short, self.ema_long) + self.ema_derivative_lookback:
                return None
            
            momentum = apply_dual_ema_filter_to_momentum(
                prices_up_to_date,
                momentum_type=self.momentum_type,
                momentum_period=self.momentum_period,
                ema_short=self.ema_short,
                ema_long=self.ema_long,
                derivative_lookback=self.ema_derivative_lookback
            )
        else:
            momentum = calculate_momentum(prices_up_to_date, self.momentum_type, self.momentum_period)
        
        if signal_date not in momentum.index:
            return None
        
        momentum_values = momentum.loc[signal_date].dropna()
        
        if len(momentum_values) == 0:
            return None  # No symbols pass filter - go to cash
        
        # Return best momentum stock
        return momentum_values.idxmax()
    
    def generate_rebalance_positions(
        self,
        prices: pd.DataFrame,
        schedule: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Generate positions for each rebalance date using no-lookahead approach.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            schedule: DataFrame with rebalance_date and signal_date columns
            
        Returns:
            DataFrame with rebalance_date as index and 'position' column
        """
        positions = []
        
        for _, row in schedule.iterrows():
            rebalance_date = row['rebalance_date']
            signal_date = row['signal_date']
            
            # Get position based on data available only up to signal_date
            position = self.get_position_for_date(prices, signal_date)
            
            positions.append({
                'rebalance_date': rebalance_date,
                'signal_date': signal_date,
                'position': position,
            })
        
        positions_df = pd.DataFrame(positions)
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
