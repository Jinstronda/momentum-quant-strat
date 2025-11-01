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
- **MOMENTUM_TYPE**: "ROC", "EMA", "Double_EMA", "DEMA", "TEMA", or "POLYMORPHIC"
- **MOMENTUM_PERIOD**: 21, 63, 126, or 252 days (1M, 3M, 6M, 12M) - ignored if POLYMORPHIC
- **REBALANCE_FREQUENCY**: "weekly" or "monthly"
- **FILTER_TYPE**: "DUAL_EMA", "SAFETY_SWITCH", or "NONE"
- **SAFETY_SMA_SHORT / SAFETY_SMA_LONG**: SPY SMA periods (default: 50/200)
- **EMA_SHORT_PERIOD / EMA_LONG_PERIOD**: EMA periods (default: 20/50)
- **EMA_DERIVATIVE_LOOKBACK**: Slope calculation period (default: 10 days)
- **POLYMORPHIC_METRIC**: "Sharpe" or "Sortino" for filter evaluation (POLYMORPHIC only)
- **POLYMORPHIC_INITIAL_YEARS**: Years for initial bake-off (default: 5)
- **POLYMORPHIC_REEVAL_YEARS**: Years for quarterly re-evaluation (default: 2)
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
# MOMENTUM_TYPE = "EMA"         # Single EMA (smooth trend)
# MOMENTUM_TYPE = "Double_EMA"  # EMA(EMA) - smoothest, slowest
# MOMENTUM_TYPE = "DEMA"        # Technical DEMA - balanced
# MOMENTUM_TYPE = "TEMA"        # EMA(EMA(EMA)) - triple smoothing
# MOMENTUM_TYPE = "POLYMORPHIC" # Auto-select best filter quarterly (advanced)

# Choose period (ignored if POLYMORPHIC)
MOMENTUM_PERIOD = 63   # 3-month (63 trading days)
# MOMENTUM_PERIOD = 21   # 1-month
# MOMENTUM_PERIOD = 126  # 6-month (Jegadeesh-Titman)
# MOMENTUM_PERIOD = 252  # 12-month
```

**Polymorphic Momentum (Advanced):**
```python
# Only used when MOMENTUM_TYPE = "POLYMORPHIC"
# Runs quarterly "bake-off" to automatically select best-performing filter
# from 20 options: 4 EMA, 8 Double_EMA, 8 TEMA with varying periods

POLYMORPHIC_METRIC = "Sharpe"  # Options: "Sharpe" or "Sortino"
POLYMORPHIC_INITIAL_YEARS = 5  # Years of history for initial selection
POLYMORPHIC_REEVAL_YEARS = 2   # Years for quarterly re-evaluation

# The 20-filter bank:
# - EMA: [12, 25, 45, 63]
# - Double_EMA: [12, 25, 45, 63, 75, 90, 105, 120]
# - TEMA: [12, 25, 45, 63, 75, 90, 105, 120]
```

**Rebalancing Frequency:**
```python
# Weekly rebalancing
REBALANCE_FREQUENCY = "weekly"
REBALANCE_WEEKDAY = 0  # 0=Monday, 1=Tuesday, etc.

# OR Monthly rebalancing
# REBALANCE_FREQUENCY = "monthly"  # First trading day of month
```

**Filter Selection (Choose ONE):**
```python
FILTER_TYPE = "SAFETY_SWITCH"  # Options: "DUAL_EMA", "SAFETY_SWITCH", "STORMGUARD", "NONE"

# SAFETY SWITCH - Market regime filter (SPY SMA)
SAFETY_SMA_SHORT = 50   # SPY short SMA  
SAFETY_SMA_LONG = 200   # SPY long SMA
# Bull: SPY.SMA(50) > SMA(200) -> Trade risk assets
# Bear: SPY.SMA(50) < SMA(200) -> Rotate to safe assets (bonds/gold)

# STORMGUARD - Advanced 3-component market regime filter (SPY only)
STORMGUARD_DEMA_FAST = 50      # Fast DEMA for price trend
STORMGUARD_DEMA_SLOW = 100     # Slow DEMA for price trend
STORMGUARD_OBV_SMA = 50        # OBV smoothing for money flow
STORMGUARD_VIX_SMA = 50        # VIX smoothing for sentiment (adaptive)
# All 3 must be bullish to trade:
#  1. Price Trend: SPY DEMA(50) > DEMA(100)
#  2. Money Flow: SPY OBV > OBV_SMA(50)
#  3. Sentiment: VIX < VIX_SMA(50) (adaptive)
# If ANY bearish -> Rotate to safe assets

# Safe assets for bear market (uses same momentum selection)
SAFE_ASSETS = ["SHY", "VGSH", "AGG", "BND", "IEI", "TIPX", 
               "BLV", "IEF", "TLH", "TLT", "ZROZ", "GLD"]

# DUAL EMA - Per-stock trend filter  
EMA_SHORT_PERIOD = 20  # Short EMA
EMA_LONG_PERIOD = 50   # Long EMA
EMA_DERIVATIVE_LOOKBACK = 10  # Slope period
# Stocks must pass: Price>20d, 20d>50d, 50d slope>0

