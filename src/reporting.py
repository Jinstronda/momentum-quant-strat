"""Reporting and visualization module for backtest results."""

from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


class BacktestReporter:
    """Generate reports and visualizations for backtest results."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize reporter with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set plotting style
        sns.set_style("darkgrid")
        plt.rcParams['figure.figsize'] = (12, 6)
    
    def save_metrics(
        self,
        metrics: Dict[str, float],
        filename: str = "metrics.csv"
    ) -> None:
        """
        Save performance metrics to CSV.
        
        Args:
            metrics: Dictionary of metrics
            filename: Output filename
        """
        metrics_df = pd.DataFrame([metrics]).T
        metrics_df.columns = ['Value']
        
        output_path = self.output_dir / filename
        metrics_df.to_csv(output_path)
        print(f"Metrics saved to {output_path}")
    
    def save_trades(
        self,
        trades: pd.DataFrame,
        filename: str = "trades.csv"
    ) -> None:
        """
        Save trade log to CSV.
        
        Args:
            trades: DataFrame with trade details
            filename: Output filename
        """
        if trades.empty:
            print("No trades to save")
            return
        
        output_path = self.output_dir / filename
        trades.to_csv(output_path, index=False)
        print(f"Trades saved to {output_path}")
    
    def save_equity_curve(
        self,
        equity_curve: pd.DataFrame,
        filename: str = "equity_curve.csv"
    ) -> None:
        """
        Save equity curve to CSV.
        
        Args:
            equity_curve: DataFrame with equity data
            filename: Output filename
        """
        output_path = self.output_dir / filename
        equity_curve.to_csv(output_path)
        print(f"Equity curve saved to {output_path}")
    
    def save_filter_history(
        self,
        filter_history: pd.DataFrame,
        filename: str = "filter_history.csv"
    ) -> None:
        """
        Save polymorphic filter history to CSV.
    
    Args:
            filter_history: DataFrame with filter selection history
            filename: Output filename
        """
        if filter_history is None or filter_history.empty:
            print("No filter history to save (not using polymorphic momentum)")
            return
        
        output_path = self.output_dir / filename
        filter_history.to_csv(output_path, index=False)
        print(f"Filter history saved to {output_path}")
    
    def plot_equity_curve(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Equity Curve",
        filename: str = "equity_curve.png",
        show_initial: bool = True,
        filter_history: Optional[pd.DataFrame] = None
    ) -> None:
        """
        Plot and save equity curve with color-coded positions or filters.
    
    Args:
            equity_curve: DataFrame with 'equity' and 'position' columns
            title: Plot title
            filename: Output filename
            show_initial: Show initial capital line
            filter_history: Optional filter history for polymorphic color-coding
        """
        fig, ax = plt.subplots(figsize=(16, 8))
        
        equity = equity_curve['equity']
        
        # POLYMORPHIC: Color by filter type instead of position
        if filter_history is not None and not filter_history.empty:
            # Define colors for different filter types
            filter_colors = {
                'EMA(12)': '#FF6B6B',      # Red
                'EMA(25)': '#FF8E53',      # Orange
                'EMA(45)': '#FFB84D',      # Light Orange
                'EMA(63)': '#FFD93D',      # Yellow
                'Double_EMA(12)': '#6BCF7F', # Green
                'Double_EMA(25)': '#4ECDC4', # Teal
                'Double_EMA(45)': '#45B7D1', # Light Blue
                'Double_EMA(63)': '#4D96FF', # Blue
                'Double_EMA(75)': '#5F72BD', # Dark Blue
                'Double_EMA(90)': '#6C5CE7', # Purple
                'Double_EMA(105)': '#A29BFE', # Light Purple
                'Double_EMA(120)': '#B19CD9', # Lavender
                'TEMA(12)': '#FD79A8',     # Pink
                'TEMA(25)': '#FDCB6E',     # Peach
                'TEMA(45)': '#E17055',     # Terracotta
                'TEMA(63)': '#D63031',     # Dark Red
                'TEMA(75)': '#00B894',     # Mint
                'TEMA(90)': '#00CEC9',     # Cyan
                'TEMA(105)': '#0984E3',    # Ocean Blue
                'TEMA(120)': '#6C5CE7',    # Violet
            }
            
            # Create filter name mapping
            filter_history_copy = filter_history.copy()
            filter_history_copy['filter_name'] = (
                filter_history_copy['filter_type'] + '(' + 
                filter_history_copy['filter_period'].astype(str) + ')'
            )
            filter_history_copy['date'] = pd.to_datetime(filter_history_copy['date'])
            
            # Plot equity curve with color changes based on active filter
            prev_filter = None
            segment_start = 0
            legend_filters = set()
            
            # Build a mapping of dates to filters
            date_to_filter = {}
            for i in range(len(filter_history_copy)):
                start_date = filter_history_copy.iloc[i]['date']
                filter_name = filter_history_copy.iloc[i]['filter_name']
                # Find end date (next filter change or end of data)
                if i < len(filter_history_copy) - 1:
                    end_date = filter_history_copy.iloc[i + 1]['date']
                else:
                    end_date = equity.index[-1]
                
                # Assign this filter to all dates in range
                for date in equity.index:
                    if start_date <= date < end_date:
                        date_to_filter[date] = filter_name
                    elif i == len(filter_history_copy) - 1 and date >= start_date:
                        # Last filter extends to end
                        date_to_filter[date] = filter_name
            
            # Plot segments by filter
            for i in range(len(equity)):
                current_filter = date_to_filter.get(equity.index[i])
                is_last = (i == len(equity) - 1)
                
                # Check if filter changed
                filter_changed = (current_filter != prev_filter)
                
                # Plot segment when filter changes or at end
                if (filter_changed or is_last) and segment_start < i:
                    filter_name = prev_filter if prev_filter else current_filter
                    color = filter_colors.get(filter_name, '#808080')
                    
                    # Only label if we haven't seen this filter before
                    use_label = filter_name not in legend_filters
                    if use_label:
                        legend_filters.add(filter_name)
                    
                    ax.plot(
                        equity.index[segment_start:i+1],
                        equity.values[segment_start:i+1],
                        linewidth=2.5,
                        color=color,
                        label=filter_name if use_label else ""
                    )
                    
                    if filter_changed:
                        segment_start = i
                        prev_filter = current_filter
            
            # Add legend
            ax.legend(loc='upper left', title='Active Filter', fontsize=9, ncol=2)
        
        # Regular: Color by position (stock/ETF held)
        elif 'position' in equity_curve.columns:
            # Define color palette for different positions
            position_colors = {
                # CASH position (when None) - BLACK to stand out
                None: '#000000',    # Black for CASH - very distinctive
                'CASH': '#000000',  # Also handle string 'CASH' if used
                # US Large Cap
                'DIA': '#1f77b4',   # Blue
                'SPY': '#ff7f0e',   # Orange
                'QQQ': '#2ca02c',   # Green
                'VTV': '#d62728',   # Red
                'VUG': '#9467bd',   # Purple
                'XLB': '#8c564b',   # Brown
                'XLE': '#e377c2',   # Pink
                'XLF': '#7f7f7f',   # Gray
                'XLI': '#bcbd22',   # Olive
                'XLK': '#17becf',   # Cyan
                'XLY': '#ff9896',   # Light Red
                # Developed Countries
                'DFIV': '#aec7e8',  # Light Blue
                'EFA': '#ffbb78',   # Light Orange
                'EWA': '#98df8a',   # Light Green
                'EWC': '#ff9896',   # Light Red
                'EWG': '#c5b0d5',   # Light Purple
                'EWJ': '#c49c94',   # Light Brown
                'EWU': '#f7b6d2',   # Light Pink
                'EZU': '#c7c7c7',   # Light Gray
                'IEFA': '#dbdb8d',  # Light Olive
                'SPDW': '#9edae5',  # Light Cyan
                'VEA': '#ff6b6b',   # Coral Red
                'GLD': '#ffd700',   # Gold
                # Safe Assets (Bonds - Blue shades)
                'SHY': '#4169E1',   # Royal Blue
                'VGSH': '#5B9BD5',  # Medium Blue
                'AGG': '#7BAFD4',   # Light Steel Blue
                'BND': '#9FC5E8',   # Powder Blue
                'IEI': '#6495ED',   # Cornflower Blue
                'TIPX': '#00BFFF',  # Deep Sky Blue
                'BLV': '#87CEEB',   # Sky Blue
                'IEF': '#ADD8E6',   # Light Blue
                'TLH': '#B0C4DE',   # Light Steel Blue
                'TLT': '#B0E0E6',   # Powder Blue
                'ZROZ': '#AFEEEE',  # Pale Turquoise
            }
            
            # Get unique positions (including None for CASH)
            positions = equity_curve['position'].unique()
            
            # Plot equity curve with color changes based on position
            prev_position = None
            segment_start = 0
            
            # Track which positions we've already added to legend
            legend_positions = set()
            
            for i in range(len(equity_curve)):
                current_position = equity_curve['position'].iloc[i]
                is_last = (i == len(equity_curve) - 1)
                
                # Check if position changed
                position_changed = False
                if pd.isna(current_position) and pd.isna(prev_position):
                    # Both None, same position
                    position_changed = False
                elif pd.isna(current_position) or pd.isna(prev_position):
                    # One is None, one isn't - position changed
                    position_changed = True
                else:
                    # Both are not None, compare values
                    position_changed = (current_position != prev_position)
                
                # If position changed or we're at the last point, plot the previous segment
                if position_changed or is_last:
                    if prev_position is not None or segment_start < i or is_last:
                        # Handle None as 'CASH'
                        display_position = 'CASH' if pd.isna(prev_position) else prev_position
                        color = position_colors.get(prev_position, position_colors.get('CASH', '#8B4513'))
                        
                        # Only label if we haven't seen this position before
                        use_label = display_position not in legend_positions
                        if use_label:
                            legend_positions.add(display_position)
                        
                        ax.plot(
                            equity.index[segment_start:i+1],
                            equity.values[segment_start:i+1],
                            linewidth=2.5,
                            color=color,
                            label=display_position if use_label else ""
                        )
                    
                    if position_changed:
                        segment_start = i
                        prev_position = current_position
            
            # Create custom legend with all positions (including CASH)
            handles = []
            labels = []
            from matplotlib.lines import Line2D
            for pos in positions:
                # Handle None as 'CASH'
                display_pos = 'CASH' if pd.isna(pos) else pos
                color = position_colors.get(pos, position_colors.get('CASH', '#8B4513'))
                handles.append(Line2D([0], [0], color=color, linewidth=2.5))
                labels.append(display_pos)
            
            # Add to legend
            if handles:
                ax.legend(handles, labels, loc='upper left', 
                         title='Holdings', fontsize=9, ncol=2)
        else:
            # Fallback: simple plot without color coding
            ax.plot(equity.index, equity.values, linewidth=2, label='Portfolio Equity', color='#2E86AB')
        
        # Add initial capital reference line (no legend for color-coded version)
        if show_initial:
            ax.axhline(
                y=equity.iloc[0],
                color='gray',
                linestyle='--',
                alpha=0.4,
                linewidth=1.5
            )
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Equity ($)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Equity curve plot saved to {output_path}")
    
    def plot_drawdown(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Drawdown",
        filename: str = "drawdown.png"
    ) -> None:
        """
        Plot and save drawdown chart.
    
    Args:
            equity_curve: DataFrame with 'equity' column
            title: Plot title
            filename: Output filename
        """
        equity = equity_curve['equity']
        rolling_max = equity.expanding().max()
        drawdown = (equity - rolling_max) / rolling_max * 100
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        ax.fill_between(
            drawdown.index,
            drawdown.values,
            0,
            alpha=0.3,
            color='red',
            label='Drawdown'
        )
        ax.plot(drawdown.index, drawdown.values, linewidth=1.5, color='darkred')
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Add annotation for max drawdown
        max_dd_idx = drawdown.idxmin()
        max_dd_val = drawdown.min()
        ax.annotate(
            f'Max DD: {max_dd_val:.2f}%',
            xy=(max_dd_idx, max_dd_val),
            xytext=(10, -30),
            textcoords='offset points',
            fontsize=10,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Drawdown plot saved to {output_path}")
    
    def plot_returns_distribution(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Daily Returns Distribution",
        filename: str = "returns_distribution.png"
    ) -> None:
        """Plot distribution of daily returns."""
        daily_returns = equity_curve['equity'].pct_change().dropna() * 100
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Histogram
        ax1.hist(daily_returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
        ax1.axvline(daily_returns.mean(), color='red', linestyle='--', 
                   label=f'Mean: {daily_returns.mean():.3f}%')
        ax1.axvline(0, color='gray', linestyle='-', alpha=0.5)
        ax1.set_title('Returns Histogram', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Daily Return (%)', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Q-Q plot
        from scipy import stats
        stats.probplot(daily_returns, dist="norm", plot=ax2)
        ax2.set_title('Q-Q Plot', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Returns distribution plot saved to {output_path}")
    
    def plot_monthly_returns(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Monthly Returns Heatmap",
        filename: str = "monthly_returns.png"
    ) -> None:
        """
        Plot monthly returns as a heatmap.
    
    Args:
            equity_curve: DataFrame with 'equity' column
            title: Plot title
            filename: Output filename
        """
        # Calculate daily returns
        equity_curve = equity_curve.copy()
        equity_curve['returns'] = equity_curve['equity'].pct_change()
        
        # Resample to monthly and calculate cumulative returns
        monthly_returns = equity_curve['returns'].resample('ME').apply(
            lambda x: (1 + x).prod() - 1
        ) * 100
    
    # Create pivot table for heatmap
        monthly_returns_df = pd.DataFrame(monthly_returns)
        monthly_returns_df['Year'] = monthly_returns_df.index.year
        monthly_returns_df['Month'] = monthly_returns_df.index.month
        
        pivot = monthly_returns_df.pivot(index='Year', columns='Month', values='returns')
        pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
        # Create heatmap
        fig, ax = plt.subplots(figsize=(14, 8))
        
        sns.heatmap(
            pivot,
            annot=True,
            fmt='.2f',
            cmap='RdYlGn',
            center=0,
            cbar_kws={'label': 'Return (%)'},
            linewidths=0.5,
            ax=ax
        )
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Year', fontsize=12)
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Monthly returns heatmap saved to {output_path}")
    
    def plot_momentum_over_time(
        self,
        prices: pd.DataFrame,
        momentum_type: str,
        momentum_period: int,
        title: str = "Momentum Over Time",
        filename: str = "momentum_over_time.png"
    ) -> None:
        """
        Plot momentum for all stocks over time using configured indicator.
        
        Args:
            prices: DataFrame with symbols as columns, dates as index
            momentum_type: "ROC", "Double_EMA", or "DEMA"
            momentum_period: Momentum calculation period
            title: Plot title
            filename: Output filename
        """
        from src.indicators import calculate_momentum
        
        # Calculate momentum for all stocks
        momentum = calculate_momentum(prices, method=momentum_type, period=momentum_period)
        
        # Create plot
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Plot each stock's momentum
        for column in momentum.columns:
            ax.plot(momentum.index, momentum[column], linewidth=1.5, label=column, alpha=0.7)
        
        # Add zero line (only relevant for ROC)
        if momentum_type == "ROC":
            ax.axhline(y=0, color='black', linestyle='--', alpha=0.3, linewidth=1)
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel(f'{momentum_type} {momentum_period}d', fontsize=12)
        ax.legend(loc='upper left', fontsize=9, ncol=2)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Momentum over time plot saved to {output_path}")
    
    def plot_filter_timeline(
        self,
        filter_history: pd.DataFrame,
        equity_curve: pd.DataFrame,
        title: str = "Polymorphic Filter Timeline",
        filename: str = "filter_timeline.png"
    ) -> None:
        """
        Plot timeline showing which filter was active over time.
        
        Shows filter changes as vertical bands on equity curve background.
        
        Args:
            filter_history: DataFrame with filter history
            equity_curve: DataFrame with equity curve
            title: Plot title
            filename: Output filename
        """
        if filter_history is None or filter_history.empty:
            print("No filter history to plot (not using polymorphic momentum)")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # Top panel: Equity curve with filter change markers
        ax1.plot(equity_curve.index, equity_curve['equity'], 
                linewidth=2, color='#2E86AB', label='Equity')
        
        # Add vertical lines at filter changes
        filter_changes = filter_history[filter_history['is_reeval'] == True]
        for _, row in filter_changes.iterrows():
            date = pd.to_datetime(row['date'])
            if date in equity_curve.index:
                ax1.axvline(x=date, color='red', linestyle='--', alpha=0.5, linewidth=1)
        
        ax1.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)
        
        # Bottom panel: Filter type bars
        # Create categorical encoding for filter names
        filter_history_copy = filter_history.copy()
        filter_history_copy['filter_name'] = (
            filter_history_copy['filter_type'] + '(' + 
            filter_history_copy['filter_period'].astype(str) + ')'
        )
        
        unique_filters = filter_history_copy['filter_name'].unique()
        filter_to_num = {f: i for i, f in enumerate(unique_filters)}
        filter_history_copy['filter_num'] = filter_history_copy['filter_name'].map(filter_to_num)
        
        # Plot as step function
        dates = pd.to_datetime(filter_history_copy['date'])
        ax2.step(dates, filter_history_copy['filter_num'], 
                where='post', linewidth=2, color='#A23B72')
        
        # Add markers for re-evaluations
        reeval_mask = filter_history_copy['is_reeval'] == True
        ax2.scatter(dates[reeval_mask], filter_history_copy.loc[reeval_mask, 'filter_num'],
                   color='red', s=100, marker='o', zorder=5, label='Re-evaluation')
        
        ax2.set_ylabel('Active Filter', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_yticks(range(len(unique_filters)))
        ax2.set_yticklabels(unique_filters, fontsize=9)
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.legend(loc='upper left', fontsize=9)
        
        plt.tight_layout()
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Filter timeline plot saved to {output_path}")
    
    def plot_stormguard_signals(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        equity_curve: pd.DataFrame,
        config: Dict,
        title: str = "STORMGUARD 3-Component Analysis",
        filename: str = "stormguard_signals.png"
    ) -> None:
        """
        Plot 3-panel STORMGUARD component analysis.
        
        Shows all 3 components with bullish/bearish zones.
    
    Args:
            spy_prices: SPY price series
            spy_volume: SPY volume series
            vix_prices: VIX price series
            equity_curve: Equity curve for overlay
            config: Configuration dict with STORMGUARD parameters
            title: Plot title
            filename: Output filename
        """
        from src.indicators import (
            check_dema_price_trend, check_obv_money_flow, check_vix_sentiment,
            calculate_double_ema, calculate_obv
        )
        
        fig, axes = plt.subplots(3, 1, figsize=(16, 12), 
                                gridspec_kw={'height_ratios': [1, 1, 1]})
        
        # Component 1: Price Trend (DEMA crossover)
        prices_df = spy_prices.to_frame()
        dema_fast = calculate_double_ema(prices_df, config['stormguard_dema_fast']).iloc[:, 0]
        dema_slow = calculate_double_ema(prices_df, config['stormguard_dema_slow']).iloc[:, 0]
        
        axes[0].plot(spy_prices.index, dema_fast, linewidth=2, 
                    label=f"DEMA({config['stormguard_dema_fast']})", color='#2E86AB')
        axes[0].plot(spy_prices.index, dema_slow, linewidth=2, 
                    label=f"DEMA({config['stormguard_dema_slow']})", color='#A23B72')
        axes[0].fill_between(spy_prices.index, dema_fast, dema_slow,
                            where=(dema_fast > dema_slow), alpha=0.2, color='green', label='Bullish')
        axes[0].fill_between(spy_prices.index, dema_fast, dema_slow,
                            where=(dema_fast <= dema_slow), alpha=0.2, color='red', label='Bearish')
        axes[0].set_title('Component 1: Price Trend (DEMA Crossover)', fontweight='bold')
        axes[0].set_ylabel('SPY Price ($)', fontsize=10)
        axes[0].legend(loc='upper left', fontsize=9)
        axes[0].grid(True, alpha=0.3)
        
        # Component 2: Money Flow (OBV)
        obv = calculate_obv(spy_prices, spy_volume)
        obv_sma = obv.rolling(window=config['stormguard_obv_sma'], 
                             min_periods=config['stormguard_obv_sma']).mean()
        
        axes[1].plot(spy_prices.index, obv, linewidth=1.5, 
                    label='OBV', color='#2E86AB', alpha=0.7)
        axes[1].plot(spy_prices.index, obv_sma, linewidth=2, 
                    label=f"OBV_SMA({config['stormguard_obv_sma']})", color='#A23B72')
        axes[1].fill_between(spy_prices.index, obv.min(), obv.max(),
                            where=(obv > obv_sma), alpha=0.1, color='green')
        axes[1].fill_between(spy_prices.index, obv.min(), obv.max(),
                            where=(obv <= obv_sma), alpha=0.1, color='red')
        axes[1].set_title('Component 2: Money Flow (On-Balance Volume)', fontweight='bold')
        axes[1].set_ylabel('OBV', fontsize=10)
        axes[1].legend(loc='upper left', fontsize=9)
        axes[1].grid(True, alpha=0.3)
        
        # Component 3: Sentiment (VIX adaptive)
        vix_sma = vix_prices.rolling(window=config['stormguard_vix_sma'],
                                    min_periods=config['stormguard_vix_sma']).mean()
        
        axes[2].plot(vix_prices.index, vix_prices, linewidth=1.5, 
                    label='VIX', color='#D62728', alpha=0.8)
        axes[2].plot(vix_prices.index, vix_sma, linewidth=2, 
                    label=f"VIX_SMA({config['stormguard_vix_sma']})", color='#8B4513')
        axes[2].fill_between(vix_prices.index, 0, vix_prices.max(),
                            where=(vix_prices < vix_sma), alpha=0.1, color='green')
        axes[2].fill_between(vix_prices.index, 0, vix_prices.max(),
                            where=(vix_prices >= vix_sma), alpha=0.1, color='red')
        axes[2].set_title('Component 3: Sentiment (VIX Adaptive)', fontweight='bold')
        axes[2].set_ylabel('VIX', fontsize=10)
        axes[2].set_xlabel('Date', fontsize=12)
        axes[2].legend(loc='upper left', fontsize=9)
        axes[2].grid(True, alpha=0.3)
        
        plt.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"STORMGUARD signals plot saved to {output_path}")
    
    def create_full_report(
        self,
        equity_curve: pd.DataFrame,
        trades: pd.DataFrame,
        metrics: Dict[str, float],
        universe_name: str = "strategy",
        prices: Optional[pd.DataFrame] = None,
        momentum_type: Optional[str] = None,
        momentum_period: Optional[int] = None,
        filter_history: Optional[pd.DataFrame] = None,
        spy_prices: Optional[pd.Series] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None,
        config: Optional[Dict] = None
    ) -> None:
        """
        Generate complete report with all visualizations and data exports.
        
        Args:
            equity_curve: DataFrame with equity data
            trades: DataFrame with trade details
            metrics: Dictionary of performance metrics
            universe_name: Name for file prefixes
            prices: Optional DataFrame with price data for momentum plot
            momentum_type: Optional momentum indicator type
            momentum_period: Optional momentum period for plot
            filter_history: Optional filter history for polymorphic momentum
            spy_prices: Optional SPY prices for STORMGUARD plot
            spy_volume: Optional SPY volume for STORMGUARD plot
            vix_prices: Optional VIX prices for STORMGUARD plot
            config: Optional config dict for STORMGUARD parameters
        """
        print(f"\n{'='*60}")
        print(f"Generating report for {universe_name}")
        print(f"{'='*60}\n")
        
        # Save data files
        self.save_metrics(metrics, f"{universe_name}_metrics.csv")
        self.save_trades(trades, f"{universe_name}_trades.csv")
        self.save_equity_curve(equity_curve, f"{universe_name}_equity.csv")
        
        # Save filter history if using polymorphic momentum
        if filter_history is not None and not filter_history.empty:
            self.save_filter_history(filter_history, f"{universe_name}_filter_history.csv")
        
        # Create plots
        # For POLYMORPHIC: Create TWO equity curve plots
        if filter_history is not None and not filter_history.empty:
            # Plot 1: Color-coded by momentum filter
            self.plot_equity_curve(
                equity_curve,
                title=f"{universe_name} - Equity Curve (by Momentum Filter)",
                filename=f"{universe_name}_equity_curve_by_filter.png",
                filter_history=filter_history
            )
            # Plot 2: Color-coded by asset/stock held (original behavior)
            self.plot_equity_curve(
                equity_curve,
                title=f"{universe_name} - Equity Curve (by Asset Held)",
                filename=f"{universe_name}_equity_curve_by_asset.png",
                filter_history=None  # Don't use filter coloring
            )
        else:
            # Regular: Single equity curve by asset
            self.plot_equity_curve(
                equity_curve,
                title=f"{universe_name} - Equity Curve",
                filename=f"{universe_name}_equity_curve.png",
                filter_history=None
            )
        
        self.plot_drawdown(
            equity_curve,
            title=f"{universe_name} - Drawdown",
            filename=f"{universe_name}_drawdown.png"
        )
        
        self.plot_returns_distribution(
            equity_curve,
            title=f"{universe_name} - Returns Distribution",
            filename=f"{universe_name}_returns_dist.png"
        )
        
        self.plot_monthly_returns(
            equity_curve,
            title=f"{universe_name} - Monthly Returns",
            filename=f"{universe_name}_monthly_returns.png"
        )
        
        # Plot filter timeline if using polymorphic momentum
        if filter_history is not None and not filter_history.empty:
            self.plot_filter_timeline(
                filter_history,
                equity_curve,
                title=f"{universe_name} - Polymorphic Filter Timeline",
                filename=f"{universe_name}_filter_timeline.png"
            )
        
        # Plot STORMGUARD components if using STORMGUARD filter
        if (config is not None and config.get('filter_type') == 'STORMGUARD' and
            spy_prices is not None and spy_volume is not None and vix_prices is not None):
            self.plot_stormguard_signals(
                spy_prices,
                spy_volume,
                vix_prices,
                equity_curve,
                config,
                title=f"{universe_name} - STORMGUARD 3-Component Analysis",
                filename=f"{universe_name}_stormguard_signals.png"
            )
        
        # Plot momentum over time if prices provided (skip for POLYMORPHIC)
        if prices is not None and momentum_period is not None and momentum_type != "POLYMORPHIC":
            mom_type = momentum_type if momentum_type else 'ROC'
            self.plot_momentum_over_time(
                prices,
                momentum_type=mom_type,
                momentum_period=momentum_period,
                title=f"{universe_name} - Momentum ({mom_type} {momentum_period}d) Over Time",
                filename=f"{universe_name}_momentum_over_time.png"
            )
        
        # Print summary metrics
        print(f"\n{'='*60}")
        print(f"Summary Metrics for {universe_name}")
        print(f"{'='*60}")
        for key, value in metrics.items():
            if isinstance(value, float):
                if 'Rate' in key or 'Ratio' in key:
                    print(f"{key:.<40} {value:>15.4f}")
                elif '$' in str(key) or 'Capital' in key or 'Equity' in key:
                    print(f"{key:.<40} ${value:>14,.2f}")
                else:
                    print(f"{key:.<40} {value:>15.2f}")
            else:
                print(f"{key:.<40} {value:>15}")
        print(f"{'='*60}\n")

        print(f"Report generation complete for {universe_name}\n")
    
    def plot_strategy_vs_benchmark(
        self,
        strategy_equity: pd.DataFrame,
        benchmark_equity: pd.DataFrame,
        strategy_name: str = "Strategy",
        benchmark_name: str = "SPY Buy & Hold",
        filename: str = "strategy_vs_benchmark.png"
    ) -> None:
        """
        Plot strategy performance vs benchmark.
        
        Args:
            strategy_equity: Strategy equity curve
            benchmark_equity: Benchmark equity curve
            strategy_name: Name of the strategy
            benchmark_name: Name of the benchmark
            filename: Output filename
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Normalize both to 100
        strategy_norm = strategy_equity['equity'] / strategy_equity['equity'].iloc[0] * 100
        benchmark_norm = benchmark_equity['equity'] / benchmark_equity['equity'].iloc[0] * 100
        
        # Plot 1: Both strategies
        ax1.plot(strategy_norm.index, strategy_norm.values, linewidth=2, 
                label=strategy_name, color='#2E86AB')
        ax1.plot(benchmark_norm.index, benchmark_norm.values, linewidth=2, 
                label=benchmark_name, color='#A23B72', linestyle='--')
        ax1.axhline(y=100, color='gray', linestyle=':', alpha=0.5, label='Initial Value')
        
        ax1.set_title('Strategy vs Benchmark (Normalized to 100)', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Normalized Value', fontsize=12)
        ax1.legend(loc='best', fontsize=11)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Outperformance
        outperformance = strategy_norm - benchmark_norm
        colors = ['green' if x >= 0 else 'red' for x in outperformance]
        ax2.fill_between(outperformance.index, outperformance.values, 0, 
                        alpha=0.3, color='green', where=(outperformance >= 0))
        ax2.fill_between(outperformance.index, outperformance.values, 0, 
                        alpha=0.3, color='red', where=(outperformance < 0))
        ax2.plot(outperformance.index, outperformance.values, linewidth=1.5, color='black')
        ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        ax2.set_title('Outperformance vs Benchmark', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Relative Performance', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Add final outperformance annotation
        final_outperf = outperformance.iloc[-1]
        ax2.annotate(
            f'Final: {final_outperf:+.1f}',
            xy=(outperformance.index[-1], final_outperf),
            xytext=(10, -30 if final_outperf > 0 else 30),
            textcoords='offset points',
            fontsize=11,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
        )
        
        plt.tight_layout()
        
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Comparison plot saved to {output_path}")
    
    def save_comparison_metrics(
        self,
        strategy_metrics: Dict[str, float],
        benchmark_metrics: Dict[str, float],
        relative_metrics: Dict[str, float],
        filename: str = "comparison_metrics.csv"
    ) -> None:
        """
        Save comparison metrics to CSV.
        
        Args:
            strategy_metrics: Strategy performance metrics
            benchmark_metrics: Benchmark performance metrics
            relative_metrics: Relative performance metrics
            filename: Output filename
        """
        comparison_df = pd.DataFrame({
            'Strategy': strategy_metrics,
            'Benchmark': benchmark_metrics,
        })
        
        # Add relative metrics
        for key, value in relative_metrics.items():
            comparison_df.loc[key] = [value, 0]  # Benchmark relative to itself is 0
        
        output_path = self.output_dir / filename
        comparison_df.to_csv(output_path)
        print(f"Comparison metrics saved to {output_path}")
