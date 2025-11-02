"""Generate run configuration and README files."""

from typing import Dict, List
from datetime import datetime
import os


def generate_run_config_file(
    output_dir: str,
    run_name: str,
    timestamp: str,
    universe_name: str,
    config: Dict
) -> str:
    """Generate run_config.txt file."""
    config_path = os.path.join(output_dir, "run_config.txt")
    symbols = config['universes'][universe_name]
    
    with open(config_path, 'w') as f:
        f.write(f"Run Name: {run_name}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Universe: {universe_name}\n")
        f.write(f"Symbols: {', '.join(symbols)}\n")
        f.write(f"Start Date: {config['start_date'].date()}\n")
        f.write(f"End Date: {config['end_date'].date()}\n")
        f.write(f"Momentum: {config['momentum_type']} ({config['momentum_period']} days)\n")
        f.write(f"Top N: {config['top_n']}\n")
        _write_filter_config(f, config)
        _write_advanced_filters(f, config)
        f.write(f"Initial Capital: ${config['initial_capital']:,.2f}\n")
        f.write(f"Commission: {config['commission_pct']*100:.2f}%\n")
        f.write(f"Slippage: {config['slippage_pct']*100:.3f}%\n")
    
    return config_path


def _write_filter_config(f, config: Dict) -> None:
    """Write filter configuration section."""
    f.write(f"Rebalance: {config['rebalance_frequency'].capitalize()}")
    if config['rebalance_frequency'] == 'weekly':
        weekday_name = 'Monday' if config['rebalance_weekday'] == 0 else f"Weekday {config['rebalance_weekday']}"
        f.write(f" ({weekday_name})\n")
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
    elif filter_type == 'STORMGUARD':
        f.write(f"Filter: STORMGUARD (5-Component)\n")
        f.write(f"  - VIX Threshold: {config.get('stormguard_volatility_threshold', 20)}\n")
        if config.get('safe_assets'):
            f.write(f"Safe Assets: {', '.join(config['safe_assets'])}\n")
    elif filter_type == 'STORMGUARD_VELOCITY':
        f.write(f"Filter: STORMGUARD-VELOCITY (5-Component + 3-State)\n")
        f.write(f"  - Z-score: {config.get('stormguard_velocity_zscore_threshold', -2.0)}\n")
        if config.get('safe_assets'):
            f.write(f"Safe Assets: {', '.join(config['safe_assets'])}\n")
    else:
        f.write("Filter: NONE\n")


def _write_advanced_filters(f, config: Dict) -> None:
    """Write advanced filter configuration."""
    if config.get('enable_momentum_persistence'):
        f.write(f"Momentum Persistence: ON (min diff: {config.get('momentum_persistence_min_diff', 0.02)*100:.1f}%)\n")
    if config.get('enable_popndrop_filter'):
        f.write(f"PopNDrop Filter: ON (max return: {config.get('popndrop_max_return', 0.15)*100:.1f}%)\n")
    if config.get('enable_volatility_adjustment'):
        f.write(f"Volatility Adjustment: ON (period: {config.get('volatility_adjustment_period', 63)}d)\n")
    if config.get('enable_price_action_filter'):
        f.write(f"Price Action Filter: ON ({config.get('price_action_filter_type')}, lookback: {config.get('price_action_lookback_days', 21)}d)\n")


