================================================================================
BACKTEST RUN: 20251101_200838_Developed_Countries_POLYMORPHIC63d_M_Top1
================================================================================

CONFIGURATION
--------------------------------------------------------------------------------
Universe:        Developed_Countries
Period:          2005-01-01 to 2024-12-31
Strategy:        Top-1 Momentum (POLYMORPHIC 63 days)
Rebalance:       Monthly
Market:          NYSE
Filter:          Safety Switch (SPY 50d/200d SMA)
                 Bull: SPY.SMA(50) > SMA(200) -> Trade risk assets
                 Bear: SPY.SMA(50) < SMA(200) -> Rotate to safe assets
                 Safe Assets: SHY, VGSH, AGG...

Initial Capital: $100,000.00
Costs:           0.10% commission + 0.050% slippage

FILES IN THIS DIRECTORY
--------------------------------------------------------------------------------
Developed_Countries_metrics.csv              - Strategy performance metrics
Developed_Countries_benchmark_metrics.csv    - SPY buy & hold metrics
Developed_Countries_comparison.csv           - Side-by-side comparison
Developed_Countries_trades.csv               - Complete trade log
Developed_Countries_equity.csv               - Daily equity curve
Developed_Countries_benchmark_equity.csv     - SPY equity curve
Developed_Countries_equity_curve.png         - Strategy equity chart (color-coded)
Developed_Countries_vs_benchmark.png         - Strategy vs SPY comparison
Developed_Countries_drawdown.png             - Drawdown analysis
Developed_Countries_monthly_returns.png      - Monthly returns heatmap
Developed_Countries_returns_dist.png         - Returns distribution
Developed_Countries_momentum_over_time.png   - All stocks' momentum (POLYMORPHIC) over time

QUICK START
--------------------------------------------------------------------------------
1. Check the comparison plot: *_vs_benchmark.png
2. Review metrics: *_comparison.csv
3. Examine trades: *_trades.csv
4. Analyze drawdowns: *_drawdown.png

RESULTS
--------------------------------------------------------------------------------
Total Return (%)                        279.52
CAGR (%)                                  6.91
Sharpe Ratio                              0.41
Sortino Ratio                             0.53
Calmar Ratio                              0.15
Max Drawdown (%)                        -47.25

