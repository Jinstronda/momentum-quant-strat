"""Configuration for momentum strategy backtests."""

from typing import List, Dict, Any
from datetime import datetime


# Backtest parameters
START_DATE = datetime(2005, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Strategy parameters - MOMENTUM CALCULATION
MOMENTUM_TYPE = "Double_EMA"  # Options:
                       #   "ROC" - Rate of Change (percentage change, responsive)
                       #   "Double_EMA" - EMA(EMA(price)) - super smooth, slow, kills noise
                       #   "DEMA" - 2*EMA - EMA(EMA) - technical DEMA, reduces lag
MOMENTUM_PERIOD = 63  # Number of days for momentum calculation
                       # Common values:
                       #   21 days ≈ 1 month
                       #   63 days ≈ 3 month  
                       #   126 days ≈ 6 month (classic Jegadeesh-Titman)
                       #   252 days ≈ 12 month
                       #
                       # Momentum Type Guide:
                       # - ROC: Direct % change, most responsive, higher turnover
                       # - Double_EMA: Smoothest, slowest, major trends only, low turnover
                       # - DEMA: Technical formula, balanced lag reduction
TOP_N = 1  # Select top-1 stock

# Rebalancing
REBALANCE_FREQUENCY = "monthly"  # Options: "weekly" or "monthly"
REBALANCE_WEEKDAY = 0  # For weekly: 0=Monday, 1=Tuesday, etc.

# Moving Average Filter - DUAL EMA SYSTEM
USE_MA_FILTER = True  # Enable/disable EMA filter
EMA_SHORT_PERIOD = 20  # Short-term EMA (20 days)
EMA_LONG_PERIOD = 50   # Long-term EMA (50 days)
EMA_DERIVATIVE_LOOKBACK = 10  # Days to look back for 50 EMA derivative (slope)

# Eligibility Rules (must meet ALL to be eligible):
# 1. Price > 20 EMA
# 2. 20 EMA > 50 EMA  
# 3. 50 EMA derivative > 0 (trending up, calculated over EMA_DERIVATIVE_LOOKBACK days)
#
# Exit Rule (loses eligibility when):
# - 50 EMA derivative < 0 (starts trending down)
#
# If no assets are eligible -> Go to CASH (money market)

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
MARKET_CALENDAR = "NYSE"  # Market calendar for trading days/holidays

# Output settings
OUTPUT_DIR = "output"
EXPERIMENTS_LOG = "experiments/experiments.md"  # Auto-log results here

# Trading settings
INITIAL_CAPITAL = 100000.0
COMMISSION_PCT = 0.001  # 0.1% per trade (buy and sell)
SLIPPAGE_PCT = 0.0005   # 0.05% slippage


def get_config() -> Dict[str, Any]:
    """Return full configuration dictionary."""
    return {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "momentum_type": MOMENTUM_TYPE,
        "momentum_period": MOMENTUM_PERIOD,
        "top_n": TOP_N,
        "rebalance_frequency": REBALANCE_FREQUENCY,
        "rebalance_weekday": REBALANCE_WEEKDAY,
        "use_ma_filter": USE_MA_FILTER,
        "ema_short_period": EMA_SHORT_PERIOD,
        "ema_long_period": EMA_LONG_PERIOD,
        "ema_derivative_lookback": EMA_DERIVATIVE_LOOKBACK,
        "universes": UNIVERSES,
        "data_dir": DATA_DIR,
        "cache_enabled": CACHE_ENABLED,
        "market_calendar": MARKET_CALENDAR,
        "output_dir": OUTPUT_DIR,
        "experiments_log": EXPERIMENTS_LOG,
        "initial_capital": INITIAL_CAPITAL,
        "commission_pct": COMMISSION_PCT,
        "slippage_pct": SLIPPAGE_PCT,
    }

