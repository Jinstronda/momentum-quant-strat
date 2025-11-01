"""Configuration for momentum strategy backtests."""

from typing import List, Dict, Any
from datetime import datetime


# ============================================================================
# MAIN SETTINGS (Change these for different strategies)
# ============================================================================

# Backtest period
START_DATE = datetime(2010, 1, 1)
END_DATE = datetime(2024, 12, 31)

# Active universe to backtest
ACTIVE_UNIVERSE = "Energy_Clean_Energy"

# Momentum calculation
MOMENTUM_TYPE = "POLYMORPHIC"  # Options: "ROC", "EMA", "Double_EMA", "DEMA", "TEMA", "POLYMORPHIC"
MOMENTUM_PERIOD = 63  # Days (ignored if POLYMORPHIC) - 21=1M, 63=3M, 126=6M, 252=12M
TOP_N = 1  # Select top-N stocks (currently only top-1 supported)

# Rebalancing
REBALANCE_FREQUENCY = "monthly"  # Options: "weekly" or "monthly"
REBALANCE_WEEKDAY = 0  # For weekly: 0=Monday, 1=Tuesday, etc.

# Market regime filter
FILTER_TYPE = "STORMGUARD"  # Options: "DUAL_EMA", "SAFETY_SWITCH", "STORMGUARD", "NONE"


# ============================================================================
# FILTER CONFIGURATIONS (Advanced settings for each filter type)
# ============================================================================

# --- DUAL EMA FILTER (per-stock trend filter) ---
EMA_SHORT_PERIOD = 20  # Short-term EMA
EMA_LONG_PERIOD = 50   # Long-term EMA
EMA_DERIVATIVE_LOOKBACK = 10  # Days for slope calculation
# Stocks must pass: Price>20d, 20d>50d, 50d slope>0 → eligible

# --- SAFETY SWITCH (simple market regime filter) ---
SAFETY_SMA_SHORT = 50   # SPY short SMA
SAFETY_SMA_LONG = 200   # SPY long SMA
# Rule: SPY.SMA(50) > SMA(200) → Bull, else Bear → safe assets

# --- STORMGUARD (Adapted StormGuard-Armor using SPY + VIX only) ---
STORMGUARD_VOLATILITY_THRESHOLD = 40.0  # VIX threshold for circuit breaker
STORMGUARD_FALSE_ALARM_DAYS = 10        # Days to check for false alarm validation
STORMGUARD_EARLY_RETURN_THRESHOLD = 0.75  # 75% rebound threshold for early return
# Adapted algorithm using OBV and VIX proxies (NYSE data not available on Yahoo Finance)

# --- POLYMORPHIC MOMENTUM (automated filter selection) ---
POLYMORPHIC_METRIC = "Sharpe"  # Options: "Sharpe" or "Sortino"
POLYMORPHIC_INITIAL_YEARS = 1  # Years for initial bake-off
POLYMORPHIC_REEVAL_YEARS = 2   # Years for quarterly re-evaluation
POLYMORPHIC_FALLBACK_MOMENTUM = "ROC"  # Fallback if insufficient history
POLYMORPHIC_MIN_HISTORY_YEARS = 1  # Minimum years needed


# ============================================================================
# UNIVERSES (Asset buckets to trade)
# ============================================================================

