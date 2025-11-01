================================================================================
BACKTEST RUN: 20251101_224439_US_Sector_Cyclicals_POLYMORPHIC63d_M_Top1
================================================================================

CONFIGURATION
--------------------------------------------------------------------------------
Universe:        US_Sector_Cyclicals
Period:          2010-01-01 to 2024-12-31
Strategy:        Top-1 Momentum (POLYMORPHIC 63 days)
Rebalance:       Monthly
Market:          NYSE
Filter:          NONE

Initial Capital: $100,000.00
Costs:           0.10% commission + 0.050% slippage

FILES IN THIS DIRECTORY
--------------------------------------------------------------------------------
US_Sector_Cyclicals_metrics.csv              - Strategy performance metrics
US_Sector_Cyclicals_benchmark_metrics.csv    - SPY buy & hold metrics
US_Sector_Cyclicals_comparison.csv           - Side-by-side comparison
US_Sector_Cyclicals_trades.csv               - Complete trade log
US_Sector_Cyclicals_equity.csv               - Daily equity curve
US_Sector_Cyclicals_benchmark_equity.csv     - SPY equity curve
US_Sector_Cyclicals_equity_curve.png         - Strategy equity chart (color-coded)
US_Sector_Cyclicals_vs_benchmark.png         - Strategy vs SPY comparison
US_Sector_Cyclicals_drawdown.png             - Drawdown analysis
US_Sector_Cyclicals_monthly_returns.png      - Monthly returns heatmap
US_Sector_Cyclicals_returns_dist.png         - Returns distribution
US_Sector_Cyclicals_momentum_over_time.png   - All stocks' momentum (POLYMORPHIC) over time

QUICK START
--------------------------------------------------------------------------------
1. Check the comparison plot: *_vs_benchmark.png
2. Review metrics: *_comparison.csv
3. Examine trades: *_trades.csv
4. Analyze drawdowns: *_drawdown.png

RESULTS
--------------------------------------------------------------------------------
Total Return (%)                        200.01
CAGR (%)                                 21.99
Sharpe Ratio                              0.81
Sortino Ratio                             1.10
Calmar Ratio                              0.71
Max Drawdown (%)                        -30.77