def generate_readme_file(
    output_dir: str,
    run_name: str,
    universe_name: str,
    config: Dict,
    final_metrics: Dict
) -> str:
    """Generate comprehensive README.txt file."""
    readme_path = os.path.join(output_dir, "README.txt")
    
    with open(readme_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write(f"BACKTEST RUN: {run_name}\n")
        f.write("="*80 + "\n\n")
        
        _write_readme_config(f, universe_name, config)
        _write_readme_files(f, universe_name, config)
        _write_readme_quickstart(f)
        
        if final_metrics:
            _write_readme_results(f, final_metrics)
    
    return readme_path


def _write_readme_config(f, universe_name: str, config: Dict) -> None:
    """Write configuration section of README."""
    f.write("CONFIGURATION\n")
    f.write("-" * 80 + "\n")
    f.write(f"Universe:        {universe_name}\n")
    f.write(f"Period:          {config['start_date'].date()} to {config['end_date'].date()}\n")
    f.write(f"Strategy:        Top-{config['top_n']} Momentum ({config['momentum_type']} {config['momentum_period']} days)\n")
    f.write(f"Rebalance:       {config['rebalance_frequency'].capitalize()}")
    
    if config['rebalance_frequency'] == 'weekly':
        weekday_name = 'Monday' if config['rebalance_weekday'] == 0 else f"Weekday {config['rebalance_weekday']}"
        f.write(f" ({weekday_name})\n")
    else:
        f.write("\n")
    
    f.write(f"Market:          {config.get('market_calendar', 'NYSE')}\n")
    _write_filter_description(f, config)
    _write_advanced_filters_description(f, config)
    f.write(f"Initial Capital: ${config['initial_capital']:,.2f}\n")
    f.write(f"Costs:           {config['commission_pct']*100:.2f}% commission + {config['slippage_pct']*100:.3f}% slippage\n\n")


def _write_filter_description(f, config: Dict) -> None:
    """Write filter description for README."""
    filter_type = config.get('filter_type', 'NONE')
    
    if filter_type == 'DUAL_EMA':
        f.write(f"Filter:          Dual EMA ({config['ema_short_period']}d/{config['ema_long_period']}d)\n")
    elif filter_type == 'SAFETY_SWITCH':
        f.write(f"Filter:          Safety Switch (SPY {config['safety_sma_short']}d/{config['safety_sma_long']}d SMA)\n")
        if config.get('safe_assets'):
            safe_list = ', '.join(config['safe_assets'][:3])
            suffix = '...' if len(config['safe_assets']) > 3 else ''
            f.write(f"                 Safe Assets: {safe_list}{suffix}\n")
    elif filter_type == 'STORMGUARD':
        f.write("Filter:          STORMGUARD (5-Component)\n")
        if config.get('safe_assets'):
            safe_list = ', '.join(config['safe_assets'][:3])
            suffix = '...' if len(config['safe_assets']) > 3 else ''
            f.write(f"                 Safe Assets: {safe_list}{suffix}\n")
    elif filter_type == 'STORMGUARD_VELOCITY':
        f.write("Filter:          STORMGUARD-VELOCITY (3-State)\n")
        if config.get('safe_assets'):
            safe_list = ', '.join(config['safe_assets'][:3])
            suffix = '...' if len(config['safe_assets']) > 3 else ''
            f.write(f"                 Safe Assets: {safe_list}{suffix}\n")
    else:
        f.write("Filter:          NONE\n")


def _write_advanced_filters_description(f, config: Dict) -> None:
    """Write advanced filters description."""
    advanced_filters = []
    if config.get('enable_momentum_persistence'):
        advanced_filters.append(f"Momentum Persistence ({config.get('momentum_persistence_min_diff', 0.02)*100:.1f}%)")
    if config.get('enable_popndrop_filter'):
        advanced_filters.append(f"PopNDrop ({config.get('popndrop_max_return', 0.15)*100:.1f}%)")
    if config.get('enable_volatility_adjustment'):
        advanced_filters.append(f"Vol-Adjusted ({config.get('volatility_adjustment_period', 63)}d)")
    if config.get('enable_price_action_filter'):
        advanced_filters.append(f"Price Action ({config.get('price_action_filter_type')})")
    
    if advanced_filters:
        f.write(f"Enhancements:    {', '.join(advanced_filters)}\n")


def _write_readme_files(f, universe_name: str, config: Dict) -> None:
    """Write files section of README."""
    f.write("FILES IN THIS DIRECTORY\n")
    f.write("-" * 80 + "\n")
    f.write(f"{universe_name}_vs_benchmark.png         - Strategy vs SPY comparison (MOST IMPORTANT)\n")
    f.write(f"{universe_name}_metrics.csv              - Strategy performance metrics\n")
    f.write(f"{universe_name}_benchmark_metrics.csv    - SPY buy & hold metrics\n")
    f.write(f"{universe_name}_comparison.csv           - Side-by-side comparison\n")
    f.write(f"{universe_name}_trades.csv               - Complete trade log\n")
    f.write(f"{universe_name}_equity.csv               - Daily equity curve\n")
    f.write(f"{universe_name}_monthly_returns.png      - Monthly returns heatmap\n")
    f.write(f"{universe_name}_returns_dist.png         - Returns distribution\n\n")


def _write_readme_quickstart(f) -> None:
    """Write quick start section."""
    f.write("QUICK START\n")
    f.write("-" * 80 + "\n")
    f.write("1. Check the comparison plot: *_vs_benchmark.png (MOST IMPORTANT)\n")
    f.write("2. Review metrics: *_comparison.csv\n")
    f.write("3. Examine trades: *_trades.csv\n")
    f.write("4. View equity curve: *_equity_curve*.png\n\n")


def _write_readme_results(f, metrics: Dict) -> None:
    """Write results section."""
    f.write("RESULTS\n")
    f.write("-" * 80 + "\n")
    for key in ['Total Return (%)', 'CAGR (%)', 'Sharpe Ratio', 
                'Sortino Ratio', 'Calmar Ratio', 'Max Drawdown (%)']:
        if key in metrics:
            f.write(f"{key:<30} {metrics[key]:>15.2f}\n")
    f.write("\n")


def log_to_experiments(
    experiments_log: str,
    run_name: str,
    run_output_dir: str,
    universe_name: str,
    config: Dict,
    final_metrics: Dict
) -> None:
    """Append run results to experiments log."""
    if not os.path.exists(experiments_log) or not final_metrics:
        return
    
    with open(experiments_log, 'a') as f:
        f.write(f"\n## {run_name}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("**Configuration:**\n")
        f.write(f"- Universe: {universe_name}\n")
        f.write(f"- Momentum: {config['momentum_type']} ({config['momentum_period']}d)\n")
        f.write(f"- Rebalance: {config['rebalance_frequency']}\n")
        f.write(f"- Filter: {config.get('filter_type', 'NONE')}\n")
        _write_experiments_advanced_filters(f, config)
        f.write("\n**Results:**\n")
        _write_experiments_results(f, final_metrics, run_output_dir)


def _write_experiments_advanced_filters(f, config: Dict) -> None:
    """Write advanced filters to experiments log."""
    advanced = []
    if config.get('enable_momentum_persistence'):
        advanced.append(f"MomPersist({config.get('momentum_persistence_min_diff', 0.02)*100:.1f}%)")
    if config.get('enable_popndrop_filter'):
        advanced.append(f"PopNDrop({config.get('popndrop_max_return', 0.15)*100:.1f}%)")
    if config.get('enable_volatility_adjustment'):
        advanced.append(f"VolAdj({config.get('volatility_adjustment_period', 63)}d)")
    if config.get('enable_price_action_filter'):
        advanced.append(f"PriceAction({config.get('price_action_filter_type')})")
    
    if advanced:
        f.write(f"- Enhancements: {', '.join(advanced)}\n")


def _write_experiments_results(f, metrics: Dict, run_output_dir: str) -> None:
    """Write results to experiments log."""
    f.write(f"- CAGR: {metrics.get('CAGR (%)', 0):.2f}%\n")
    f.write(f"- Sharpe: {metrics.get('Sharpe Ratio', 0):.2f}\n")
    f.write(f"- Sortino: {metrics.get('Sortino Ratio', 0):.2f}\n")
    f.write(f"- Calmar: {metrics.get('Calmar Ratio', 0):.2f}\n")
    f.write(f"- Max DD: {metrics.get('Max Drawdown (%)', 0):.2f}%\n")
    f.write(f"- Total Return: {metrics.get('Total Return (%)', 0):.2f}%\n")
    f.write(f"- Path: `{run_output_dir}`\n\n")