UNIVERSES: Dict[str, List[str]] = {
    "AI_Developed_Countries": [
        "EZA", "EWZ", "FXI", "QQQ", "EWA", "IWM", "EWL", "INDA", 
        "GLD", "EWU", "EWW", "EWC", "EZA"
    ],
    "AI_US_Large_Cap": [
        "VNQ", "VTV", "VUG", "XLB", "XLE", "XLF", "XLI", "XLK", 
        "XLP", "XLU", "XLV", "XLY"
    ],
    "AI_Energy": [
        "XOM", "CVX", "COP", "WMB", "EOG", "OKE", "KMI", "SLB", 
        "MPC", "PSX", "XLE"
    ],
    "US_Tech_Innovation": [
        "QQQ", "SMH", "SOXX", "ARKK", "ARKW", "XBI", "IGV", "TAN", 
        "CIBR", "IYW", "BOTZ"
    ],
    "US_Sector_Cyclicals": [
        "XLY", "XLF", "XLE", "XLI", "XLB", "XLC", "XRT", "ITB", 
        "IYT", "XLK", "XLP", "XHB"
    ],
    "US_Small_Mid_Cap": [
        "IWM", "IJR", "SPSM", "SCHA", "MDY", "IJH", "IWO", "IWN", 
        "VO", "IWR", "RSP", "VTWO"
    ],
    "Intl_Emerging_Markets": [
        "EEM", "VWO", "EWZ", "FXI", "MCHI", "INDA", "EWY", "EWT", 
        "EWH", "ILF", "IEMG", "SCHE"
    ],
    "Commodities_Gold_Materials": [
        "GLD", "GDX", "GDXJ", "SLV", "DBA", "DBC", "USO", "XME", 
        "COPX", "URA", "PALL", "LIT"
    ],
    "Energy_Clean_Energy": [
        "XLE", "OIH", "FCG", "TAN", "ICLN", "URA", "LIT", "XOP", 
        "VDE", "AMLP", "NLR", "IXC"
    ],
    "Crypto_Blockchain": [
        "IBIT", "BITO", "WGMI", "BLOK", "COIN", "MSTR", "RIOT", 
        "MARA", "HUT"
    ],
    "US_Tech_Leaders": [
        "NVDA", "TSLA", "MSFT", "META", "AMZN", "AAPL", "PLTR", 
        "COIN", "MSTR", "SHOP", "NFLX", "RIVN"
    ],
    "AI_Harvest_Agriculture": [
        "DE", "AGCO", "CTVA", "FMC", "NTR", "CF", "MOS", "ADM", 
        "BG", "VMI", "LNN", "TSN"
    ],
}

# Safe assets (for bear market rotation)
SAFE_ASSETS = [
    "SHY",   # iShares 1-3 Year Treasury Bond
    "VGSH",  # Vanguard Short-Term Treasury
    "AGG",   # iShares Core US Aggregate Bond
    "BND",   # Vanguard Total Bond Market
    "IEI",   # iShares 3-7 Year Treasury Bond
    "TIPX",  # SPDR Bloomberg 1-10 Year TIPS
    "BLV",   # Vanguard Long-Term Bond
    "IEF",   # iShares 7-10 Year Treasury Bond
    "TLH",   # iShares 10-20 Year Treasury Bond
    "TLT",   # iShares 20+ Year Treasury Bond
    "ZROZ",  # PIMCO 25+ Year Zero Coupon US Treasury
    "GLD",   # SPDR Gold Trust
]


# ============================================================================
# SYSTEM SETTINGS (Rarely changed)
# ============================================================================

# Data settings
DATA_DIR = "data"
CACHE_ENABLED = True
MARKET_CALENDAR = "NYSE"  # Market calendar for trading days/holidays

# Output settings
OUTPUT_DIR = "output"
EXPERIMENTS_LOG = "experiments/experiments.md"  # Auto-log results here

# Trading costs
INITIAL_CAPITAL = 100000.0
COMMISSION_PCT = 0.001  # 0.1% per trade (buy and sell)
SLIPPAGE_PCT = 0.0005   # 0.05% slippage


# ============================================================================
# CONFIG EXPORT (Do not modify)
# ============================================================================

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
        "filter_type": FILTER_TYPE,
        "ema_short_period": EMA_SHORT_PERIOD,
        "ema_long_period": EMA_LONG_PERIOD,
        "ema_derivative_lookback": EMA_DERIVATIVE_LOOKBACK,
        "safety_sma_short": SAFETY_SMA_SHORT,
        "safety_sma_long": SAFETY_SMA_LONG,
        "stormguard_volatility_threshold": STORMGUARD_VOLATILITY_THRESHOLD,
        "stormguard_false_alarm_days": STORMGUARD_FALSE_ALARM_DAYS,
        "stormguard_early_return_threshold": STORMGUARD_EARLY_RETURN_THRESHOLD,
        "polymorphic_metric": POLYMORPHIC_METRIC,
        "polymorphic_initial_years": POLYMORPHIC_INITIAL_YEARS,
        "polymorphic_reeval_years": POLYMORPHIC_REEVAL_YEARS,
        "polymorphic_fallback_momentum": POLYMORPHIC_FALLBACK_MOMENTUM,
        "polymorphic_min_history_years": POLYMORPHIC_MIN_HISTORY_YEARS,
        "universes": UNIVERSES,
        "safe_assets": SAFE_ASSETS,
        "data_dir": DATA_DIR,
        "cache_enabled": CACHE_ENABLED,
        "market_calendar": MARKET_CALENDAR,
        "output_dir": OUTPUT_DIR,
        "experiments_log": EXPERIMENTS_LOG,
        "initial_capital": INITIAL_CAPITAL,
        "commission_pct": COMMISSION_PCT,
        "slippage_pct": SLIPPAGE_PCT,
    }
