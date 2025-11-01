"""Main script to run momentum strategy backtests."""

import sys
import os
from typing import Dict
from datetime import datetime
from pathlib import Path

from src.config import ACTIVE_UNIVERSE, get_config
from src.data import DataLoader
from src.schedule import create_rebalance_schedule
from src.strategy import MomentumStrategy
from src.backtest import BacktestEngine
from src.reporting import BacktestReporter
from src.benchmark import BenchmarkRunner, calculate_relative_metrics


def run_backtest_for_universe(universe_name: str, config: Dict, output_dir: str) -> None:
    """
    Run complete backtest for a single universe.
    
    Args:
        universe_name: Name of the universe
        config: Configuration dictionary with all backtest parameters
        output_dir: Output directory for results
    """
    # Extract parameters from config
    symbols = config['universes'][universe_name]
    start_date = config['start_date']
    end_date = config['end_date']
    roc_period = config['roc_period_days']
    top_n = config['top_n']
    rebalance_weekday = config['rebalance_weekday']
    initial_capital = config['initial_capital']
    commission_pct = config['commission_pct']
    slippage_pct = config['slippage_pct']
    data_dir = config['data_dir']
    cache_enabled = config['cache_enabled']
    print(f"\n{'='*80}")
    print(f"Running backtest for universe: {universe_name}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"{'='*80}\n")
    
    try:
        # Step 1: Load data
        print("Step 1/6: Loading price data...")
        loader = DataLoader(data_dir=data_dir, cache_enabled=cache_enabled)
        prices = loader.get_close_prices(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            force_refresh=False
        )
        print(f"[OK] Loaded {len(prices)} days of data for {len(prices.columns)} symbols\n")
        
        # Step 2: Create rebalance schedule
        print("Step 2/6: Creating rebalance schedule...")
        schedule = create_rebalance_schedule(
            start_date=start_date,
            end_date=end_date,
            weekday=rebalance_weekday,
            lookback_periods=roc_period,
            market='NYSE'
        )
        print(f"[OK] Generated {len(schedule)} rebalance dates\n")
        
        # Step 3: Generate trading signals
        print("Step 3/6: Generating trading signals...")
        strategy = MomentumStrategy(roc_period=roc_period, top_n=top_n)
        positions = strategy.generate_rebalance_positions(prices, schedule)
        print(f"[OK] Generated positions for {len(positions)} rebalance dates\n")
        
        # Step 4: Run backtest
        print("Step 4/6: Running backtest...")
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct
        )
        equity_curve, trades = engine.run_backtest(prices, positions)
        metrics = engine.calculate_metrics(equity_curve)
        print(f"[OK] Backtest complete - {len(trades)} trades executed\n")
        
        # Step 5: Run benchmark (SPY buy & hold)
        print("Step 5/6: Running SPY benchmark...")
        benchmark_runner = BenchmarkRunner(
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct
        )
        
        # Get SPY prices (should already be in our universe)
        if 'SPY' in prices.columns:
            spy_prices = prices['SPY']
        else:
            # If SPY not in universe, download it
            spy_prices = loader.get_close_prices(['SPY'], start_date, end_date)['SPY']
        
        benchmark_equity, benchmark_trades = benchmark_runner.run_buy_and_hold(spy_prices, "SPY")
        benchmark_metrics = benchmark_runner.calculate_metrics(benchmark_equity)
        print(f"[OK] Benchmark complete\n")
        
        # Step 6: Generate reports with benchmark comparison
        print("Step 6/6: Generating reports...")
        reporter = BacktestReporter(output_dir=output_dir)
        
        # Generate strategy reports
        reporter.create_full_report(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            universe_name=universe_name
        )
        
        # Generate benchmark reports
        reporter.save_metrics(benchmark_metrics, f"{universe_name}_benchmark_metrics.csv")
        reporter.save_equity_curve(benchmark_equity, f"{universe_name}_benchmark_equity.csv")
        
        # Generate comparison plot
        reporter.plot_strategy_vs_benchmark(
            strategy_equity=equity_curve,
            benchmark_equity=benchmark_equity,
            strategy_name=universe_name,
            benchmark_name="SPY Buy & Hold",
            filename=f"{universe_name}_vs_benchmark.png"
        )
        
        # Calculate and save relative metrics
        relative_metrics = calculate_relative_metrics(metrics, benchmark_metrics)
        reporter.save_comparison_metrics(
            strategy_metrics=metrics,
            benchmark_metrics=benchmark_metrics,
            relative_metrics=relative_metrics,
            filename=f"{universe_name}_comparison.csv"
        )
        
        # Print comparison summary
        print(f"\n{'='*80}")
        print(f"Performance Comparison: {universe_name} vs SPY Buy & Hold")
        print(f"{'='*80}")
        print(f"{'Metric':<30} {'Strategy':>15} {'SPY':>15} {'Difference':>15}")
        print(f"{'-'*80}")
        
        comparison_metrics = [
            ('Total Return (%)', 'Total Return (%)'),
            ('CAGR (%)', 'CAGR (%)'),
            ('Sharpe Ratio', 'Sharpe Ratio'),
            ('Max Drawdown (%)', 'Max Drawdown (%)'),
            ('Volatility (%)', 'Volatility (%)'),
        ]
        
        for label, key in comparison_metrics:
            strat_val = metrics[key]
            bench_val = benchmark_metrics[key]
            diff = strat_val - bench_val
            print(f"{label:<30} {strat_val:>15.2f} {bench_val:>15.2f} {diff:>15.2f}")
        
        print(f"{'='*80}\n")
        
        print(f"[OK] Reports generated successfully\n")
        
        print(f"{'='*80}")
        print(f"Backtest complete for {universe_name}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n{'!'*80}")
        print(f"ERROR: Backtest failed for {universe_name}")
        print(f"Error: {str(e)}")
        print(f"{'!'*80}\n")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main entry point for running backtests."""
    # Get configuration
    config = get_config()
    universe_name = ACTIVE_UNIVERSE
    
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{timestamp}_{universe_name}_ROC{config['roc_period_days']}d_Top{config['top_n']}"
    run_output_dir = os.path.join(config['output_dir'], run_name)
    
    # Create directory
    Path(run_output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("MOMENTUM STRATEGY BACKTEST")
    print("="*80)
    print(f"Run Name: {run_name}")
    print(f"Output Directory: {run_output_dir}")
    print(f"\nConfiguration:")
    print(f"  Universe: {universe_name}")
    print(f"  Start Date: {config['start_date'].date()}")
    print(f"  End Date: {config['end_date'].date()}")
    print(f"  ROC Period: {config['roc_period_days']} days")
    print(f"  Top N: {config['top_n']}")
    print(f"  Rebalance: {'Monday' if config['rebalance_weekday'] == 0 else 'Weekday ' + str(config['rebalance_weekday'])}")
    print(f"  Initial Capital: ${config['initial_capital']:,.0f}")
    print(f"  Commission: {config['commission_pct']*100:.2f}%")
    print(f"  Slippage: {config['slippage_pct']*100:.3f}%")
    print("="*80)
    
    # Run backtest for active universe
    run_backtest_for_universe(
        universe_name=universe_name,
        config=config,
        output_dir=run_output_dir
    )
    
    # Save run configuration and create README
    config_file = os.path.join(run_output_dir, "run_config.txt")
    readme_file = os.path.join(run_output_dir, "README.txt")
    symbols = config['universes'][universe_name]
    
    with open(config_file, 'w') as f:
        f.write(f"Run Name: {run_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Universe: {universe_name}\n")
        f.write(f"Symbols: {', '.join(symbols)}\n")
        f.write(f"Start Date: {config['start_date'].date()}\n")
        f.write(f"End Date: {config['end_date'].date()}\n")
        f.write(f"ROC Period: {config['roc_period_days']} days\n")
        f.write(f"Top N: {config['top_n']}\n")
        f.write(f"Rebalance Day: {'Monday' if config['rebalance_weekday'] == 0 else 'Weekday ' + str(config['rebalance_weekday'])}\n")
        f.write(f"Initial Capital: ${config['initial_capital']:,.2f}\n")
        f.write(f"Commission: {config['commission_pct']*100:.2f}%\n")
        f.write(f"Slippage: {config['slippage_pct']*100:.3f}%\n")
    
    # Create a comprehensive README
    with open(readme_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write(f"BACKTEST RUN: {run_name}\n")
        f.write("="*80 + "\n\n")
        
        f.write("CONFIGURATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Universe:        {universe_name}\n")
        f.write(f"Period:          {config['start_date'].date()} to {config['end_date'].date()}\n")
        f.write(f"Strategy:        Top-{config['top_n']} Momentum (ROC {config['roc_period_days']} days)\n")
        f.write(f"Rebalance:       Every Monday (NYSE calendar)\n")
        f.write(f"Initial Capital: ${config['initial_capital']:,.2f}\n")
        f.write(f"Costs:           {config['commission_pct']*100:.2f}% commission + {config['slippage_pct']*100:.3f}% slippage\n\n")
        
        f.write("FILES IN THIS DIRECTORY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{universe_name}_metrics.csv              - Strategy performance metrics\n")
        f.write(f"{universe_name}_benchmark_metrics.csv    - SPY buy & hold metrics\n")
        f.write(f"{universe_name}_comparison.csv           - Side-by-side comparison\n")
        f.write(f"{universe_name}_trades.csv               - Complete trade log\n")
        f.write(f"{universe_name}_equity.csv               - Daily equity curve\n")
        f.write(f"{universe_name}_benchmark_equity.csv     - SPY equity curve\n")
        f.write(f"{universe_name}_equity_curve.png         - Strategy equity chart\n")
        f.write(f"{universe_name}_vs_benchmark.png         - Strategy vs SPY comparison\n")
        f.write(f"{universe_name}_drawdown.png             - Drawdown analysis\n")
        f.write(f"{universe_name}_monthly_returns.png      - Monthly returns heatmap\n")
        f.write(f"{universe_name}_returns_dist.png         - Returns distribution\n\n")
        
        f.write("QUICK START\n")
        f.write("-" * 80 + "\n")
        f.write("1. Check the comparison plot: *_vs_benchmark.png\n")
        f.write("2. Review metrics: *_comparison.csv\n")
        f.write("3. Examine trades: *_trades.csv\n")
        f.write("4. Analyze drawdowns: *_drawdown.png\n\n")
    
    print(f"\nRun configuration saved to: {config_file}")
    print(f"README created: {readme_file}")
    
    print("\n" + "="*80)
    print("ALL BACKTESTS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBacktest failed with error: {e}")
        sys.exit(1)