# NONE - No filter, pure momentum
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
- `*_equity_curve.png` - Color-coded equity chart (by asset held)
- `*_equity_curve_by_filter.png` - Equity colored by momentum filter (POLYMORPHIC only)
- `*_equity_curve_by_asset.png` - Equity colored by asset held (POLYMORPHIC only)
- `*_vs_benchmark.png` - Strategy vs SPY
- `*_drawdown.png` - Drawdown analysis
- `*_monthly_returns.png` - Monthly returns heatmap
- `*_returns_dist.png` - Returns distribution
- `*_momentum_over_time.png` - All stocks' momentum trends
- `*_filter_history.csv` - Polymorphic filter selection log (POLYMORPHIC only)
- `*_filter_timeline.png` - Filter changes over time (POLYMORPHIC only)
- `*_stormguard_signals.png` - 3-component analysis (STORMGUARD only)
- `README.txt` - Run summary
- `run_config.txt` - Configuration used

## Momentum Indicators Explained

### ROC (Rate of Change)
**Formula:** `(Price_today - Price_N_days_ago) / Price_N_days_ago × 100`
- Direct percentage change measurement
- Most responsive to price movements
- Higher turnover, more trades
- Best for: Capturing quick momentum shifts

### EMA (Single Exponential Moving Average)
**Formula:** `EMA(price)`
- Single smoothing layer
- Moderate responsiveness
- Good for trend-following
- Less noise than ROC

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

### TEMA (Triple Smoothing)
**Formula:** `EMA(EMA(EMA(price)))`
- Maximum smoothing with triple filtering
- Extremely slow response
- Captures only long-term trends
- Minimal noise and whipsaw

### POLYMORPHIC (Adaptive Momentum - Advanced)
**System:** Automated quarterly selection from 20-filter bank

**How It Works:**
1. Initial 5-year bake-off to select best filter
2. Uses winner for next quarter
3. Quarterly re-evaluation with 2-year lookback
4. Automatically switches if market regime changes

**The 20-Filter Bank:**
- 4 EMA: [12, 25, 45, 63]
- 8 Double_EMA: [12, 25, 45, 63, 75, 90, 105, 120]
- 8 TEMA: [12, 25, 45, 63, 75, 90, 105, 120]

**Characteristics:**
- Adaptive to changing markets
- Data-driven filter selection
- No manual tuning required
- Requires 5+ years pre-start history

**When to use:**
- **ROC**: Aggressive, high turnover, responsive
- **EMA**: Moderate smoothing, trend-following
- **Double_EMA**: Conservative, low turnover, smooth
- **DEMA**: Balanced, moderate turnover, reduced lag
- **TEMA**: Ultra-conservative, major trends only
- **POLYMORPHIC**: Adaptive, systematic, set-and-forget

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

## Filter Types Explained

### Safety Switch (Market Regime Filter)
**Logic:** Check SPY's SMA(50) vs SMA(200)
- **Bull**: SPY.SMA(50) > SPY.SMA(200) → Trade risk assets normally
- **Bear**: SPY.SMA(50) < SPY.SMA(200) → Rotate to safe assets (bonds/gold)

**Safe Assets (Bear Market):**
When bear market detected, selects best momentum from:
- Treasury bonds (SHY, VGSH, IEI, IEF, TLH, TLT, ZROZ)
- Aggregate bonds (AGG, BND, BLV)
- Inflation-protected (TIPX)
- Gold (GLD)

**Characteristics:**
- Simple, robust bear market protection
- Based on S&P 500 only (whole market proxy)
- Stays invested in safe assets during downturns
- Uses same momentum logic for safe asset selection
- Low turnover (only exits/enters on regime change)
- Best for: Risk-averse, capital preservation with returns

### STORMGUARD (Advanced 3-Component Market Regime Filter)
**Logic:** ALL 3 SPY-based components must be bullish to trade risk assets

**Component 1: Price Trend (DEMA Crossover)**
- Check: SPY DEMA(50) > DEMA(100)
- Purpose: Smoother than SMA, less whipsaw
- Detects: Major price trend direction

**Component 2: Money Flow (On-Balance Volume)**
- Check: SPY OBV > OBV_SMA(50)
- Purpose: Confirms price moves with volume
- Detects: Institutional money flow (accumulation vs distribution)

**Component 3: Sentiment (VIX Adaptive)**
- Check: VIX < VIX_SMA(50)
- Purpose: Adaptive fear gauge (compares to recent average)
- Detects: Fear spikes relative to current regime
- Why adaptive: VIX avg ~12 in 2017, ~28 in 2020-2022

**Bear Market Behavior:**
If ANY component is bearish → Rotate to safe assets (same as Safety Switch)

**Characteristics:**
- Most conservative filter (3 checks vs 1)
- Fewer false positives than single-indicator filters
- Adapts to changing volatility regimes (VIX adaptive)
- Confirms trend with multiple data sources (price, volume, volatility)
- Lower whipsaw than SMA crossover (DEMA smoothing)
- Generates 3-panel diagnostic plot
- Best for: Maximum capital preservation, bear market avoidance

**When to Use:**
- **Safety Switch**: Simple, proven, low maintenance
- **STORMGUARD**: Maximum protection, willing to sacrifice some upside for safety
- **Dual EMA**: Per-stock filtering, trend-following focus

### Dual EMA (Per-Stock Trend Filter)
**Logic:** Each stock must pass ALL three conditions:
1. Price > 20d EMA
2. 20d EMA > 50d EMA
3. 50d EMA slope > 0 (10-day derivative)

**Characteristics:**
- Stock-specific trend confirmation
- More aggressive filtering (can have many stocks in cash)
- Higher turnover than Safety Switch
- Best for: Trend-following within stocks

### None (Pure Momentum)
- No filtering
- Always invested (unless no valid momentum)
- Highest turnover
- Best for: Testing raw momentum performance

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

