"""Main script to run momentum strategy backtests."""

import sys
import os
from datetime import datetime
from pathlib import Path

from src.config import (
    START_DATE, END_DATE, ROC_PERIOD_DAYS, TOP_N, 
    REBALANCE_WEEKDAY, UNIVERSES, ACTIVE_UNIVERSE,
    DATA_DIR, CACHE_ENABLED, OUTPUT_DIR,
    INITIAL_CAPITAL, COMMISSION_PCT, SLIPPAGE_PCT
)
from src.data import DataLoader
from src.schedule import create_rebalance_schedule
from src.strategy import MomentumStrategy
from src.backtest import BacktestEngine
from src.reporting import BacktestReporter
from src.benchmark import BenchmarkRunner, calculate_relative_metrics


def run_backtest_for_universe(
    universe_name: str,
    symbols: list,
    start_date: datetime,
    end_date: datetime,
    roc_period: int,
    top_n: int,
    rebalance_weekday: int,
    initial_capital: float,
    commission_pct: float,
    slippage_pct: float,
    data_dir: str,
    cache_enabled: bool,
    output_dir: str
) -> None:
    """
    Run complete backtest for a single universe.
    
    Args:
        universe_name: Name of the universe
        symbols: List of symbols in the universe
        start_date: Backtest start date
        end_date: Backtest end date
        roc_period: ROC lookback period
        top_n: Number of top stocks to select
        rebalance_weekday: Day of week for rebalancing
        initial_capital: Starting capital
        commission_pct: Commission percentage
        slippage_pct: Slippage percentage
        data_dir: Data directory for caching
        cache_enabled: Whether to use cache
        output_dir: Output directory for results
    """
    print(f"\n{'='*80}")
    print(f"Running backtest for universe: {universe_name}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"{'='*80}\n")
    
    try:
        # Step 1: Load data
        print("Step 1/5: Loading price data...")
        loader = DataLoader(data_dir=data_dir, cache_enabled=cache_enabled)
        prices = loader.get_close_prices(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            force_refresh=False
        )
        print(f"[OK] Loaded {len(prices)} days of data for {len(prices.columns)} symbols\n")
        
        # Step 2: Create rebalance schedule
        print("Step 2/5: Creating rebalance schedule...")
        schedule = create_rebalance_schedule(
            start_date=start_date,
            end_date=end_date,
            weekday=rebalance_weekday,
            lookback_periods=roc_period,
            market='NYSE'
        )
        print(f"[OK] Generated {len(schedule)} rebalance dates\n")
        
        # Step 3: Generate trading signals
        print("Step 3/5: Generating trading signals...")
        strategy = MomentumStrategy(roc_period=roc_period, top_n=top_n)
        positions = strategy.generate_rebalance_positions(prices, schedule)
        print(f"[OK] Generated positions for {len(positions)} rebalance dates\n")
        
        # Step 4: Run backtest
        print("Step 4/5: Running backtest...")
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
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    universe_name = ACTIVE_UNIVERSE
    run_name = f"{timestamp}_{universe_name}_ROC{ROC_PERIOD_DAYS}d_Top{TOP_N}"
    run_output_dir = os.path.join(OUTPUT_DIR, run_name)
    
    # Create directory
    Path(run_output_dir).mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("MOMENTUM STRATEGY BACKTEST")
    print("="*80)
    print(f"Run Name: {run_name}")
    print(f"Output Directory: {run_output_dir}")
    print(f"\nConfiguration:")
    print(f"  Universe: {universe_name}")
    print(f"  Start Date: {START_DATE.date()}")
    print(f"  End Date: {END_DATE.date()}")
    print(f"  ROC Period: {ROC_PERIOD_DAYS} days")
    print(f"  Top N: {TOP_N}")
    print(f"  Rebalance: {'Monday' if REBALANCE_WEEKDAY == 0 else 'Weekday ' + str(REBALANCE_WEEKDAY)}")
    print(f"  Initial Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"  Commission: {COMMISSION_PCT*100:.2f}%")
    print(f"  Slippage: {SLIPPAGE_PCT*100:.3f}%")
    print("="*80)
    
    # Run backtest for active universe
    symbols = UNIVERSES[universe_name]
    
    run_backtest_for_universe(
        universe_name=universe_name,
        symbols=symbols,
        start_date=START_DATE,
        end_date=END_DATE,
        roc_period=ROC_PERIOD_DAYS,
        top_n=TOP_N,
        rebalance_weekday=REBALANCE_WEEKDAY,
        initial_capital=INITIAL_CAPITAL,
        commission_pct=COMMISSION_PCT,
        slippage_pct=SLIPPAGE_PCT,
        data_dir=DATA_DIR,
        cache_enabled=CACHE_ENABLED,
        output_dir=run_output_dir
    )
    
    # Save run configuration and create README
    config_file = os.path.join(run_output_dir, "run_config.txt")
    readme_file = os.path.join(run_output_dir, "README.txt")
    
    with open(config_file, 'w') as f:
        f.write(f"Run Name: {run_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Universe: {universe_name}\n")
        f.write(f"Symbols: {', '.join(symbols)}\n")
        f.write(f"Start Date: {START_DATE.date()}\n")
        f.write(f"End Date: {END_DATE.date()}\n")
        f.write(f"ROC Period: {ROC_PERIOD_DAYS} days\n")
        f.write(f"Top N: {TOP_N}\n")
        f.write(f"Rebalance Day: {'Monday' if REBALANCE_WEEKDAY == 0 else 'Weekday ' + str(REBALANCE_WEEKDAY)}\n")
        f.write(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}\n")
        f.write(f"Commission: {COMMISSION_PCT*100:.2f}%\n")
        f.write(f"Slippage: {SLIPPAGE_PCT*100:.3f}%\n")
    
    # Create a comprehensive README
    with open(readme_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write(f"BACKTEST RUN: {run_name}\n")
        f.write("="*80 + "\n\n")
        
        f.write("CONFIGURATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Universe:        {universe_name}\n")
        f.write(f"Period:          {START_DATE.date()} to {END_DATE.date()}\n")
        f.write(f"Strategy:        Top-{TOP_N} Momentum (ROC {ROC_PERIOD_DAYS} days)\n")
        f.write(f"Rebalance:       Every Monday (NYSE calendar)\n")
        f.write(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}\n")
        f.write(f"Costs:           {COMMISSION_PCT*100:.2f}% commission + {SLIPPAGE_PCT*100:.3f}% slippage\n\n")
        
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
