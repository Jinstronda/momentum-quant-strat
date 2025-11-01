"""Strategy logic for momentum-based stock selection."""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd
import numpy as np

from src.indicators import calculate_roc, get_top_symbol_per_date


class MomentumStrategy:
    """Pure momentum strategy - select top N stocks by ROC."""
    
    def __init__(
        self,
        roc_period: int = 21,
        top_n: int = 1
    ):
        """
        Initialize momentum strategy.
        
        Args:
            roc_period: Lookback period for ROC calculation (trading days)
            top_n: Number of top stocks to select
        """
        self.roc_period = roc_period
        self.top_n = top_n
    
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
        # Calculate ROC for all dates
        roc = calculate_roc(prices, self.roc_period)
        
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
        
        This is for top-1 strategies where we hold only one position.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            signal_date: Date to calculate signal (using data up to this date)
            
        Returns:
            Symbol name to hold, or None if no valid signal
        """
        if self.top_n != 1:
            raise ValueError("This method is only for top-1 strategies")
        
        # Get prices up to signal date
        prices_up_to_date = prices[prices.index <= signal_date]
        
        if len(prices_up_to_date) < self.roc_period + 1:
            # Not enough data
            return None
        
        # Calculate ROC
        roc = calculate_roc(prices_up_to_date, self.roc_period)
        
        # Get ROC for the signal date
        if signal_date not in roc.index:
            return None
        
        roc_values = roc.loc[signal_date].dropna()
        
        if len(roc_values) == 0:
            return None
        
        # Return symbol with highest ROC
        top_symbol = roc_values.idxmax()
        
        return top_symbol
    
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
            
            if len(prices_up_to_date) < self.roc_period + 1:
                continue
            
            # Calculate ROC
            roc = calculate_roc(prices_up_to_date, self.roc_period)
            
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
