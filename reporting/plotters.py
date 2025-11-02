"""Plotting functions for backtest visualizations."""

from pathlib import Path
from typing import Dict, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D

from reporting.colors import get_filter_color, get_position_color


def _build_filter_date_mapping(filter_history, equity_index):
    """Build mapping of dates to active filters."""
    filter_history_copy = filter_history.copy()
    filter_history_copy['filter_name'] = (
        filter_history_copy['filter_type'] + '(' + 
        filter_history_copy['filter_period'].astype(str) + ')'
    )
    filter_history_copy['date'] = pd.to_datetime(filter_history_copy['date'])
    
    date_to_filter = {}
    for i in range(len(filter_history_copy)):
        start_date = filter_history_copy.iloc[i]['date']
        filter_name = filter_history_copy.iloc[i]['filter_name']
        
        if i < len(filter_history_copy) - 1:
            end_date = filter_history_copy.iloc[i + 1]['date']
        else:
            end_date = equity_index[-1]
        
        for date in equity_index:
            if start_date <= date < end_date:
                date_to_filter[date] = filter_name
            elif i == len(filter_history_copy) - 1 and date >= start_date:
                date_to_filter[date] = filter_name
    
    return date_to_filter, filter_history_copy


def _plot_filter_segments(ax, equity, date_to_filter):
    """Plot equity curve segments colored by filter."""
    prev_filter = None
    segment_start = 0
    legend_filters = set()
    
    for i in range(len(equity)):
        current_filter = date_to_filter.get(equity.index[i])
        is_last = (i == len(equity) - 1)
        filter_changed = (current_filter != prev_filter)
        
        if (filter_changed or is_last) and segment_start < i:
            filter_name = prev_filter if prev_filter else current_filter
            color = get_filter_color(filter_name)
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
    
    ax.legend(loc='upper left', title='Active Filter', fontsize=9, ncol=2)


def _plot_position_segments(ax, equity, equity_curve):
    """Plot equity curve segments colored by position."""
    prev_position = None
    segment_start = 0
    legend_positions = set()
    positions = equity_curve['position'].unique()
    
    for i in range(len(equity_curve)):
        current_position = equity_curve['position'].iloc[i]
        is_last = (i == len(equity_curve) - 1)
        
        position_changed = False
        if pd.isna(current_position) and pd.isna(prev_position):
            position_changed = False
        elif pd.isna(current_position) or pd.isna(prev_position):
            position_changed = True
        else:
            position_changed = (current_position != prev_position)
        
        if position_changed or is_last:
            if prev_position is not None or segment_start < i or is_last:
                display_position = 'CASH' if pd.isna(prev_position) else prev_position
                color = get_position_color(prev_position)
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
    
    handles, labels = [], []
    for pos in positions:
        display_pos = 'CASH' if pd.isna(pos) else pos
        color = get_position_color(pos)
        handles.append(Line2D([0], [0], color=color, linewidth=2.5))
        labels.append(display_pos)
    
    if handles:
        ax.legend(handles, labels, loc='upper left', title='Holdings', fontsize=9, ncol=2)


def plot_equity_curve(
    output_dir: Path,
    equity_curve: pd.DataFrame,
    title: str = "Equity Curve",
    filename: str = "equity_curve.png",
    show_initial: bool = True,
    filter_history: Optional[pd.DataFrame] = None
) -> None:
    """Plot and save equity curve with color-coded positions or filters."""
    fig, ax = plt.subplots(figsize=(16, 8))
    equity = equity_curve['equity']
    
    if filter_history is not None and not filter_history.empty:
        date_to_filter, _ = _build_filter_date_mapping(filter_history, equity.index)
        _plot_filter_segments(ax, equity, date_to_filter)
    elif 'position' in equity_curve.columns:
        _plot_position_segments(ax, equity, equity_curve)
    else:
        ax.plot(equity.index, equity.values, linewidth=2, 
                label='Portfolio Equity', color='#2E86AB')
    
    if show_initial:
        ax.axhline(y=equity.iloc[0], color='gray', linestyle='--', 
                  alpha=0.4, linewidth=1.5)
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Equity ($)', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.tight_layout()
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Equity curve plot saved to {output_path}")


