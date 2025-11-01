# Momentum Strategy Backtest

## Overview
Pure momentum strategy that selects the top-1 ETF by 1-month ROC, rebalanced weekly on Mondays.

## Strategy Logic
- **Universe**: US Large Cap ETFs (DIA, SPY, QQQ, VTV, VUG, XLB, XLE, XLF, XLI, XLK, XLY)
- **Indicator**: 1-month Rate of Change (ROC) - 21 trading days
- **Selection**: Top-1 ETF by ROC
- **Rebalance**: Every Monday (NYSE trading days)
- **Execution**: No lookahead bias, holiday-aware scheduling
- **Costs**: 0.1% commission + 0.05% slippage per trade

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
```bash
uv run python main.py
# or
python main.py
```

## Testing
```bash
uv run pytest tests/ -v
# or
pytest tests/ -v
```

## Output
All results are saved in the `output/` directory:
- `*_metrics.csv` - Performance metrics
- `*_trades.csv` - Trade log with all transactions
- `*_equity.csv` - Daily equity curve
- `*_equity_curve.png` - Equity visualization
- `*_drawdown.png` - Drawdown chart
- `*_returns_dist.png` - Returns distribution analysis
- `*_monthly_returns.png` - Monthly returns heatmap

## Project Structure
```
.
├── src/
│   ├── config.py          # Strategy parameters and universes
│   ├── data.py            # Data loading with yfinance + parquet caching
│   ├── indicators.py      # ROC and momentum calculations
│   ├── schedule.py        # Rebalance scheduling with market calendar
│   ├── strategy.py        # Position selection logic
│   ├── backtest.py        # Backtest engine and metrics
│   └── reporting.py       # Report generation and visualization
├── tests/                 # Unit tests
├── data/                  # Cached price data (parquet)
├── output/                # Backtest results
├── main.py                # Main runner script
└── requirements.txt       # Python dependencies
```

## Configuration
Edit `src/config.py` to customize:
- Start/End dates
- ROC period
- Rebalance frequency
- Trading costs
- Universe composition

