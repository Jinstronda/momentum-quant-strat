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
        """
        Initialize reporter.
        
        Args:
            output_dir: Directory for saving output files
        """
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
    
    def plot_equity_curve(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Equity Curve",
        filename: str = "equity_curve.png",
        show_initial: bool = True
    ) -> None:
        """
        Plot and save equity curve with color-coded positions.
        
        Args:
            equity_curve: DataFrame with 'equity' and 'position' columns
            title: Plot title
            filename: Output filename
            show_initial: Show initial capital line
        """
        fig, ax = plt.subplots(figsize=(16, 8))
        
        equity = equity_curve['equity']
        
        # Check if position data is available
        if 'position' in equity_curve.columns:
            # Define color palette for different positions
            position_colors = {
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
            }
            
            # Get unique positions in order of appearance
            positions = equity_curve['position'].dropna().unique()
            
            # Plot equity curve with color changes based on position
            prev_position = None
            segment_start = 0
            
            for i in range(len(equity_curve)):
                current_position = equity_curve['position'].iloc[i]
                
                # When position changes or at the end
                if current_position != prev_position or i == len(equity_curve) - 1:
                    if prev_position is not None and segment_start < i:
                        # Plot the segment with the previous position's color
                        color = position_colors.get(prev_position, '#000000')
                        ax.plot(
                            equity.index[segment_start:i+1],
                            equity.values[segment_start:i+1],
                            linewidth=2.5,
                            color=color,
                            label=prev_position if prev_position not in ax.get_legend_handles_labels()[1] else ""
                        )
                    
                    segment_start = i
                    prev_position = current_position
            
            # Create custom legend with all positions
            handles = []
            labels = []
            for pos in positions:
                if pos is not None and pos in position_colors:
                    from matplotlib.lines import Line2D
                    handles.append(Line2D([0], [0], color=position_colors[pos], linewidth=2.5))
                    labels.append(pos)
            
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
        """
        Plot distribution of daily returns.
        
        Args:
            equity_curve: DataFrame with 'equity' column
            title: Plot title
            filename: Output filename
        """
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
    
    def create_full_report(
        self,
        equity_curve: pd.DataFrame,
        trades: pd.DataFrame,
        metrics: Dict[str, float],
        universe_name: str = "strategy"
    ) -> None:
        """
        Generate complete report with all visualizations and data exports.
        
        Args:
            equity_curve: DataFrame with equity data
            trades: DataFrame with trade details
            metrics: Dictionary of performance metrics
            universe_name: Name for file prefixes
        """
        print(f"\n{'='*60}")
        print(f"Generating report for {universe_name}")
        print(f"{'='*60}\n")
        
        # Save data files
        self.save_metrics(metrics, f"{universe_name}_metrics.csv")
        self.save_trades(trades, f"{universe_name}_trades.csv")
        self.save_equity_curve(equity_curve, f"{universe_name}_equity.csv")
        
        # Create plots
        self.plot_equity_curve(
            equity_curve,
            title=f"{universe_name} - Equity Curve",
            filename=f"{universe_name}_equity_curve.png"
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
