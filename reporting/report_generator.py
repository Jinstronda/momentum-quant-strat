"""Main report generator class combining base functionality and plotters."""

from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from reporting.base import BaseReporter
from reporting.plotters import (
    plot_equity_curve,
    plot_returns_distribution,
    plot_monthly_returns,
    plot_momentum_over_time,
    plot_filter_timeline,
    plot_stormguard_signals,
    plot_strategy_vs_benchmark,
    plot_equity_curve_with_regime_background,
    plot_multi_bucket_equity_curve,
)


class BacktestReporter(BaseReporter):
    """Generate reports and visualizations for backtest results."""
    
    def plot_equity_curve(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Equity Curve",
        filename: str = "equity_curve.png",
        show_initial: bool = True,
        filter_history: Optional[pd.DataFrame] = None
    ) -> None:
        """Plot and save equity curve with color-coded positions or filters."""
        plot_equity_curve(self.output_dir, equity_curve, title, filename, show_initial, filter_history)
    
    def plot_returns_distribution(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Daily Returns Distribution",
        filename: str = "returns_distribution.png"
    ) -> None:
        """Plot distribution of daily returns."""
        plot_returns_distribution(self.output_dir, equity_curve, title, filename)
    
    def plot_monthly_returns(
        self,
        equity_curve: pd.DataFrame,
        title: str = "Monthly Returns Heatmap",
        filename: str = "monthly_returns.png"
    ) -> None:
        """Plot monthly returns as a heatmap."""
        plot_monthly_returns(self.output_dir, equity_curve, title, filename)
    
    def plot_momentum_over_time(
        self,
        prices: pd.DataFrame,
        momentum_type: str,
        momentum_period: int,
        title: str = "Momentum Over Time",
        filename: str = "momentum_over_time.png"
    ) -> None:
        """Plot momentum for all stocks over time."""
        plot_momentum_over_time(self.output_dir, prices, momentum_type, 
                               momentum_period, title, filename)
    
    def plot_filter_timeline(
        self,
        filter_history: pd.DataFrame,
        equity_curve: pd.DataFrame,
        title: str = "Polymorphic Filter Timeline",
        filename: str = "filter_timeline.png"
    ) -> None:
        """Plot timeline showing which filter was active over time."""
        plot_filter_timeline(self.output_dir, filter_history, equity_curve, title, filename)
    
    def plot_stormguard_signals(
        self,
        spy_prices: pd.Series,
        spy_volume: pd.Series,
        vix_prices: pd.Series,
        hyg_prices: pd.Series,
        ief_prices: pd.Series,
        rsp_prices: pd.Series,
        equity_curve: pd.DataFrame,
        config: Dict,
        title: str = "STORMGUARD Analysis (5-Component)",
        filename: str = "stormguard_signals.png"
    ) -> None:
        """Plot 6-panel STORMGUARD analysis with all 5 metrics."""
        plot_stormguard_signals(self.output_dir, spy_prices, spy_volume, 
                               vix_prices, hyg_prices, ief_prices, rsp_prices,
                               equity_curve, config, title, filename)
    
    def plot_strategy_vs_benchmark(
        self,
        strategy_equity: pd.DataFrame,
        benchmark_equity: pd.DataFrame,
        strategy_name: str = "Strategy",
        benchmark_name: str = "SPY Buy & Hold",
        filename: str = "strategy_vs_benchmark.png"
    ) -> None:
        """Plot strategy performance vs benchmark."""
        plot_strategy_vs_benchmark(self.output_dir, strategy_equity, benchmark_equity,
                                  strategy_name, benchmark_name, filename)
    
    def plot_equity_curve_with_regime_background(
        self,
        equity_curve: pd.DataFrame,
        regime_history: pd.DataFrame,
        title: str = "Equity Curve with Market Regime",
        filename: str = "equity_curve_regime.png"
    ) -> None:
        """Plot equity curve with bull/bear regime background shading."""
        plot_equity_curve_with_regime_background(
            self.output_dir, equity_curve, regime_history, title, filename
        )
    
    def save_comparison_metrics(
        self,
        strategy_metrics: Dict[str, float],
        benchmark_metrics: Dict[str, float],
        relative_metrics: Dict[str, float],
        filename: str = "comparison_metrics.csv"
    ) -> None:
        """Save comparison metrics to CSV."""
        comparison_df = pd.DataFrame({
            'Strategy': strategy_metrics,
            'Benchmark': benchmark_metrics,
        })
        
        for key, value in relative_metrics.items():
            comparison_df.loc[key] = [value, 0]
        
        output_path = self.output_dir / filename
        comparison_df.to_csv(output_path)
        print(f"Comparison metrics saved to {output_path}")
    
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
        regime_history: Optional[pd.DataFrame] = None,
        spy_prices: Optional[pd.Series] = None,
        spy_volume: Optional[pd.Series] = None,
        vix_prices: Optional[pd.Series] = None,
        hyg_prices: Optional[pd.Series] = None,
        ief_prices: Optional[pd.Series] = None,
        rsp_prices: Optional[pd.Series] = None,
        config: Optional[Dict] = None,
        schedule: Optional[pd.DataFrame] = None,
        benchmark_equity: Optional[pd.DataFrame] = None,
        benchmark_metrics: Optional[Dict[str, float]] = None,
        buckets: Optional[list] = None
    ) -> None:
        """Generate complete report with all visualizations and data exports."""
        print(f"\n{'='*60}")
        print(f"Generating report for {universe_name}")
        print(f"{'='*60}\n")
        
        # Detect multi-bucket mode
        is_multi_bucket = buckets is not None and len(buckets) > 1
        
        self.save_metrics(metrics, f"{universe_name}_metrics.csv")
        self.save_trades(trades, f"{universe_name}_trades.csv")
        self.save_equity_curve(equity_curve, f"{universe_name}_equity.csv")
        
        # Save benchmark data if provided
        if benchmark_metrics is not None:
            self.save_metrics(benchmark_metrics, f"{universe_name}_benchmark_metrics.csv")
        if benchmark_equity is not None:
            self.save_equity_curve(benchmark_equity, f"{universe_name}_benchmark_equity.csv")
        
        if filter_history is not None and not filter_history.empty:
            self.save_filter_history(filter_history, f"{universe_name}_filter_history.csv")
        
        # Generate equity curve based on mode
        if is_multi_bucket:
            # Multi-bucket mode: use blended color plot
            plot_multi_bucket_equity_curve(
                self.output_dir,
                equity_curve,
                buckets,
                regime_history=regime_history,
                title=f"{universe_name} - Multi-Bucket Portfolio",
                filename=f"{universe_name}_equity_curve.png"
            )
        elif filter_history is not None and not filter_history.empty:
            # Polymorphic mode: show by filter and by asset
            self.plot_equity_curve(
                equity_curve,
                title=f"{universe_name} - Equity Curve (by Momentum Filter)",
                filename=f"{universe_name}_equity_curve_by_filter.png",
                filter_history=filter_history
            )
            self.plot_equity_curve(
                equity_curve,
                title=f"{universe_name} - Equity Curve (by Asset Held)",
                filename=f"{universe_name}_equity_curve_by_asset.png",
                filter_history=None
            )
        else:
            # Single-bucket mode: standard plot
            self.plot_equity_curve(
                equity_curve,
                title=f"{universe_name} - Equity Curve",
                filename=f"{universe_name}_equity_curve.png",
                filter_history=None
            )
        
        # Generate benchmark comparison (MOST IMPORTANT CHART)
        if benchmark_equity is not None:
            print(f"\n[INFO] Generating benchmark comparison chart...")
            self.plot_strategy_vs_benchmark(
                strategy_equity=equity_curve,
                benchmark_equity=benchmark_equity,
                strategy_name=universe_name,
                benchmark_name="SPY Buy & Hold",
                filename=f"{universe_name}_vs_benchmark.png"
            )
            
            # Save comparison metrics if benchmark metrics provided
            if benchmark_metrics is not None:
                from src.benchmark import calculate_relative_metrics
                relative_metrics = calculate_relative_metrics(metrics, benchmark_metrics)
                self.save_comparison_metrics(
                    strategy_metrics=metrics,
                    benchmark_metrics=benchmark_metrics,
                    relative_metrics=relative_metrics,
                    filename=f"{universe_name}_comparison.csv"
                )
        else:
            print(f"\n[WARNING] Benchmark equity is None - skipping benchmark comparison chart!")
        
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
        
        if filter_history is not None and not filter_history.empty:
            self.plot_filter_timeline(
                filter_history,
                equity_curve,
                title=f"{universe_name} - Polymorphic Filter Timeline",
                filename=f"{universe_name}_filter_timeline.png"
            )
        
        # Generate STORMGUARD signals only in single-bucket mode
        if (not is_multi_bucket and
            config is not None and config.get('filter_type') == 'STORMGUARD' and
            spy_prices is not None and spy_volume is not None and vix_prices is not None and
            hyg_prices is not None and ief_prices is not None and rsp_prices is not None):
            self.plot_stormguard_signals(
                spy_prices, spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices,
                equity_curve, config,
                title=f"{universe_name} - STORMGUARD 5-Component Analysis",
                filename=f"{universe_name}_stormguard_signals.png"
            )
            
            # Also generate equity curve with regime background (using cached regime history)
            if regime_history is not None and not regime_history.empty:
                self.plot_equity_curve_with_regime_background(
                    equity_curve, regime_history,
                    title=f"{universe_name} - Equity Curve with Bull/Bear Regime",
                    filename=f"{universe_name}_equity_curve_regime.png"
                )
        
        # Skip momentum over time in multi-bucket mode (ambiguous with multiple universes)
        if (not is_multi_bucket and
            prices is not None and momentum_period is not None and momentum_type != "POLYMORPHIC"):
            mom_type = momentum_type if momentum_type else 'ROC'
            self.plot_momentum_over_time(
                prices, momentum_type=mom_type, momentum_period=momentum_period,
                title=f"{universe_name} - Momentum ({mom_type} {momentum_period}d) Over Time",
                filename=f"{universe_name}_momentum_over_time.png"
            )
        
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

