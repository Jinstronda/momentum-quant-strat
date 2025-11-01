================================================================================
BACKTEST RUN: 20251101_202032_US_Large_Cap_POLYMORPHIC63d_W_Top1
================================================================================

CONFIGURATION
--------------------------------------------------------------------------------
Universe:        US_Large_Cap
Period:          2005-01-01 to 2024-12-31
Strategy:        Top-1 Momentum (POLYMORPHIC 63 days)
Rebalance:       Weekly (Monday)
Market:          NYSE
Filter:          Safety Switch (SPY 50d/200d SMA)
                 Bull: SPY.SMA(50) > SMA(200) -> Trade risk assets
                 Bear: SPY.SMA(50) < SMA(200) -> Rotate to safe assets
                 Safe Assets: SHY, VGSH, AGG...

Initial Capital: $100,000.00
Costs:           0.10% commission + 0.050% slippage

FILES IN THIS DIRECTORY
--------------------------------------------------------------------------------
US_Large_Cap_metrics.csv              - Strategy performance metrics
US_Large_Cap_benchmark_metrics.csv    - SPY buy & hold metrics
US_Large_Cap_comparison.csv           - Side-by-side comparison
US_Large_Cap_trades.csv               - Complete trade log
US_Large_Cap_equity.csv               - Daily equity curve
US_Large_Cap_benchmark_equity.csv     - SPY equity curve
US_Large_Cap_equity_curve.png         - Strategy equity chart (color-coded)
US_Large_Cap_vs_benchmark.png         - Strategy vs SPY comparison
US_Large_Cap_drawdown.png             - Drawdown analysis
US_Large_Cap_monthly_returns.png      - Monthly returns heatmap
US_Large_Cap_returns_dist.png         - Returns distribution
US_Large_Cap_momentum_over_time.png   - All stocks' momentum (POLYMORPHIC) over time

QUICK START
--------------------------------------------------------------------------------
1. Check the comparison plot: *_vs_benchmark.png
2. Review metrics: *_comparison.csv
3. Examine trades: *_trades.csv
4. Analyze drawdowns: *_drawdown.png

RESULTS
--------------------------------------------------------------------------------
Total Return (%)                        446.02
CAGR (%)                                  8.87
Sharpe Ratio                              0.63
Sortino Ratio                             0.64
Calmar Ratio                              0.24
Max Drawdown (%)                        -36.66

