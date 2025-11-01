"""Configuration for momentum strategy backtests."""

from typing import List, Dict, Any
from datetime import datetime


# Backtest parameters
START_DATE = datetime(2005, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Strategy parameters
ROC_PERIOD_DAYS = 21  # Approximately 1 month of trading days
TOP_N = 1  # Select top-1 stock
REBALANCE_WEEKDAY = 0  # Monday (0=Monday, 4=Friday)

# Universe definitions
UNIVERSES: Dict[str, List[str]] = {
    "US_Large_Cap": [
        "DIA",  # Dow Jones Industrial Average
        "SPY",  # S&P 500
        "QQQ",  # Nasdaq 100
        "VTV",  # Vanguard Value ETF
        "VUG",  # Vanguard Growth ETF
        "XLB",  # Materials Select Sector SPDR
        "XLE",  # Energy Select Sector SPDR
        "XLF",  # Financial Select Sector SPDR
        "XLI",  # Industrial Select Sector SPDR
        "XLK",  # Technology Select Sector SPDR
        "XLY",  # Consumer Discretionary Select Sector SPDR
    ],
    "Developed_Countries": [
        "DFIV", # iShares Developed Markets ex-US Small-Cap
        "EFA",  # iShares MSCI EAFE ETF
        "EWA",  # iShares MSCI Australia ETF
        "EWC",  # iShares MSCI Canada ETF
        "EWG",  # iShares MSCI Germany ETF
        "EWJ",  # iShares MSCI Japan ETF
        "EWU",  # iShares MSCI United Kingdom ETF
        "EZU",  # iShares MSCI Eurozone ETF
        "IEFA", # iShares Core MSCI EAFE ETF
        "SPDW", # SPDR Portfolio Developed World ex-US ETF
        "VEA",  # Vanguard FTSE Developed Markets ETF
        "GLD",  # SPDR Gold Trust
    ],
}

# Active universe to backtest
ACTIVE_UNIVERSE = "US_Large_Cap"

# Data settings
DATA_DIR = "data"
CACHE_ENABLED = True

# Output settings
OUTPUT_DIR = "output"

# Trading settings
INITIAL_CAPITAL = 100000.0
COMMISSION_PCT = 0.001  # 0.1% per trade (buy and sell)
SLIPPAGE_PCT = 0.0005   # 0.05% slippage


def get_config() -> Dict[str, Any]:
    """Return full configuration dictionary."""
    return {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "roc_period_days": ROC_PERIOD_DAYS,
        "top_n": TOP_N,
        "rebalance_weekday": REBALANCE_WEEKDAY,
        "universes": UNIVERSES,
        "data_dir": DATA_DIR,
        "cache_enabled": CACHE_ENABLED,
        "output_dir": OUTPUT_DIR,
        "initial_capital": INITIAL_CAPITAL,
        "commission_pct": COMMISSION_PCT,
        "slippage_pct": SLIPPAGE_PCT,
    }

