"""Main script to run momentum strategy backtests."""

import sys
import os
from typing import Dict
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

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
        # Step 1: Load data and check inception dates
        print("Step 1/6: Loading price data...")
        loader = DataLoader(data_dir=data_dir, cache_enabled=cache_enabled)
        
        # Load a wider date range to find asset inception dates
        extended_start = datetime(start_date.year - 10, 1, 1)
        prices_full = loader.get_close_prices(
            symbols=symbols,
            start_date=extended_start,
            end_date=end_date,
            force_refresh=False
        )
        
        # Find earliest date with valid data for ALL assets
        first_valid_dates = []
        for col in prices_full.columns:
            first_valid = prices_full[col].first_valid_index()
            if first_valid is not None:
                first_valid_dates.append(first_valid)
        
        earliest_inception = max(first_valid_dates) if first_valid_dates else start_date
        
        # Check if we have enough history for polymorphic
        actual_start_date = start_date
        actual_momentum_type = config.get('momentum_type', 'ROC')
        
        if actual_momentum_type == 'POLYMORPHIC':
            min_history_years = config.get('polymorphic_min_history_years', 5)
            required_history_start = start_date - timedelta(days=min_history_years * 365)
            
            if earliest_inception > required_history_start:
                # Insufficient history for polymorphic
                years_available = (start_date - earliest_inception).days / 365
                print(f"\n[WARNING] Insufficient history for POLYMORPHIC mode")
                print(f"          Earliest asset inception: {earliest_inception.date()}")
                print(f"          Available history: {years_available:.1f} years")
                print(f"          Required: {min_history_years} years before {start_date.date()}")
                
                # Option 1: Adjust start date forward
                adjusted_start = earliest_inception + timedelta(days=min_history_years * 365)
                if adjusted_start < end_date:
                    print(f"          Adjusting start date to {adjusted_start.date()} (after {min_history_years} years of history)")
                    actual_start_date = adjusted_start
                else:
                    # Option 2: Fall back to simpler momentum
                    fallback_type = config.get('polymorphic_fallback_momentum', 'ROC')
                    print(f"          Cannot adjust start date (would exceed end date)")
                    print(f"          Falling back to {fallback_type} momentum\n")
                    actual_momentum_type = fallback_type
        
        # Trim prices to actual date range
        prices = prices_full[(prices_full.index >= actual_start_date) & (prices_full.index <= end_date)]
        print(f"[OK] Loaded {len(prices)} days of data for {len(prices.columns)} symbols")
        print(f"     Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"     Earliest inception: {earliest_inception.date()}\n")
        
        # Step 2: Create rebalance schedule
        print("Step 2/6: Creating rebalance schedule...")
        schedule = create_rebalance_schedule(
            start_date=actual_start_date,
            end_date=end_date,
            frequency=config.get('rebalance_frequency', 'weekly'),
            weekday=rebalance_weekday,
            lookback_periods=config.get('momentum_period', 21),
            market=config.get('market_calendar', 'NYSE')
        )
        print(f"[OK] Generated {len(schedule)} rebalance dates ({config.get('rebalance_frequency', 'weekly')} rebalancing)\n")
        
        # Step 3: Generate trading signals
        print("Step 3/6: Generating trading signals...")
        strategy = MomentumStrategy(
            momentum_type=actual_momentum_type,
            momentum_period=config.get('momentum_period', 21),
            top_n=top_n,
            filter_type=config.get('filter_type', 'NONE'),
            ema_short=config.get('ema_short_period', 20),
            ema_long=config.get('ema_long_period', 50),
            ema_derivative_lookback=config.get('ema_derivative_lookback', 10),
            safety_sma_short=config.get('safety_sma_short', 50),
            safety_sma_long=config.get('safety_sma_long', 200),
            stormguard_dema_fast=config.get('stormguard_dema_fast', 50),
            stormguard_dema_slow=config.get('stormguard_dema_slow', 100),
            stormguard_obv_sma=config.get('stormguard_obv_sma', 50),
            stormguard_vix_sma=config.get('stormguard_vix_sma', 50),
            polymorphic_metric=config.get('polymorphic_metric', 'Sharpe'),
            polymorphic_initial_years=config.get('polymorphic_initial_years', 5),
            polymorphic_reeval_years=config.get('polymorphic_reeval_years', 2),
            initial_capital=initial_capital
        )
        
        # Get SPY, safe assets, volume, VIX if needed for filters
        spy_prices = None
        safe_prices = None
        spy_volume = None
        vix_prices = None
        
        if config.get('filter_type') == 'SAFETY_SWITCH':
            # Load SPY if not in universe (needed for market regime check)
            if 'SPY' in prices.columns:
                spy_prices = prices['SPY']
            else:
                print("Loading SPY for Safety Switch filter...")
                spy_df = loader.get_close_prices(['SPY'], extended_start, end_date)
                spy_prices = spy_df['SPY']
                print("[OK] SPY loaded\n")
            
            # Load safe assets for bear market rotation
            safe_assets = config.get('safe_assets', [])
            if safe_assets:
                print(f"Loading {len(safe_assets)} safe assets for bear market rotation...")
                safe_prices = loader.get_close_prices(safe_assets, extended_start, end_date)
                print(f"[OK] Loaded safe assets: {', '.join(safe_assets)}\n")
        
        elif config.get('filter_type') == 'STORMGUARD':
            print("Loading data for STORMGUARD 3-component filter...")
            
            # Load SPY with volume
            print("  Component 1: Price Trend (DEMA) - loading SPY...")
            print("  Component 2: Money Flow (OBV) - loading SPY volume...")
            spy_prices, spy_volume = loader.get_symbol_with_volume('SPY', extended_start, end_date)
            
            # Load VIX
            print("  Component 3: Sentiment (VIX) - loading VIX...")
            vix_prices, _ = loader.get_symbol_with_volume('^VIX', extended_start, end_date)
            
            print("[OK] Loaded SPY (price + volume) and VIX\n")
            
            # Load safe assets for bear market rotation
            safe_assets = config.get('safe_assets', [])
            if safe_assets:
                print(f"Loading {len(safe_assets)} safe assets for bear market rotation...")
                safe_prices = loader.get_close_prices(safe_assets, extended_start, end_date)
                print(f"[OK] Loaded safe assets: {', '.join(safe_assets)}\n")
        
        positions = strategy.generate_rebalance_positions(
            prices, schedule, spy_prices, safe_prices, spy_volume, vix_prices
        )
        
        # Get filter history if using polymorphic momentum
        filter_history = strategy.get_filter_history()
        
        # Count cash positions
        cash_positions = positions['position'].isna().sum()
        invested_positions = len(positions) - cash_positions
        
        print(f"[OK] Generated positions for {len(positions)} rebalance dates")
        if actual_momentum_type == 'POLYMORPHIC':
            print(f"     Momentum: POLYMORPHIC (metric: {config['polymorphic_metric']})")
            if filter_history is not None and not filter_history.empty:
                print(f"     Filter changes: {len(filter_history)} re-evaluations")
                # Show filter distribution
                filter_counts = filter_history['filter_type'].value_counts()
                print(f"     Filter usage: {dict(filter_counts)}")
        else:
            print(f"     Momentum: {actual_momentum_type} ({config.get('momentum_period')}d)")
        
        filter_type = config.get('filter_type', 'NONE')
        if filter_type == 'DUAL_EMA':
            print(f"     Filter: Dual EMA ({config['ema_short_period']}d/{config['ema_long_period']}d, derivative: {config['ema_derivative_lookback']}d)")
        elif filter_type == 'SAFETY_SWITCH':
            print(f"     Filter: Safety Switch (SPY {config['safety_sma_short']}d/{config['safety_sma_long']}d SMA)")
            if config.get('safe_assets'):
                # Count safe asset positions
                safe_symbols = set(config.get('safe_assets', []))
                safe_positions = positions['position'].isin(safe_symbols).sum()
                risk_positions = invested_positions - safe_positions
                print(f"     Risk Assets: {risk_positions} | Safe Assets: {safe_positions} | Cash: {cash_positions}")
        elif filter_type == 'STORMGUARD':
            print(f"     Filter: STORMGUARD 3-Component")
            print(f"       1. Price Trend: DEMA({config['stormguard_dema_fast']}/{config['stormguard_dema_slow']})")
            print(f"       2. Money Flow: OBV > SMA({config['stormguard_obv_sma']})")
            print(f"       3. Sentiment: VIX < VIX_SMA({config['stormguard_vix_sma']})")
            if config.get('safe_assets'):
                # Count safe asset positions
                safe_symbols = set(config.get('safe_assets', []))
                safe_positions = positions['position'].isin(safe_symbols).sum()
                risk_positions = invested_positions - safe_positions
                print(f"     Risk Assets: {risk_positions} | Safe Assets: {safe_positions} | Cash: {cash_positions}")
        else:
            print(f"     Filter: NONE")
        if filter_type not in ['SAFETY_SWITCH', 'STORMGUARD'] or not config.get('safe_assets'):
            print(f"     Invested: {invested_positions} | Cash: {cash_positions}")
        print()
        
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
        
        # Get SPY prices - use actual_start_date to match strategy start date
        if 'SPY' in prices.columns:
            # SPY already loaded, align to actual_start_date
            spy_prices = prices['SPY']
        else:
            # If SPY not in universe, download it starting from actual_start_date
            spy_prices = loader.get_close_prices(['SPY'], actual_start_date, end_date)['SPY']
        
        # Ensure benchmark starts at same date as strategy (align indices)
        benchmark_start = equity_curve.index[0] if not equity_curve.empty else actual_start_date
        spy_prices_aligned = spy_prices[spy_prices.index >= benchmark_start].copy()
        
        benchmark_equity, benchmark_trades = benchmark_runner.run_buy_and_hold(spy_prices_aligned, "SPY")
        benchmark_metrics = benchmark_runner.calculate_metrics(benchmark_equity)
        print(f"[OK] Benchmark complete (aligned to strategy start: {benchmark_start.date()})\n")
        
        # Step 6: Generate reports with benchmark comparison
        print("Step 6/6: Generating reports...")
        reporter = BacktestReporter(output_dir=output_dir)
        
        # Generate strategy reports
        reporter.create_full_report(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            universe_name=universe_name,
            prices=prices,
            momentum_type=actual_momentum_type,
            momentum_period=config.get('momentum_period', 21),
            filter_history=filter_history,
            spy_prices=spy_prices,
            spy_volume=spy_volume,
            vix_prices=vix_prices,
            config=config
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
            ('Sortino Ratio', 'Sortino Ratio'),
            ('Calmar Ratio', 'Calmar Ratio'),
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
    freq = "W" if config['rebalance_frequency'] == 'weekly' else "M"
    run_name = f"{timestamp}_{universe_name}_{config['momentum_type']}{config['momentum_period']}d_{freq}_Top{config['top_n']}"
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
    print(f"  Momentum: {config['momentum_type']} ({config['momentum_period']} days)")
    print(f"  Top N: {config['top_n']}")
    print(f"  Rebalance: {config['rebalance_frequency'].capitalize()}", end="")
    if config['rebalance_frequency'] == 'weekly':
        print(f" ({'Monday' if config['rebalance_weekday'] == 0 else 'Weekday ' + str(config['rebalance_weekday'])})")
    else:
        print()
    
    # Show filter status
    filter_type = config.get('filter_type', 'NONE')
    if filter_type == 'DUAL_EMA':
        print(f"  Filter: Dual EMA ({config['ema_short_period']}d/{config['ema_long_period']}d, {config['ema_derivative_lookback']}d slope)")
    elif filter_type == 'SAFETY_SWITCH':
        print(f"  Filter: Safety Switch (SPY {config['safety_sma_short']}d/{config['safety_sma_long']}d SMA)")
    else:
        print(f"  Filter: NONE")
    
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
    
    # Get metrics for logging
    metrics_file = os.path.join(run_output_dir, f"{universe_name}_metrics.csv")
    final_metrics = {}
    if os.path.exists(metrics_file):
        metrics_df = pd.read_csv(metrics_file, index_col=0)
        final_metrics = metrics_df['Value'].to_dict()
    
    with open(config_file, 'w') as f:
        f.write(f"Run Name: {run_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Universe: {universe_name}\n")
        f.write(f"Symbols: {', '.join(symbols)}\n")
        f.write(f"Start Date: {config['start_date'].date()}\n")
        f.write(f"End Date: {config['end_date'].date()}\n")
        f.write(f"Momentum: {config['momentum_type']} ({config['momentum_period']} days)\n")
        f.write(f"Top N: {config['top_n']}\n")
        f.write(f"Rebalance: {config['rebalance_frequency'].capitalize()}")
        if config['rebalance_frequency'] == 'weekly':
            f.write(f" ({'Monday' if config['rebalance_weekday'] == 0 else 'Weekday ' + str(config['rebalance_weekday'])})\n")
        else:
            f.write("\n")
        f.write(f"Market: {config.get('market_calendar', 'NYSE')}\n")
        filter_type = config.get('filter_type', 'NONE')
        if filter_type == 'DUAL_EMA':
            f.write(f"Filter: Dual EMA ({config['ema_short_period']}d/{config['ema_long_period']}d, derivative: {config['ema_derivative_lookback']}d)\n")
        elif filter_type == 'SAFETY_SWITCH':
            f.write(f"Filter: Safety Switch (SPY {config['safety_sma_short']}d/{config['safety_sma_long']}d SMA)\n")
            if config.get('safe_assets'):
                f.write(f"Safe Assets: {', '.join(config['safe_assets'])}\n")
        else:
            f.write(f"Filter: NONE\n")
        
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
        f.write(f"Strategy:        Top-{config['top_n']} Momentum ({config['momentum_type']} {config['momentum_period']} days)\n")
        f.write(f"Rebalance:       {config['rebalance_frequency'].capitalize()}")
        if config['rebalance_frequency'] == 'weekly':
            f.write(f" ({'Monday' if config['rebalance_weekday'] == 0 else 'Weekday ' + str(config['rebalance_weekday'])})\n")
        else:
            f.write("\n")
        f.write(f"Market:          {config.get('market_calendar', 'NYSE')}\n")
        filter_type = config.get('filter_type', 'NONE')
        if filter_type == 'DUAL_EMA':
            f.write(f"Filter:          Dual EMA ({config['ema_short_period']}d/{config['ema_long_period']}d, {config['ema_derivative_lookback']}d slope)\n")
            f.write(f"                 Price>{config['ema_short_period']}d, {config['ema_short_period']}d>{config['ema_long_period']}d, {config['ema_long_period']}d slope>0\n")
        elif filter_type == 'SAFETY_SWITCH':
            f.write(f"Filter:          Safety Switch (SPY {config['safety_sma_short']}d/{config['safety_sma_long']}d SMA)\n")
            f.write(f"                 Bull: SPY.SMA({config['safety_sma_short']}) > SMA({config['safety_sma_long']}) -> Trade risk assets\n")
            if config.get('safe_assets'):
                f.write(f"                 Bear: SPY.SMA({config['safety_sma_short']}) < SMA({config['safety_sma_long']}) -> Rotate to safe assets\n")
                f.write(f"                 Safe Assets: {', '.join(config['safe_assets'][:3])}{'...' if len(config['safe_assets']) > 3 else ''}\n")
            else:
                f.write(f"                 Bear: SPY.SMA({config['safety_sma_short']}) < SMA({config['safety_sma_long']}) -> CASH\n")
        else:
            f.write(f"Filter:          NONE\n")
        
        f.write(f"\n")
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
        f.write(f"{universe_name}_equity_curve.png         - Strategy equity chart (color-coded)\n")
        f.write(f"{universe_name}_vs_benchmark.png         - Strategy vs SPY comparison\n")
        f.write(f"{universe_name}_drawdown.png             - Drawdown analysis\n")
        f.write(f"{universe_name}_monthly_returns.png      - Monthly returns heatmap\n")
        f.write(f"{universe_name}_returns_dist.png         - Returns distribution\n")
        f.write(f"{universe_name}_momentum_over_time.png   - All stocks' momentum ({config['momentum_type']}) over time\n\n")
        
        f.write("QUICK START\n")
        f.write("-" * 80 + "\n")
        f.write("1. Check the comparison plot: *_vs_benchmark.png\n")
        f.write("2. Review metrics: *_comparison.csv\n")
        f.write("3. Examine trades: *_trades.csv\n")
        f.write("4. Analyze drawdowns: *_drawdown.png\n\n")
        
        # Add performance results if available
        if final_metrics:
            f.write("RESULTS\n")
            f.write("-" * 80 + "\n")
            for key in ['Total Return (%)', 'CAGR (%)', 'Sharpe Ratio', 'Sortino Ratio', 
                       'Calmar Ratio', 'Max Drawdown (%)']:
                if key in final_metrics:
                    f.write(f"{key:<30} {final_metrics[key]:>15.2f}\n")
            f.write("\n")
    
    print(f"\nRun configuration saved to: {config_file}")
    print(f"README created: {readme_file}")
    
    # Auto-append to experiments log
    experiments_log = config.get('experiments_log', 'experiments/experiments.md')
    if os.path.exists(experiments_log) and final_metrics:
        with open(experiments_log, 'a') as f:
            f.write(f"\n## {run_name}\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Configuration:**\n")
            f.write(f"- Universe: {universe_name}\n")
            f.write(f"- Momentum: {config['momentum_type']} ({config['momentum_period']}d)\n")
            f.write(f"- Rebalance: {config['rebalance_frequency']}\n")
            filter_type = config.get('filter_type', 'NONE')
            f.write(f"- Filter: {filter_type}")
            if filter_type == 'DUAL_EMA':
                f.write(f" ({config['ema_short_period']}/{config['ema_long_period']}/{config['ema_derivative_lookback']}d)")
            elif filter_type == 'SAFETY_SWITCH':
                f.write(f" (SPY {config['safety_sma_short']}/{config['safety_sma_long']}d)")
                if config.get('safe_assets'):
                    f.write(f" + {len(config['safe_assets'])} safe assets")
            f.write("\n\n")
            f.write(f"**Results:**\n")
            f.write(f"- CAGR: {final_metrics.get('CAGR (%)', 0):.2f}%\n")
            f.write(f"- Sharpe: {final_metrics.get('Sharpe Ratio', 0):.2f}\n")
            f.write(f"- Sortino: {final_metrics.get('Sortino Ratio', 0):.2f}\n")
            f.write(f"- Calmar: {final_metrics.get('Calmar Ratio', 0):.2f}\n")
            f.write(f"- Max DD: {final_metrics.get('Max Drawdown (%)', 0):.2f}%\n")
            f.write(f"- Total Return: {final_metrics.get('Total Return (%)', 0):.2f}%\n")
            f.write(f"- Path: `{run_output_dir}`\n\n")
        print(f"Results logged to: {experiments_log}")
    
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
