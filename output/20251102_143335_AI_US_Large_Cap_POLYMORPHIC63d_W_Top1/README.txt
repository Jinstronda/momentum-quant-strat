================================================================================
BACKTEST RUN: 20251102_143335_AI_US_Large_Cap_POLYMORPHIC63d_W_Top1
================================================================================

CONFIGURATION
--------------------------------------------------------------------------------
Universe:        AI_US_Large_Cap
Period:          1995-01-03 to 2024-12-31
Strategy:        Top-1 Momentum (POLYMORPHIC 63 days)
Rebalance:       Weekly (Weekday 4)
Market:          NYSE
Filter:          STORMGUARD (5-Component)
                 Safe Assets: TLT, IEF, IEI...
Enhancements:    Price Action (EMA20_LOW)
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
AI_US_Large_Cap_monthly_returns.png      - Monthly returns heatmap
AI_US_Large_Cap_returns_dist.png         - Returns distribution

QUICK START
--------------------------------------------------------------------------------
1. Check the comparison plot: *_vs_benchmark.png (MOST IMPORTANT)
2. Review metrics: *_comparison.csv
3. Examine trades: *_trades.csv
4. View equity curve: *_equity_curve*.png

RESULTS
--------------------------------------------------------------------------------
Total Return (%)                        310.17
CAGR (%)                                  7.23
Sharpe Ratio                              0.45
Sortino Ratio                             0.49
Calmar Ratio                              0.24
Max Drawdown (%)                        -29.57