def plot_drawdown(
    output_dir: Path,
    equity_curve: pd.DataFrame,
    title: str = "Drawdown",
    filename: str = "drawdown.png"
) -> None:
    """Plot and save drawdown chart."""
    equity = equity_curve['equity']
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max * 100
    
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, 
                    color='red', label='Drawdown')
    ax.plot(drawdown.index, drawdown.values, linewidth=1.5, color='darkred')
    
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
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Drawdown (%)', fontsize=12)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Drawdown plot saved to {output_path}")


def plot_returns_distribution(
    output_dir: Path,
    equity_curve: pd.DataFrame,
    title: str = "Daily Returns Distribution",
    filename: str = "returns_distribution.png"
) -> None:
    """Plot distribution of daily returns."""
    from scipy import stats
    
    daily_returns = equity_curve['equity'].pct_change().dropna() * 100
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    ax1.hist(daily_returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
    ax1.axvline(daily_returns.mean(), color='red', linestyle='--', 
               label=f'Mean: {daily_returns.mean():.3f}%')
    ax1.axvline(0, color='gray', linestyle='-', alpha=0.5)
    ax1.set_title('Returns Histogram', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Daily Return (%)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    stats.probplot(daily_returns, dist="norm", plot=ax2)
    ax2.set_title('Q-Q Plot', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Returns distribution plot saved to {output_path}")


def plot_monthly_returns(
    output_dir: Path,
    equity_curve: pd.DataFrame,
    title: str = "Monthly Returns Heatmap",
    filename: str = "monthly_returns.png"
) -> None:
    """Plot monthly returns as a heatmap."""
    equity_curve = equity_curve.copy()
    equity_curve['returns'] = equity_curve['equity'].pct_change()
    monthly_returns = equity_curve['returns'].resample('ME').apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    
    monthly_returns_df = pd.DataFrame(monthly_returns)
    monthly_returns_df['Year'] = monthly_returns_df.index.year
    monthly_returns_df['Month'] = monthly_returns_df.index.month
    
    pivot = monthly_returns_df.pivot(index='Year', columns='Month', values='returns')
    pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
                cbar_kws={'label': 'Return (%)'}, linewidths=0.5, ax=ax)
    
    ax.set_title(title, fontsize=16, fontweight='bold')
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Year', fontsize=12)
    plt.tight_layout()
    
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Monthly returns heatmap saved to {output_path}")


def plot_momentum_over_time(
    output_dir: Path,
    prices: pd.DataFrame,
    momentum_type: str,
    momentum_period: int,
    title: str = "Momentum Over Time",
    filename: str = "momentum_over_time.png"
) -> None:
    """Plot momentum for all stocks over time."""
    from src.indicators import calculate_momentum
    
    momentum = calculate_momentum(prices, method=momentum_type, period=momentum_period)
    fig, ax = plt.subplots(figsize=(16, 8))
    
    for column in momentum.columns:
        ax.plot(momentum.index, momentum[column], linewidth=1.5, 
               label=column, alpha=0.7)
    
    if momentum_type == "ROC":
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3, linewidth=1)
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel(f'{momentum_type} {momentum_period}d', fontsize=12)
    ax.legend(loc='upper left', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Momentum over time plot saved to {output_path}")


def plot_equity_curve_with_regime_background(
    output_dir: Path,
    equity_curve: pd.DataFrame,
    regime_history: pd.DataFrame,
    title: str = "Equity Curve with Market Regime",
    filename: str = "equity_curve_regime.png"
) -> None:
    """
    Plot equity curve colored by asset with background shading for bull/bear regime.
    
    Green background = Bull market (safe to trade risk assets)
    Red background = Bear market (rotated to safe assets)
    
    Args:
        output_dir: Output directory for plot
        equity_curve: Equity curve DataFrame with 'equity' and 'position' columns
        regime_history: DataFrame with 'date' and 'regime' columns (pre-calculated states)
        title: Plot title
        filename: Output filename
    """
    # Convert regime history to dictionary for fast lookup
    regime_history['date'] = pd.to_datetime(regime_history['date'])
    regime_dict = dict(zip(regime_history['date'], regime_history['regime']))
    
    # Map each equity curve date to its regime (forward fill from rebalance dates)
    states = {}
    current_regime = "BULL"  # Default to bull
    
    for date in equity_curve.index:
        # If this date has a regime change, update
        if date in regime_dict:
            current_regime = regime_dict[date]
        # Otherwise use last known regime (forward fill)
        states[date] = current_regime
    
    # Create figure
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Plot background shading for regime
    prev_state = None
    segment_start_idx = 0
    
    for i, (date, state) in enumerate(states.items()):
        is_last = (i == len(states) - 1)
        state_changed = (state != prev_state)
        
        if (state_changed or is_last) and i > 0:
            # Plot background segment
            start_date = equity_curve.index[segment_start_idx]
            end_date = date
            
            if prev_state == "BULL":
                ax.axvspan(start_date, end_date, alpha=0.15, color='green', zorder=0)
            else:  # BEAR
                ax.axvspan(start_date, end_date, alpha=0.15, color='red', zorder=0)
            
            if state_changed:
                segment_start_idx = i
                prev_state = state
        
        if i == 0:
            prev_state = state
    
    # Plot equity curve colored by position on top of background
    equity = equity_curve['equity']
    _plot_position_segments(ax, equity, equity_curve)
    
    # Add initial capital reference line
    ax.axhline(y=equity.iloc[0], color='gray', linestyle='--', 
              alpha=0.4, linewidth=1.5, label='Initial Capital')
    
    # Add regime indicators to legend
    from matplotlib.patches import Patch
    regime_handles = [
        Patch(facecolor='green', alpha=0.15, label='Bull Market'),
        Patch(facecolor='red', alpha=0.15, label='Bear Market')
    ]
    
    # Get existing legend and combine with regime legend
    handles, labels = ax.get_legend_handles_labels()
    handles.extend(regime_handles)
    labels.extend(['Bull Market', 'Bear Market'])
    ax.legend(handles, labels, loc='upper left', fontsize=9, ncol=2)
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Equity ($)', fontsize=12)
    ax.grid(True, alpha=0.3, zorder=1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.tight_layout()
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Equity curve with regime background saved to {output_path}")


def plot_filter_timeline(
    output_dir: Path,
    filter_history: pd.DataFrame,
    equity_curve: pd.DataFrame,
    title: str = "Polymorphic Filter Timeline",
    filename: str = "filter_timeline.png"
) -> None:
    """Plot timeline showing which filter was active over time."""
    if filter_history is None or filter_history.empty:
        print("No filter history to plot (not using polymorphic momentum)")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), 
                                   gridspec_kw={'height_ratios': [3, 1]})
    
    ax1.plot(equity_curve.index, equity_curve['equity'], 
            linewidth=2, color='#2E86AB', label='Equity')
    
    filter_changes = filter_history[filter_history['is_reeval'] == True]
    for _, row in filter_changes.iterrows():
        date = pd.to_datetime(row['date'])
        if date in equity_curve.index:
            ax1.axvline(x=date, color='red', linestyle='--', alpha=0.5, linewidth=1)
    
    ax1.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax1.set_ylabel('Equity ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left', fontsize=10)
    
    filter_history_copy = filter_history.copy()
    filter_history_copy['filter_name'] = (
        filter_history_copy['filter_type'] + '(' + 
        filter_history_copy['filter_period'].astype(str) + ')'
    )
    
    unique_filters = filter_history_copy['filter_name'].unique()
    filter_to_num = {f: i for i, f in enumerate(unique_filters)}
    filter_history_copy['filter_num'] = filter_history_copy['filter_name'].map(filter_to_num)
    
    dates = pd.to_datetime(filter_history_copy['date'])
    ax2.step(dates, filter_history_copy['filter_num'], 
            where='post', linewidth=2, color='#A23B72')
    
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
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Filter timeline plot saved to {output_path}")


def plot_stormguard_signals(
    output_dir: Path,
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
    from src.stormguard import StormGuardCalculator
    
    calculator = StormGuardCalculator(
        volatility_threshold=config.get('stormguard_volatility_threshold', 40.0),
        false_alarm_days=config.get('stormguard_false_alarm_days', 10),
        early_return_threshold=config.get('stormguard_early_return_threshold', 0.75)
    )
    
    metrics = calculator.calculate_all_metrics(
        spy_prices, spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices
    )
    fig, axes = plt.subplots(6, 1, figsize=(16, 20), 
                            gridspec_kw={'height_ratios': [1, 1, 1, 1, 1, 1]})
    
    price_trend = metrics['price_trend']
    axes[0].plot(price_trend.index, price_trend, linewidth=2, 
                color='#2E86AB', label='Price-Trend')
    axes[0].axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    axes[0].fill_between(price_trend.index, 0, price_trend,
                        where=(price_trend > 0), alpha=0.2, color='green', label='Bullish')
    axes[0].fill_between(price_trend.index, 0, price_trend,
                        where=(price_trend <= 0), alpha=0.2, color='red', label='Bearish')
    axes[0].set_title('Metric 1: Price-Trend = 21 × DEMA_50(SPY Returns) + 0.5%', fontweight='bold')
    axes[0].set_ylabel('Price-Trend', fontsize=10)
    axes[0].legend(loc='upper left', fontsize=9)
    axes[0].grid(True, alpha=0.3)
    
    money_flow = metrics['money_flow']
    axes[1].plot(money_flow.index, money_flow, linewidth=2, 
                color='#2E86AB', label='Money Flow')
    axes[1].axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    axes[1].fill_between(money_flow.index, 0, money_flow.max(),
                        where=(money_flow > 0), alpha=0.1, color='green', label='Bullish')
    axes[1].fill_between(money_flow.index, money_flow.min(), 0,
                        where=(money_flow <= 0), alpha=0.1, color='red', label='Bearish')
    axes[1].set_title('Metric 2: Money Flow = OBV - SMA_50(OBV)', fontweight='bold')
    axes[1].set_ylabel('Money Flow', fontsize=10)
    axes[1].legend(loc='upper left', fontsize=9)
    axes[1].grid(True, alpha=0.3)
    
    sentiment = metrics['sentiment']
    axes[2].plot(sentiment.index, sentiment, linewidth=2, 
                color='#A23B72', label='Sentiment')
    axes[2].axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    axes[2].fill_between(sentiment.index, 0, sentiment.max(),
                        where=(sentiment > 0), alpha=0.1, color='green', label='Bullish (Low Fear)')
    axes[2].fill_between(sentiment.index, sentiment.min(), 0,
                        where=(sentiment <= 0), alpha=0.1, color='red', label='Bearish (High Fear)')
    axes[2].set_title('Metric 3: Sentiment = SMA_50(VIX) - VIX', fontweight='bold')
    axes[2].set_ylabel('Sentiment', fontsize=10)
    axes[2].legend(loc='upper left', fontsize=9)
    axes[2].grid(True, alpha=0.3)
    
    volatility = metrics['market_volatility']
    threshold = config.get('stormguard_volatility_threshold', 40.0)
    axes[3].plot(volatility.index, volatility, linewidth=2, 
                color='#D62728', label='Market Volatility')
    axes[3].axhline(y=threshold, color='red', linestyle='--', 
                   linewidth=2, label=f'Threshold ({threshold})')
    axes[3].fill_between(volatility.index, 0, threshold,
                        where=(volatility < threshold), alpha=0.1, color='green', label='Normal')
    axes[3].fill_between(volatility.index, threshold, volatility.max(),
                        where=(volatility >= threshold), alpha=0.1, color='red', label='Panic')
    axes[3].set_title('Metric 4: Market Volatility = (2/3) × EMA_4(VIX)', fontweight='bold')
    axes[3].set_ylabel('Volatility', fontsize=10)
    axes[3].legend(loc='upper left', fontsize=9)
    axes[3].grid(True, alpha=0.3)
    
    # Panel 5: Credit Risk Appetite (LEADING INDICATOR)
    credit_risk = metrics['credit_risk'].astype(int)  # Convert boolean to 0/1 for plotting
    axes[4].fill_between(credit_risk.index, 0, 1,
                        where=(credit_risk == 1), alpha=0.2, color='green', 
                        step='post', label='Bullish (Seeking Risk)')
    axes[4].fill_between(credit_risk.index, 0, 1,
                        where=(credit_risk == 0), alpha=0.2, color='red', 
                        step='post', label='Bearish (Risk-Off)')
    axes[4].step(credit_risk.index, credit_risk, where='post', 
                linewidth=2, color='#9C27B0', label='Credit Risk Signal')
    axes[4].set_title('Metric 5: Credit Risk Appetite = HYG:IEF Ratio Momentum (LEADING)', 
                     fontweight='bold')
    axes[4].set_ylabel('Signal (0=Bear, 1=Bull)', fontsize=10)
    axes[4].set_yticks([0, 1])
    axes[4].set_yticklabels(['Risk-Off', 'Seeking Risk'])
    axes[4].legend(loc='upper left', fontsize=9)
    axes[4].grid(True, alpha=0.3, axis='x')
    
    # Panel 6: Internal Breadth (LEADING INDICATOR)
    breadth = metrics['internal_breadth'].astype(int)  # Convert boolean to 0/1 for plotting
    axes[5].fill_between(breadth.index, 0, 1,
                        where=(breadth == 1), alpha=0.2, color='green', 
                        step='post', label='Bullish (Troops Strong)')
    axes[5].fill_between(breadth.index, 0, 1,
                        where=(breadth == 0), alpha=0.2, color='red', 
                        step='post', label='Bearish (Troops Weak)')
    axes[5].step(breadth.index, breadth, where='post', 
                linewidth=2, color='#FF5722', label='Breadth Signal')
    axes[5].set_title('Metric 6: Internal Breadth = RSP vs SPY Momentum (LEADING)', 
                     fontweight='bold')
    axes[5].set_ylabel('Signal (0=Weak, 1=Strong)', fontsize=10)
    axes[5].set_xlabel('Date', fontsize=12)
    axes[5].set_yticks([0, 1])
    axes[5].set_yticklabels(['Weak Breadth', 'Strong Breadth'])
    axes[5].legend(loc='upper left', fontsize=9)
    axes[5].grid(True, alpha=0.3, axis='x')
    
    plt.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"STORMGUARD signals plot saved to {output_path}")


def plot_multi_bucket_equity_curve(
    output_dir: Path,
    equity_curve: pd.DataFrame,
    buckets: list,
    regime_history: Optional[pd.DataFrame] = None,
    title: str = "Multi-Bucket Portfolio Equity Curve",
    filename: str = "equity_curve.png"
) -> None:
    """
    Plot equity curve for multi-bucket portfolio with color-blended asset combinations.
    
    Shows line segments colored by the combination of holdings across all buckets.
    Each unique combination gets a blended color based on constituent asset colors.
    
    Args:
        output_dir: Output directory
        equity_curve: Equity curve with bucket position columns
        buckets: List of (bucket_name, allocation) tuples
        regime_history: Optional regime history for background shading
        title: Plot title
        filename: Output filename
    """
    from reporting.colors import get_position_color, blend_colors
    
    fig, ax = plt.subplots(figsize=(16, 8))
    
    # Plot bull/bear background if regime history provided
    if regime_history is not None and not regime_history.empty:
        regime_history['date'] = pd.to_datetime(regime_history['date'])
        regime_dict = dict(zip(regime_history['date'], regime_history['regime']))
        
        states = {}
        current_regime = "BULL"
        for date in equity_curve.index:
            if date in regime_dict:
                current_regime = regime_dict[date]
            states[date] = current_regime
        
        prev_state = None
        segment_start_idx = 0
        
        for i, (date, state) in enumerate(states.items()):
            if (state != prev_state or i == len(states) - 1) and i > 0:
                start_date = equity_curve.index[segment_start_idx]
                end_date = date
                
                if prev_state == "BULL":
                    ax.axvspan(start_date, end_date, alpha=0.15, color='green', zorder=0)
                else:
                    ax.axvspan(start_date, end_date, alpha=0.15, color='red', zorder=0)
                
                if state != prev_state:
                    segment_start_idx = i
                    prev_state = state
            
            if i == 0:
                prev_state = state
    
    # Plot equity colored by asset combination
    equity = equity_curve['equity']
    prev_combination = None
    segment_start = 0
    legend_combinations = set()
    
    for i in range(len(equity_curve)):
        # Get current combination of holdings
        holdings = []
        allocations = []
        
        for bucket_name, bucket_alloc in buckets:
            position = equity_curve.iloc[i][f'{bucket_name}_position']
            if not pd.isna(position):
                holdings.append(position)
                allocations.append(bucket_alloc)
        
        current_combination = tuple(holdings) if holdings else ('CASH',)
        is_last = (i == len(equity_curve) - 1)
        
        if current_combination != prev_combination or is_last:
            if segment_start < i or is_last:
                # Get blended color for combination
                if prev_combination and prev_combination != ('CASH',):
                    colors = [get_position_color(asset) for asset in prev_combination]
                    prev_allocations = allocations if current_combination == prev_combination else [1.0/len(prev_combination)] * len(prev_combination)
                    if len(colors) == len(prev_allocations):
                        blended_color = blend_colors(colors, prev_allocations)
                    else:
                        blended_color = colors[0] if colors else '#808080'
                else:
                    blended_color = '#FF0000'  # CASH
                
                # Create label
                if prev_combination:
                    if prev_combination == ('CASH',):
                        label_text = 'CASH'
                    else:
                        # Format: "60% XLE + 40% EEM"
                        parts = []
                        for j, asset in enumerate(prev_combination):
                            alloc = prev_allocations[j] if j < len(prev_allocations) else 0
                            parts.append(f"{alloc*100:.0f}% {asset}")
                        label_text = " + ".join(parts)
                else:
                    label_text = 'CASH'
                
                use_label = label_text not in legend_combinations
                if use_label:
                    legend_combinations.add(label_text)
                
                ax.plot(
                    equity.index[segment_start:i+1],
                    equity.values[segment_start:i+1],
                    linewidth=2.5,
                    color=blended_color,
                    label=label_text if use_label else "",
                    zorder=2
                )
            
            if current_combination != prev_combination:
                segment_start = i
                prev_combination = current_combination
    
    ax.axhline(y=equity.iloc[0], color='gray', linestyle='--', 
              alpha=0.4, linewidth=1.5, label='Initial Capital', zorder=1)
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Equity ($)', fontsize=12)
    ax.grid(True, alpha=0.3, zorder=1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax.legend(loc='upper left', title='Holdings', fontsize=9, ncol=2)
    
    plt.tight_layout()
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Multi-bucket equity curve saved to {output_path}")


def plot_strategy_vs_benchmark(
    output_dir: Path,
    strategy_equity: pd.DataFrame,
    benchmark_equity: pd.DataFrame,
    strategy_name: str = "Strategy",
    benchmark_name: str = "SPY Buy & Hold",
    filename: str = "strategy_vs_benchmark.png"
) -> None:
    """Plot strategy performance vs benchmark."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    strategy_norm = strategy_equity['equity'] / strategy_equity['equity'].iloc[0] * 100
    benchmark_norm = benchmark_equity['equity'] / benchmark_equity['equity'].iloc[0] * 100
    
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
    
    outperformance = strategy_norm - benchmark_norm
    ax2.fill_between(outperformance.index, outperformance.values, 0, 
                    alpha=0.3, color='green', where=(outperformance >= 0))
    ax2.fill_between(outperformance.index, outperformance.values, 0, 
                    alpha=0.3, color='red', where=(outperformance < 0))
    ax2.plot(outperformance.index, outperformance.values, linewidth=1.5, color='black')
    ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
    
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
    
    ax2.set_title('Outperformance vs Benchmark', fontsize=16, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Relative Performance', fontsize=12)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_path = output_dir / filename
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Comparison plot saved to {output_path}")

