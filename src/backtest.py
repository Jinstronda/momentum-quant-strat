"""Backtest engine for calculating PnL and performance metrics."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from src.metrics import calculate_performance_metrics


class BacktestEngine:
    """Execute backtest and calculate performance metrics."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005
    ):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital
            commission_pct: Commission as percentage (0.001 = 0.1%)
            slippage_pct: Slippage as percentage (0.0005 = 0.05%)
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
    
    def calculate_trade_cost(self, trade_value: float) -> float:
        """Calculate transaction cost for a trade."""
        commission = trade_value * self.commission_pct
        slippage = trade_value * self.slippage_pct
        return commission + slippage
    
    def run_backtest(
        self,
        prices: pd.DataFrame,
        positions: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run backtest for a single-position strategy.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            positions: DataFrame with rebalance_date as index and 'position' column
            
        Returns:
            Tuple of (equity_curve, trades):
                - equity_curve: DataFrame with date, equity, position columns
                - trades: DataFrame with trade details
        """
        # Initialize tracking
        cash = self.initial_capital
        shares = 0
        current_position = None
        
        equity_history = []
        trades_history = []
        
        # Get all trading days
        all_dates = prices.index.tolist()
        rebalance_dates = positions.index.tolist()
        
        for date in all_dates:
            # Check if we need to rebalance
            if date in rebalance_dates:
                new_position = positions.loc[date, 'position']
                
                # Handle position change (NaN-safe comparison)
                position_changed = False
                if pd.isna(new_position) and pd.isna(current_position):
                    # Both are cash/None - no change
                    position_changed = False
                elif pd.isna(new_position) or pd.isna(current_position):
                    # One is cash, one isn't - position changed
                    position_changed = True
                else:
                    # Both are valid positions - compare them
                    position_changed = (new_position != current_position)
                
                if position_changed:
                    # Close existing position if any
                    if not pd.isna(current_position) and shares > 0:
                        if current_position in prices.columns and date in prices.index:
                            exit_price = prices.loc[date, current_position]
                            gross_proceeds = shares * exit_price
                            transaction_cost = self.calculate_trade_cost(gross_proceeds)
                            net_proceeds = gross_proceeds - transaction_cost
                            
                            cash += net_proceeds
                            
                            trades_history.append({
                                'date': date,
                                'action': 'SELL',
                                'symbol': current_position,
                                'shares': shares,
                                'price': exit_price,
                                'value': gross_proceeds,
                                'cost': transaction_cost,
                                'cash_after': cash
                            })
                            
                            shares = 0
                    
                    # Open new position if valid
                    if not pd.isna(new_position) and new_position in prices.columns:
                        if date in prices.index:
                            entry_price = prices.loc[date, new_position]
                            
                            # Calculate shares to buy (use all available cash)
                            gross_investment = cash * 0.999  # Leave small buffer
                            transaction_cost = self.calculate_trade_cost(gross_investment)
                            net_investment = gross_investment - transaction_cost
                            
                            shares = int(net_investment / entry_price)
                            
                            if shares > 0:
                                actual_cost = shares * entry_price
                                actual_transaction_cost = self.calculate_trade_cost(actual_cost)
                                total_cost = actual_cost + actual_transaction_cost
                                
                                cash -= total_cost
                                
                                trades_history.append({
                                    'date': date,
                                    'action': 'BUY',
                                    'symbol': new_position,
                                    'shares': shares,
                                    'price': entry_price,
                                    'value': actual_cost,
                                    'cost': actual_transaction_cost,
                                    'cash_after': cash
                                })
                    
                    current_position = new_position
            
            # Calculate current equity
            position_value = 0
            if not pd.isna(current_position) and shares > 0:
                if current_position in prices.columns and date in prices.index:
                    current_price = prices.loc[date, current_position]
                    position_value = shares * current_price
            
            total_equity = cash + position_value
            
            equity_history.append({
                'date': date,
                'equity': total_equity,
                'cash': cash,
                'position_value': position_value,
                'position': current_position,
                'shares': shares
            })
        
        # Create DataFrames
        equity_df = pd.DataFrame(equity_history)
        equity_df.set_index('date', inplace=True)
        
        trades_df = pd.DataFrame(trades_history)
        if not trades_df.empty:
            trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        return equity_df, trades_df
    
    def calculate_metrics(self, equity_curve: pd.DataFrame, trades_df: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        Calculate performance metrics from equity curve.
        
        Args:
            equity_curve: DataFrame with date index and 'equity' column
            trades_df: Optional DataFrame with trade history
            
        Returns:
            Dictionary of performance metrics
        """
        return calculate_performance_metrics(equity_curve, self.initial_capital, trades_df)
    
    def calculate_drawdown_series(self, equity_curve: pd.DataFrame) -> pd.Series:
        """
        Calculate drawdown series from equity curve.
        
        Args:
            equity_curve: DataFrame with 'equity' column
            
        Returns:
            Series of drawdown percentages
        """
        equity = equity_curve['equity']
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        return drawdown
    
    def calculate_rolling_returns(
        self,
        equity_curve: pd.DataFrame,
        window: int = 252
    ) -> pd.Series:
        """
        Calculate rolling returns.
        
        Args:
            equity_curve: DataFrame with 'equity' column
            window: Rolling window size in days (default 252 = 1 year)
            
        Returns:
            Series of rolling returns
        """
        equity = equity_curve['equity']
        rolling_returns = equity.pct_change(window) * 100
        return rolling_returns
    
    def run_multi_bucket_backtest(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        positions: pd.DataFrame,
        buckets: List[tuple]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Run backtest for multi-bucket portfolio.
        
        Each bucket independently holds top-1 ETF with fixed allocation.
        On rebalance: close all positions, allocate capital by weights, buy new positions.
        
        Args:
            prices_dict: Dictionary mapping universe_name to price DataFrame
            positions: DataFrame with columns: {bucket}_position, {bucket}_allocation
            buckets: List of (universe_name, allocation) tuples
            
        Returns:
            Tuple of (equity_curve, trades)
        """
        # Initialize tracking
        cash = self.initial_capital
        bucket_positions = {name: {'shares': 0, 'symbol': None} for name, _ in buckets}
        
        equity_history = []
        trades_history = []
        
        # Get union of all dates from all buckets
        all_dates_sets = [set(prices_dict[name].index) for name, _ in buckets]
        all_dates = sorted(set.union(*all_dates_sets))
        
        # Convert positions index to set for fast lookup (same as single-bucket)
        rebalance_dates_set = set(positions.index)
        
        for date in all_dates:
            # Check if we need to rebalance
            if date in rebalance_dates_set:
                # Check and trade each bucket independently
                for bucket_name, bucket_allocation in buckets:
                    new_symbol = positions.loc[date, f'{bucket_name}_position']
                    bucket_state = bucket_positions[bucket_name]
                    current_symbol = bucket_state['symbol']
                    bucket_prices = prices_dict[bucket_name]
                    
                    # Check if position changed (NaN-safe comparison)
                    position_changed = False
                    if pd.isna(new_symbol) and pd.isna(current_symbol):
                        position_changed = False
                    elif pd.isna(new_symbol) or pd.isna(current_symbol):
                        position_changed = True
                    else:
                        position_changed = (new_symbol != current_symbol)
                    
                    # Only trade if position changed
                    if position_changed:
                        # Close existing position
                        if bucket_state['shares'] > 0 and current_symbol is not None:
                            # Look up price in bucket's price DataFrame
                            if current_symbol in bucket_prices.columns and date in bucket_prices.index:
                                exit_price = bucket_prices.loc[date, current_symbol]
                                gross_proceeds = bucket_state['shares'] * exit_price
                                cost = self.calculate_trade_cost(gross_proceeds)
                                net_proceeds = gross_proceeds - cost
                                
                                cash += net_proceeds
                                
                                trades_history.append({
                                    'date': date,
                                    'action': 'SELL',
                                    'bucket': bucket_name,
                                    'symbol': current_symbol,
                                    'shares': bucket_state['shares'],
                                    'price': exit_price,
                                    'value': gross_proceeds,
                                    'cost': cost,
                                    'cash_after': cash
                                })
                                
                                bucket_state['shares'] = 0
                                bucket_state['symbol'] = None
                        
                        # Open new position
                        if not pd.isna(new_symbol) and new_symbol in bucket_prices.columns:
                            if date in bucket_prices.index:
                                entry_price = bucket_prices.loc[date, new_symbol]
                                
                                # Calculate bucket capital from current portfolio equity
                                # Must recalculate total equity before allocation
                                total_position_value = 0
                                for bn, _ in buckets:
                                    if bucket_positions[bn]['shares'] > 0 and bucket_positions[bn]['symbol']:
                                        bn_prices = prices_dict[bn]
                                        bn_symbol = bucket_positions[bn]['symbol']
                                        if bn_symbol in bn_prices.columns and date in bn_prices.index:
                                            total_position_value += bucket_positions[bn]['shares'] * bn_prices.loc[date, bn_symbol]
                                
                                current_equity = cash + total_position_value
                                
                                # Allocate by bucket weight
                                bucket_capital = current_equity * bucket_allocation
                                gross_investment = bucket_capital * 0.999
                                cost = self.calculate_trade_cost(gross_investment)
                                net_investment = gross_investment - cost
                                
                                shares = int(net_investment / entry_price)
                                
                                if shares > 0:
                                    actual_cost = shares * entry_price
                                    actual_cost_total = actual_cost + self.calculate_trade_cost(actual_cost)
                                    
                                    cash -= actual_cost_total
                                    
                                    bucket_positions[bucket_name]['shares'] = shares
                                    bucket_positions[bucket_name]['symbol'] = new_symbol
                                    
                                    trades_history.append({
                                        'date': date,
                                        'action': 'BUY',
                                        'bucket': bucket_name,
                                        'symbol': new_symbol,
                                        'shares': shares,
                                        'price': entry_price,
                                        'value': actual_cost,
                                        'cost': self.calculate_trade_cost(actual_cost),
                                        'cash_after': cash
                                    })
            
            # Calculate current equity (mark to market)
            total_position_value = 0
            position_details = {}
            
            for bucket_name, _ in buckets:
                bucket_state = bucket_positions[bucket_name]
                bucket_prices = prices_dict[bucket_name]
                bucket_value = 0
                
                if bucket_state['shares'] > 0 and bucket_state['symbol'] is not None:
                    if bucket_state['symbol'] in bucket_prices.columns and date in bucket_prices.index:
                        current_price = bucket_prices.loc[date, bucket_state['symbol']]
                        bucket_value = bucket_state['shares'] * current_price
                
                total_position_value += bucket_value
                position_details[f'{bucket_name}_position'] = bucket_state['symbol']
                position_details[f'{bucket_name}_shares'] = bucket_state['shares']
                position_details[f'{bucket_name}_value'] = bucket_value
            
            total_equity = cash + total_position_value
            
            equity_row = {
                'date': date,
                'equity': total_equity,
                'cash': cash,
                'position_value': total_position_value,
            }
            equity_row.update(position_details)
            
            equity_history.append(equity_row)
        
        # Create DataFrames
        equity_df = pd.DataFrame(equity_history)
        equity_df.set_index('date', inplace=True)
        
        trades_df = pd.DataFrame(trades_history)
        if not trades_df.empty:
            trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        return equity_df, trades_df