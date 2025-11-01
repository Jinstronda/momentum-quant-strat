================================================================================
BACKTEST RUN: 20251101_193021_US_Large_Cap_Double_EMA63d_M_Top1
================================================================================

CONFIGURATION
--------------------------------------------------------------------------------
Universe:        US_Large_Cap
Period:          2005-01-01 to 2024-12-31
Strategy:        Top-1 Momentum (Double_EMA 63 days)
Rebalance:       Monthly
Market:          NYSE
Filter:          Safety Switch (SPY 50d/200d SMA)
                 Bull: SPY.SMA(50) > SMA(200) -> Trade
                 Bear: SPY.SMA(50) < SMA(200) -> CASH

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
US_Large_Cap_momentum_over_time.png   - All stocks' momentum (Double_EMA) over time

QUICK START
--------------------------------------------------------------------------------
1. Check the comparison plot: *_vs_benchmark.png
2. Review metrics: *_comparison.csv
3. Examine trades: *_trades.csv
4. Analyze drawdowns: *_drawdown.png

RESULTS
--------------------------------------------------------------------------------
Total Return (%)                        430.63
CAGR (%)                                  8.72
Sharpe Ratio                              0.64
Sortino Ratio                             0.66
Calmar Ratio                              0.26
Max Drawdown (%)                        -33.68

