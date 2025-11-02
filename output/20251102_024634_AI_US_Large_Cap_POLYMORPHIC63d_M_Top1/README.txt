================================================================================
BACKTEST RUN: 20251102_024634_AI_US_Large_Cap_POLYMORPHIC63d_M_Top1
================================================================================

CONFIGURATION
--------------------------------------------------------------------------------
Universe:        AI_US_Large_Cap
Period:          1995-01-03 to 2024-12-31
Strategy:        Top-1 Momentum (POLYMORPHIC 63 days)
Rebalance:       Monthly
Market:          NYSE
Filter:          STORMGUARD-VELOCITY (5-Component + Velocity Detection)
                 States: BULL -> WATCH -> BEAR (3-state machine)
                 Velocity: Z-score -2.0 | ROC: 10d
                 Hysteresis: Min dwell 10d | WATCH timeout 20d
                 Bear Mode: Rotate to safe assets (TLT, IEF, IEI...)

Initial Capital: $100,000.00
Costs:           0.10% commission + 0.050% slippage

FILES IN THIS DIRECTORY
--------------------------------------------------------------------------------
AI_US_Large_Cap_vs_benchmark.png         - Strategy vs SPY comparison (MOST IMPORTANT)
AI_US_Large_Cap_metrics.csv              - Strategy performance metrics
AI_US_Large_Cap_benchmark_metrics.csv    - SPY buy & hold metrics
AI_US_Large_Cap_comparison.csv           - Side-by-side comparison
AI_US_Large_Cap_trades.csv               - Complete trade log
AI_US_Large_Cap_equity.csv               - Daily equity curve
AI_US_Large_Cap_benchmark_equity.csv     - SPY equity curve
AI_US_Large_Cap_equity_curve*.png        - Strategy equity charts (color-coded)
AI_US_Large_Cap_monthly_returns.png      - Monthly returns heatmap
AI_US_Large_Cap_returns_dist.png         - Returns distribution
AI_US_Large_Cap_momentum_over_time.png   - All stocks' momentum (POLYMORPHIC) over time

QUICK START
--------------------------------------------------------------------------------
1. Check the comparison plot: *_vs_benchmark.png (MOST IMPORTANT)
2. Review metrics: *_comparison.csv
3. Examine trades: *_trades.csv
4. View equity curve: *_equity_curve*.png

RESULTS
--------------------------------------------------------------------------------
Total Return (%)                        471.74
CAGR (%)                                  9.00
Sharpe Ratio                              0.49
Sortino Ratio                             0.57
Calmar Ratio                              0.32
Max Drawdown (%)                        -28.43

