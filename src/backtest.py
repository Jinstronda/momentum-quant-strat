"""Backtest engine for calculating PnL and performance metrics."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


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
                
                # Handle position change
                if new_position != current_position:
                    # Close existing position if any
                    if current_position is not None and shares > 0:
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
                    if new_position is not None and new_position in prices.columns:
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
            if current_position is not None and shares > 0:
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
    
    def calculate_metrics(self, equity_curve: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate performance metrics from equity curve.
        
        Args:
            equity_curve: DataFrame with date index and 'equity' column
            
        Returns:
            Dictionary of performance metrics
        """
        equity = equity_curve['equity']
        
        # Total return
        total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
        
        # Calculate daily returns
        daily_returns = equity.pct_change().dropna()
        
        # Annualized return (assuming 252 trading days)
        years = len(equity) / 252
        if years > 0:
            cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
            cagr_pct = cagr * 100
        else:
            cagr_pct = 0
        
        # Volatility (annualized)
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # Sharpe ratio (assuming 0% risk-free rate)
        if volatility > 0:
            sharpe = (cagr * 100) / volatility
        else:
            sharpe = 0
        
        # Maximum drawdown
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # Calmar ratio (CAGR / abs(max drawdown))
        if max_drawdown != 0:
            calmar = abs(cagr_pct / max_drawdown)
        else:
            calmar = 0
        
        # Win rate (percentage of positive daily returns)
        win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100 if len(daily_returns) > 0 else 0
        
        # Average win/loss
        winning_days = daily_returns[daily_returns > 0]
        losing_days = daily_returns[daily_returns < 0]
        
        avg_win = winning_days.mean() * 100 if len(winning_days) > 0 else 0
        avg_loss = losing_days.mean() * 100 if len(losing_days) > 0 else 0
        
        # Final equity
        final_equity = equity.iloc[-1]
        
        return {
            'Initial Capital': self.initial_capital,
            'Final Equity': final_equity,
            'Total Return (%)': total_return,
            'CAGR (%)': cagr_pct,
            'Volatility (%)': volatility,
            'Sharpe Ratio': sharpe,
            'Max Drawdown (%)': max_drawdown,
            'Calmar Ratio': calmar,
            'Win Rate (%)': win_rate,
            'Avg Win (%)': avg_win,
            'Avg Loss (%)': avg_loss,
            'Total Trades': len(equity),
        }
    
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
