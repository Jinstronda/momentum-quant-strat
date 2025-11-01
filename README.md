# Momentum Strategy Backtest
conda deactivate
uv run python main.py

## Overview
Pure momentum strategy that selects the top-1 ETF by 1-month ROC, rebalanced weekly on Mondays.

## Strategy Logic
- **Universe**: US Large Cap ETFs (DIA, SPY, QQQ, VTV, VUG, XLB, XLE, XLF, XLI, XLK, XLY) or Developed Countries
- **Momentum Indicator**: ROC (Rate of Change) or DEMA (Double EMA) - configurable
- **Period**: 21, 63, 126, or 252 days (1M, 3M, 6M, 12M)
- **Selection**: Top-1 ETF by momentum
- **Rebalance**: Weekly (Monday) or Monthly (first trading day) - configurable
- **EMA Filter**: Optional dual 20/50 EMA system with 10-day derivative
- **Execution**: No lookahead bias, holiday-aware scheduling
- **Costs**: 0.1% commission + 0.05% slippage per trade

## Configuration
Edit `src/config.py` to adjust:
- **MOMENTUM_TYPE**: "ROC", "Double_EMA", or "DEMA"
- **MOMENTUM_PERIOD**: 21, 63, 126, or 252 days (1M, 3M, 6M, 12M)
- **REBALANCE_FREQUENCY**: "weekly" or "monthly"
- **USE_MA_FILTER**: Enable/disable dual EMA trend filter
- **EMA_SHORT_PERIOD / EMA_LONG_PERIOD**: EMA periods (default: 20/50)
- **EMA_DERIVATIVE_LOOKBACK**: Slope calculation period (default: 10 days)
- **START_DATE / END_DATE**: Backtest period
- **ACTIVE_UNIVERSE**: Choose "US_Large_Cap" or "Developed_Countries"

## Performance (2020-2024)
- **Total Return**: 96.87%
- **CAGR**: 14.55%
- **Sharpe Ratio**: 0.51
- **Max Drawdown**: -31.38%
- **Win Rate**: 53.34%

## Setup

### Using uv (recommended)
```bash
uv venv
uv pip install -r requirements.txt
```

### Using pip
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Quick Start
```bash
# Deactivate conda if active
conda deactivate

# Run backtest
uv run python main.py
```

### Configure Strategy
Edit `src/config.py` before running:

**Momentum Indicator:**
```python
# Choose indicator type
MOMENTUM_TYPE = "ROC"         # Rate of Change (most responsive)
# MOMENTUM_TYPE = "Double_EMA"  # EMA(EMA) - smoothest, slowest
# MOMENTUM_TYPE = "DEMA"        # Technical DEMA - balanced

# Choose period
MOMENTUM_PERIOD = 63   # 3-month (63 trading days)
# MOMENTUM_PERIOD = 21   # 1-month
# MOMENTUM_PERIOD = 126  # 6-month (Jegadeesh-Titman)
# MOMENTUM_PERIOD = 252  # 12-month
```

**Rebalancing Frequency:**
```python
# Weekly rebalancing
REBALANCE_FREQUENCY = "weekly"
REBALANCE_WEEKDAY = 0  # 0=Monday, 1=Tuesday, etc.

# OR Monthly rebalancing
# REBALANCE_FREQUENCY = "monthly"  # First trading day of month
```

**EMA Trend Filter (Optional):**
```python
USE_MA_FILTER = True   # Enable dual EMA filter
EMA_SHORT_PERIOD = 20  # Short EMA
EMA_LONG_PERIOD = 50   # Long EMA
EMA_DERIVATIVE_LOOKBACK = 10  # Slope calculation period

# Set to False to disable filter
# USE_MA_FILTER = False
```

**Universe Selection:**
```python
ACTIVE_UNIVERSE = "US_Large_Cap"
# ACTIVE_UNIVERSE = "Developed_Countries"
```

## Testing
```bash
uv run pytest tests/ -v
# or
pytest tests/ -v
```

## Output
Each backtest run creates a timestamped folder in `output/` with format:
```
YYYYMMDD_HHMMSS_Universe_MomentumType_Period_Frequency_TopN/
Example: 20251101_185705_US_Large_Cap_ROC63d_W_Top1/
```

**Files generated:**
- `*_metrics.csv` - Strategy performance metrics
- `*_benchmark_metrics.csv` - SPY buy & hold metrics
- `*_comparison.csv` - Side-by-side comparison
- `*_trades.csv` - Complete trade log
- `*_equity_curve.png` - Color-coded equity chart
- `*_vs_benchmark.png` - Strategy vs SPY
- `*_drawdown.png` - Drawdown analysis
- `*_monthly_returns.png` - Monthly returns heatmap
- `*_returns_dist.png` - Returns distribution
- `*_momentum_over_time.png` - All stocks' momentum trends
- `README.txt` - Run summary
- `run_config.txt` - Configuration used

## Momentum Indicators Explained

### ROC (Rate of Change)
**Formula:** `(Price_today - Price_N_days_ago) / Price_N_days_ago × 100`
- Direct percentage change measurement
- Most responsive to price movements
- Higher turnover, more trades
- Best for: Capturing quick momentum shifts

### Double EMA (Smoothed)
**Formula:** `EMA(EMA(price))`
- Maximum smoothing, kills short-term noise
- Very slow, far from price
- Ignores whipsaws, only major trends
- Lowest turnover
- Best for: Multi-month/year trends, reducing costs

### DEMA (Technical)
**Formula:** `2 × EMA - EMA(EMA)`
- Reduces lag while maintaining smoothness
- Faster than EMA, smoother than ROC
- Moderate turnover
- Best for: Balanced approach, trending markets

**When to use:**
- **ROC**: Aggressive, high turnover, responsive
- **Double_EMA**: Conservative, low turnover, smooth
- **DEMA**: Balanced, moderate turnover, reduced lag

## Rebalancing Frequencies

### Weekly
- Rebalances every Monday (or specified weekday)
- More responsive to momentum changes
- Higher transaction costs
- ~52 rebalance dates per year

### Monthly
- Rebalances on first trading day of each month
- Lower transaction costs
- Smoother, less trading
- ~12 rebalance dates per year

## Project Structure
```
.
├── src/
│   ├── config.py          # Configuration (EDIT THIS)
│   ├── data.py            # Data loading with caching
│   ├── indicators.py      # ROC, DEMA, EMA calculations
│   ├── schedule.py        # Weekly/monthly scheduling
│   ├── strategy.py        # Momentum strategy logic
│   ├── backtest.py        # Backtest engine
│   ├── reporting.py       # Visualization and reports
│   └── metrics.py         # Performance calculations
├── tests/                 # Unit tests
├── data/                  # Cached price data (parquet)
├── output/                # Backtest results
├── experiments/           # Experiment tracking
├── main.py                # Main entry point
└── requirements.txt       # Dependencies
```

