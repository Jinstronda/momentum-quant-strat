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
from src.backtest_utils import (
    load_filter_data,
    create_strategy_from_config,
    load_ohlc_if_needed
)
from src.run_config_generator import (
    generate_run_config_file,
    generate_readme_file,
    log_to_experiments
)


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
        
        # Step 2: Create rebalance schedule
        print("Step 2/6: Creating rebalance schedule...")
        momentum_period = config.get('momentum_period', 21)
        schedule = create_rebalance_schedule(
            start_date=actual_start_date,
            end_date=end_date,
            frequency=config.get('rebalance_frequency', 'weekly'),
            weekday=rebalance_weekday,
            lookback_periods=momentum_period,
            market=config.get('market_calendar', 'NYSE')
        )
        
        # Calculate minimum data start date needed for signal calculations
        if not schedule.empty:
            min_data_start = schedule['data_start_date'].min()
            data_lookback_days = momentum_period * 3
            min_required_date = actual_start_date - timedelta(days=data_lookback_days)
            prices_start_date = min(min_data_start, min_required_date, earliest_inception)
        else:
            data_lookback_days = momentum_period * 3
            prices_start_date = min(actual_start_date - timedelta(days=data_lookback_days), earliest_inception)
        
        prices = prices_full[(prices_full.index >= prices_start_date) & (prices_full.index <= end_date)]
        print(f"[OK] Generated {len(schedule)} rebalance dates ({config.get('rebalance_frequency', 'weekly')} rebalancing)")
        print(f"[OK] Loaded {len(prices)} days of data for {len(prices.columns)} symbols")
        print(f"     Data range: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"     Backtest starts: {actual_start_date.date()}")
        print(f"     Earliest inception: {earliest_inception.date()}\n")
        
        # Step 3: Generate trading signals
        print("Step 3/6: Generating trading signals...")
        strategy = create_strategy_from_config(config, actual_momentum_type)
        
        # Load filter data (SPY, VIX, safe assets, etc.)
        spy_prices, safe_prices, spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices = load_filter_data(
            config, loader, extended_start, end_date
        )
        
        # Load OHLC data if price action filter enabled
        prices_ohlc = load_ohlc_if_needed(config, loader, symbols, extended_start, end_date)
        
        positions = strategy.generate_rebalance_positions(
            prices, schedule, spy_prices, safe_prices, spy_volume, vix_prices, 
            hyg_prices, ief_prices, rsp_prices, None, prices_ohlc
        )
        
        positions = positions[positions.index >= actual_start_date]
        
        filter_history = strategy.get_filter_history()
        regime_history = strategy.get_regime_history()
        
        cash_positions = positions['position'].isna().sum()
        invested_positions = len(positions) - cash_positions
        
        print(f"[OK] Generated positions for {len(positions)} rebalance dates")
        if actual_momentum_type == 'POLYMORPHIC':
            print(f"     Momentum: POLYMORPHIC (metric: {config['polymorphic_metric']})")
            if filter_history is not None and not filter_history.empty:
                print(f"     Filter changes: {len(filter_history)} re-evaluations")
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
                safe_symbols = set(config.get('safe_assets', []))
                safe_positions = positions['position'].isin(safe_symbols).sum()
                risk_positions = invested_positions - safe_positions
                print(f"     Risk Assets: {risk_positions} | Safe Assets: {safe_positions} | Cash: {cash_positions}")
        elif filter_type == 'STORMGUARD':
            print(f"     Filter: STORMGUARD (5-Component Analysis)")
            if config.get('safe_assets'):
                safe_symbols = set(config.get('safe_assets', []))
                safe_positions = positions['position'].isin(safe_symbols).sum()
                risk_positions = invested_positions - safe_positions
                print(f"       Risk Assets: {risk_positions} | Safe Assets: {safe_positions} | Cash: {cash_positions}")
        elif filter_type == 'STORMGUARD_VELOCITY':
            print(f"     Filter: STORMGUARD-VELOCITY (5-Component + 3-State Machine)")
            if config.get('safe_assets'):
                safe_symbols = set(config.get('safe_assets', []))
                safe_positions = positions['position'].isin(safe_symbols).sum()
                risk_positions = invested_positions - safe_positions
                print(f"       Risk Assets: {risk_positions} | Safe Assets: {safe_positions} | Cash: {cash_positions}")
        else:
            print(f"     Filter: NONE")
        if filter_type not in ['SAFETY_SWITCH', 'STORMGUARD', 'STORMGUARD_VELOCITY'] or not config.get('safe_assets'):
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
        metrics = engine.calculate_metrics(equity_curve, trades)
        print(f"[OK] Backtest complete - {len(trades)} trades executed\n")
        
        # Step 5: Run benchmark (SPY buy & hold)
        print("Step 5/6: Running SPY benchmark...")
        benchmark_runner = BenchmarkRunner(
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct
        )
        
        # Get SPY prices for benchmark - MUST start at actual_start_date (same as strategy)
        if 'SPY' in prices.columns:
            # SPY is in universe, but prices includes lookback data
            # Filter to actual backtest period only
            spy_prices_full = prices['SPY']
            spy_prices = spy_prices_full[spy_prices_full.index >= actual_start_date].copy()
        else:
            # SPY not in universe, download it starting from actual_start_date
            spy_prices = loader.get_close_prices(['SPY'], actual_start_date, end_date)['SPY']
        
        # Benchmark must start at same date as strategy equity curve
        benchmark_start = equity_curve.index[0] if not equity_curve.empty else actual_start_date
        spy_prices_aligned = spy_prices[spy_prices.index >= benchmark_start].copy()
        
        if len(spy_prices_aligned) == 0:
            raise ValueError(f"No SPY data available from {benchmark_start.date()}")
        
        benchmark_equity, benchmark_trades = benchmark_runner.run_buy_and_hold(spy_prices_aligned, "SPY")
        benchmark_metrics = benchmark_runner.calculate_metrics(benchmark_equity, benchmark_trades)
        
        # Verify alignment
        if benchmark_equity.index[0] != equity_curve.index[0]:
            print(f"[WARNING] Benchmark start mismatch:")
            print(f"  Strategy: {equity_curve.index[0].date()}")
            print(f"  Benchmark: {benchmark_equity.index[0].date()}")
        
        print(f"[OK] Benchmark complete (start: {benchmark_equity.index[0].date()}, aligned to strategy)\n")
        
        # Step 6: Generate reports
        print("Step 6/6: Generating reports...")
        reporter = BacktestReporter(output_dir=output_dir)
        
        reporter.create_full_report(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            universe_name=universe_name,
            prices=prices,
            momentum_type=actual_momentum_type,
            momentum_period=config.get('momentum_period', 21),
            filter_history=filter_history,
            regime_history=regime_history,
            spy_prices=spy_prices,
            spy_volume=spy_volume,
            vix_prices=vix_prices,
            hyg_prices=hyg_prices,
            ief_prices=ief_prices,
            rsp_prices=rsp_prices,
            config=config,
            schedule=schedule,
            benchmark_equity=benchmark_equity,
            benchmark_metrics=benchmark_metrics
        )
        
        # Print comparison summary
        relative_metrics = calculate_relative_metrics(metrics, benchmark_metrics)
        
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


def run_multi_bucket_backtest(buckets: list, config: Dict, output_dir: str) -> None:
    """
    Run backtest for multi-bucket portfolio.
    
    Args:
        buckets: List of (universe_name, allocation) tuples
        config: Configuration dictionary
        output_dir: Output directory for results
    """
    start_date = config['start_date']
    end_date = config['end_date']
    initial_capital = config['initial_capital']
    commission_pct = config['commission_pct']
    slippage_pct = config['slippage_pct']
    data_dir = config['data_dir']
    cache_enabled = config['cache_enabled']
    
    portfolio_name = "+".join([f"{int(alloc*100)}{name[:3]}" for name, alloc in buckets])
    
    print(f"\n{'='*80}")
    print(f"Running MULTI-BUCKET backtest: {portfolio_name}")
    print(f"Buckets: {len(buckets)}")
    for bucket_name, allocation in buckets:
        print(f"  - {bucket_name}: {allocation*100:.0f}%")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"{'='*80}\n")
    
    try:
        # Step 1: Load data for all buckets
        print("Step 1/6: Loading price data for all buckets...")
        loader = DataLoader(data_dir=data_dir, cache_enabled=cache_enabled)
        
        extended_start = datetime(start_date.year - 10, 1, 1)
        prices_dict = {}
        all_symbols = set()
        
        for bucket_name, _ in buckets:
            symbols = config['universes'][bucket_name]
            all_symbols.update(symbols)
            bucket_prices = loader.get_close_prices(symbols, extended_start, end_date)
            prices_dict[bucket_name] = bucket_prices
        
        print(f"[OK] Loaded {len(buckets)} buckets with {len(all_symbols)} unique symbols\n")
        
        # Find earliest inception date across ALL buckets (same as single-bucket)
        all_first_valid_dates = []
        for bucket_name, _ in buckets:
            bucket_prices = prices_dict[bucket_name]
            for col in bucket_prices.columns:
                first_valid = bucket_prices[col].first_valid_index()
                if first_valid is not None:
                    all_first_valid_dates.append(first_valid)
        
        earliest_inception = max(all_first_valid_dates) if all_first_valid_dates else start_date
        
        # Check if we have enough history for polymorphic
        actual_start_date = start_date
        actual_momentum_type = config.get('momentum_type', 'ROC')
        
        if actual_momentum_type == 'POLYMORPHIC':
            min_history_years = config.get('polymorphic_min_history_years', 5)
            required_history_start = start_date - timedelta(days=min_history_years * 365)
            
            if earliest_inception > required_history_start:
                years_available = (start_date - earliest_inception).days / 365
                print(f"\n[WARNING] Insufficient history for POLYMORPHIC mode")
                print(f"          Earliest asset inception: {earliest_inception.date()}")
                print(f"          Available history: {years_available:.1f} years")
                print(f"          Required: {min_history_years} years before {start_date.date()}")
                
                adjusted_start = earliest_inception + timedelta(days=min_history_years * 365)
                if adjusted_start < end_date:
                    print(f"          Adjusting start date to {adjusted_start.date()}\n")
                    actual_start_date = adjusted_start
                else:
                    fallback_type = config.get('polymorphic_fallback_momentum', 'ROC')
                    print(f"          Falling back to {fallback_type} momentum\n")
                    actual_momentum_type = fallback_type
        
        # Step 2: Create rebalance schedule
        print("Step 2/6: Creating rebalance schedule...")
        momentum_period = config.get('momentum_period', 21)
        schedule = create_rebalance_schedule(
            start_date=actual_start_date,
            end_date=end_date,
            frequency=config.get('rebalance_frequency', 'weekly'),
            weekday=config.get('rebalance_weekday', 0),
            lookback_periods=momentum_period,
            market=config.get('market_calendar', 'NYSE')
        )
        
        # Calculate data start date (need lookback for momentum calculation)
        if not schedule.empty:
            min_data_start = schedule['data_start_date'].min()
            data_lookback_days = momentum_period * 3
            min_required_date = actual_start_date - timedelta(days=data_lookback_days)
            prices_start_date = min(min_data_start, min_required_date, earliest_inception)
        else:
            data_lookback_days = momentum_period * 3
            prices_start_date = min(actual_start_date - timedelta(days=data_lookback_days), earliest_inception)
        
        # Trim all bucket prices to include lookback data
        for bucket_name in prices_dict.keys():
            bucket_prices = prices_dict[bucket_name]
            prices_dict[bucket_name] = bucket_prices[
                (bucket_prices.index >= prices_start_date) & (bucket_prices.index <= end_date)
            ]
        
        print(f"[OK] Generated {len(schedule)} rebalance dates")
        print(f"     Backtest period: {actual_start_date.date()} to {end_date.date()}")
        print(f"     Earliest asset inception: {earliest_inception.date()}")
        print(f"     Data starts: {prices_start_date.date()} (includes lookback)\n")
        
        # Step 3: Load filter data
        print("Step 3/6: Loading filter data...")
        spy_prices, safe_prices, spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices = load_filter_data(
            config, loader, extended_start, end_date
        )
        
        # Step 4: Generate positions
        print("Step 4/6: Generating multi-bucket positions...")
        strategy = create_strategy_from_config(config, actual_momentum_type)
        
        # Load OHLC data for all buckets if needed
        prices_ohlc_dict = None
        if config.get('enable_price_action_filter', False):
            print(f"Loading OHLC data for price action filter...")
            prices_ohlc_dict = {}
            for bucket_name, _ in buckets:
                bucket_symbols = config['universes'][bucket_name]
                prices_ohlc_dict[bucket_name] = loader.get_ohlc_prices(
                    bucket_symbols, extended_start, end_date
                )
            print(f"[OK] OHLC data loaded for all buckets\n")
        
        positions = strategy.generate_multi_bucket_positions(
            buckets, prices_dict, schedule,
            spy_prices, safe_prices, spy_volume, vix_prices,
            hyg_prices, ief_prices, rsp_prices, None, prices_ohlc_dict
        )
        
        regime_history = strategy.get_regime_history()
        print(f"[OK] Generated positions for {len(positions)} rebalance dates\n")
        
        # Step 5: Run backtest
        print("Step 5/6: Running multi-bucket backtest...")
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct
        )
        equity_curve, trades = engine.run_multi_bucket_backtest(prices_dict, positions, buckets)
        metrics = engine.calculate_metrics(equity_curve, trades)
        print(f"[OK] Backtest complete - {len(trades)} trades executed\n")
        
        # Step 6: Run benchmark and generate reports
        print("Step 6/6: Running benchmark and generating reports...")
        benchmark_runner = BenchmarkRunner(
            initial_capital=initial_capital,
            commission_pct=commission_pct,
            slippage_pct=slippage_pct
        )
        
        spy_benchmark = loader.get_close_prices(['SPY'], actual_start_date, end_date)['SPY']
        benchmark_start = equity_curve.index[0] if not equity_curve.empty else actual_start_date
        spy_aligned = spy_benchmark[spy_benchmark.index >= benchmark_start].copy()
        
        if len(spy_aligned) == 0:
            raise ValueError(f"No SPY data from {benchmark_start.date()}")
        
        benchmark_equity, benchmark_trades = benchmark_runner.run_buy_and_hold(spy_aligned, "SPY")
        benchmark_metrics = benchmark_runner.calculate_metrics(benchmark_equity, benchmark_trades)
        
        # Verify alignment
        if benchmark_equity.index[0] != equity_curve.index[0]:
            print(f"[WARNING] Benchmark start mismatch:")
            print(f"  Strategy: {equity_curve.index[0].date()}")
            print(f"  Benchmark: {benchmark_equity.index[0].date()}")
        
        print(f"[OK] Benchmark complete (start: {benchmark_equity.index[0].date()}, aligned to strategy)\n")
        
        reporter = BacktestReporter(output_dir=output_dir)
        reporter.create_full_report(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            universe_name=portfolio_name,
            config=config,
            regime_history=regime_history,
            benchmark_equity=benchmark_equity,
            benchmark_metrics=benchmark_metrics,
            buckets=buckets
        )
        
        print(f"\n{'='*80}")
        print(f"Multi-bucket backtest complete: {portfolio_name}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n{'!'*80}")
        print(f"ERROR: Multi-bucket backtest failed")
        print(f"Error: {str(e)}")
        print(f"{'!'*80}\n")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main entry point for running backtests."""
    config = get_config()
    
    # Multi-bucket mode
    if config.get('is_multi_bucket', False):
        buckets = config['active_universes']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        freq = "W" if config['rebalance_frequency'] == 'weekly' else "M"
        run_name = f"{timestamp}_MultiBucket_{config['momentum_type']}{config['momentum_period']}d_{freq}"
        run_output_dir = os.path.join(config['output_dir'], run_name)
        
        Path(run_output_dir).mkdir(parents=True, exist_ok=True)
        
        print("\n" + "="*80)
        print("MULTI-BUCKET PORTFOLIO BACKTEST")
        print("="*80)
        print(f"Run Name: {run_name}")
        print(f"Buckets: {len(buckets)}")
        for name, alloc in buckets:
            print(f"  - {name}: {alloc*100:.0f}%")
        print(f"Momentum: {config['momentum_type']} ({config['momentum_period']}d)")
        print(f"Filter: {config.get('filter_type', 'NONE')}")
        print(f"Output Directory: {run_output_dir}")
        print("="*80)
        
        run_multi_bucket_backtest(buckets, config, run_output_dir)
        
        print("\n" + "="*80)
        print("MULTI-BUCKET BACKTEST COMPLETE")
        print("="*80 + "\n")
        return
    
    # Single-bucket mode
    if isinstance(ACTIVE_UNIVERSE, str):
        universe_name = ACTIVE_UNIVERSE
    else:
        raise ValueError("ACTIVE_UNIVERSE must be a string in single-bucket mode.")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    freq = "W" if config['rebalance_frequency'] == 'weekly' else "M"
    run_name = f"{timestamp}_{universe_name}_{config['momentum_type']}{config['momentum_period']}d_{freq}_Top{config['top_n']}"
    run_output_dir = os.path.join(config['output_dir'], run_name)
    
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
        weekday_name = 'Monday' if config['rebalance_weekday'] == 0 else f"Weekday {config['rebalance_weekday']}"
        print(f" ({weekday_name})")
    else:
        print()
    
    filter_type = config.get('filter_type', 'NONE')
    if filter_type == 'DUAL_EMA':
        print(f"  Filter: Dual EMA ({config['ema_short_period']}d/{config['ema_long_period']}d)")
    elif filter_type == 'SAFETY_SWITCH':
        print(f"  Filter: Safety Switch (SPY {config['safety_sma_short']}d/{config['safety_sma_long']}d SMA)")
    else:
        print(f"  Filter: NONE")
    
    print(f"  Initial Capital: ${config['initial_capital']:,.0f}")
    print(f"  Commission: {config['commission_pct']*100:.2f}%")
    print(f"  Slippage: {config['slippage_pct']*100:.3f}%")
    print("="*80)
    
    # Run backtest
    run_backtest_for_universe(
        universe_name=universe_name,
        config=config,
        output_dir=run_output_dir
    )
    
    # Get metrics for reporting
    metrics_file = os.path.join(run_output_dir, f"{universe_name}_metrics.csv")
    final_metrics = {}
    if os.path.exists(metrics_file):
        metrics_df = pd.read_csv(metrics_file, index_col=0)
        final_metrics = metrics_df['Value'].to_dict()
    
    # Generate configuration and documentation
    config_file = generate_run_config_file(
        run_output_dir, run_name, timestamp, universe_name, config
    )
    readme_file = generate_readme_file(
        run_output_dir, run_name, universe_name, config, final_metrics
    )
    
    print(f"\nRun configuration saved to: {config_file}")
    print(f"README created: {readme_file}")
    
    # Log to experiments
    log_to_experiments(
        config.get('experiments_log', 'experiments/experiments.md'),
        run_name, run_output_dir, universe_name, config, final_metrics
    )
    
    if final_metrics:
        print(f"Results logged to: {config.get('experiments_log', 'experiments/experiments.md')}")
    
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
