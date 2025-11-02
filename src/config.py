"""Configuration for momentum strategy backtests."""

from typing import List, Dict, Any
from datetime import datetime

from src.config_types import StrategyConfig, config_from_dict


# ============================================================================
# MAIN SETTINGS (Change these for different strategies)
# ============================================================================

# Backtest period
START_DATE = datetime(1995, 1, 3)
END_DATE = datetime(2024, 12, 31)

# Active universe to backtest (single-bucket mode)
ACTIVE_UNIVERSE = [
    ("AI_US_Sectors_Basic", 0.50),      # 50% US sectors (all existed since 1998)
    ("AI_Global_Developed", 0.20),      # 20% developed markets (all existed by 2001)
    ("AI_Emerging_Markets", 0.15),      # 15% emerging (BRIC hype era)
    ("AI_Real_Assets", 0.15),           # 15% gold/real estate (inflation fears)
]
# OR use multi-bucket mode with allocations (NEW)
# Uncomment to enable multi-bucket portfolio:
# ACTIVE_UNIVERSES = [
#     ("AI_US_Large_Cap", 0.6),       # 60% allocation
#     ("AI_Emerging_Markets", 0.4),   # 40% allocation
# ]
# Note: Allocations must sum to 1.0

# Momentum calculation
MOMENTUM_TYPE = "POLYMORPHIC"  # Options: "ROC", "EMA", "Double_EMA", "DEMA", "TEMA", "POLYMORPHIC"
MOMENTUM_PERIOD = 63  # Days (ignored if POLYMORPHIC) - 21=1M, 63=3M, 126=6M, 252=12M
TOP_N = 1  # Select top-N stocks (currently only top-1 supported)

# Rebalancing
REBALANCE_FREQUENCY = "weekly"  # Options: "weekly" or "monthly"
REBALANCE_WEEKDAY = 4 # For weekly: 0=Monday, 1=Tuesday, etc.

# Market regime filter
FILTER_TYPE = "STORMGUARD"  # Options: "DUAL_EMA", "SAFETY_SWITCH", "STORMGUARD", "STORMGUARD_VELOCITY", "NONE"


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

# --- STORMGUARD (5-Component Market Regime Filter) ---
# Standard thresholds
STORMGUARD_VOLATILITY_THRESHOLD = 40  # VIX threshold for emergency circuit breaker (was 20 - WAY too sensitive)
STORMGUARD_VOLATILITY_WATCH_THRESHOLD = 25  # VIX for WATCH state (moderate concern)
STORMGUARD_FALSE_ALARM_DAYS = 30      # Days to check for false alarm validation
STORMGUARD_EARLY_RETURN_THRESHOLD = 0.75  # 75% rebound threshold
STORMGUARD_CREDIT_RISK_FAST = 20   # Fast SMA for HYG:IEF ratio (leading indicator)
STORMGUARD_CREDIT_RISK_SLOW = 50   # Slow SMA for HYG:IEF ratio (leading indicator)
STORMGUARD_BREADTH_PERIOD = 63     # ROC period for RSP vs SPY breadth (leading indicator)
# Uses 5 metrics: Price-Trend, Money Flow, Sentiment, Credit Risk (LEADING), Internal Breadth (LEADING)

# Bear Exit Requirements (Harder to exit BEAR mode - prevents premature exits)
STORMGUARD_BEAR_EXIT_PRICE_THRESHOLD = 1.5  # Price trend must be > this (not just > 0)
STORMGUARD_MIN_BEAR_DURATION = 20  # Minimum days in BEAR before exit allowed
STORMGUARD_BEAR_EXIT_REQUIRE_BREADTH = True  # Also require breadth confirmation
STORMGUARD_BEAR_EXIT_REQUIRE_MAJORITY = False  # If True, need 4/5 metrics (very conservative)

# --- STORMGUARD VELOCITY (Enhanced with WATCH state) ---
# Only applies if FILTER_TYPE = "STORMGUARD_VELOCITY"
STORMGUARD_VELOCITY_ENABLE = True  # Enable velocity detection (ignored if not using STORMGUARD_VELOCITY)
STORMGUARD_VELOCITY_ROC_PERIOD = 10  # Days to measure metric velocity
STORMGUARD_VELOCITY_ZSCORE_THRESHOLD = -2.0  # Z-score threshold (recommended: -2.0)
STORMGUARD_VELOCITY_VOLATILITY_WINDOW = 63  # Days for z-score normalization
STORMGUARD_VELOCITY_MIN_DWELL_DAYS = 10  # Minimum days in BULL/BEAR before state change
STORMGUARD_VELOCITY_MIN_WATCH_DWELL = 5  # Minimum days in WATCH before exit (prevents flickering)
STORMGUARD_VELOCITY_WATCH_TIMEOUT_DAYS = 20  # Max days in WATCH before reverting to BULL

# --- POLYMORPHIC MOMENTUM (automated filter selection) ---
POLYMORPHIC_METRIC = "Sharpe"  # Options: "Sharpe" or "Sortino"
POLYMORPHIC_INITIAL_YEARS = 5  # Years for initial bake-off
POLYMORPHIC_REEVAL_YEARS = 5  # Years for quarterly re-evaluation
POLYMORPHIC_FALLBACK_MOMENTUM = "Double_EMA"  # Fallback if insufficient history
POLYMORPHIC_MIN_HISTORY_YEARS = 3  # Minimum years needed

# --- ADVANCED TRADE FILTERS (Based on CORE11 methodology) ---
# Momentum Persistence Filter: Only trade if momentum change is significant
ENABLE_MOMENTUM_PERSISTENCE = False  # Set True to reduce whipsaws
MOMENTUM_PERSISTENCE_MIN_DIFF = 0.02  # Minimum 2% momentum difference to trade
MOMENTUM_PERSISTENCE_PERIODS = 2  # New leader must be top for N periods

# PopNDrop Risk Filter: Exclude overbought ETFs likely to reverse
ENABLE_POPNDROP_FILTER = False  # Set True to avoid chasing parabolic moves
POPNDROP_MAX_RETURN = 0.15  # Skip ETFs up >15% in 21 days

# Volatility-Adjusted Momentum: Use Sharpe-like risk-adjusted scores
ENABLE_VOLATILITY_ADJUSTMENT = False  # Set True to prefer lower-volatility winners
VOLATILITY_ADJUSTMENT_PERIOD = 63  # Period for volatility calculation
VOLATILITY_MAX_THRESHOLD = 0.25  # Penalize volatility >25% (80% score)
VOLATILITY_ADJUSTMENT_MULT = 0.8  # Score multiplier for high volatility

# --- PRICE ACTION ENTRY FILTER (NEW) ---
# Only enter new positions when price action confirms (e.g., pullback to support)
# This filter ONLY applies when SWITCHING assets (not when staying in same asset)
ENABLE_PRICE_ACTION_FILTER = True  # Set True to wait for pullback before entry
PRICE_ACTION_FILTER_TYPE = "EMA20_LOW"  # Options: "EMA20_LOW", "EMA20_DEFENDED"
PRICE_ACTION_LOOKBACK_DAYS = 21  # Days to look back for valid entry signal
PRICE_ACTION_RELATIVE_CLOSE_THRESHOLD = 0.5  # For EMA20_DEFENDED: min relative close (0.5 = upper half)

# Filter Types Explained:
# - EMA20_LOW: Low ≤ EMA(20) in last N days (any touch counts)
# - EMA20_DEFENDED: Low ≤ EMA(20) AND bar closed in upper 50% of range
#   (confirms buyers defended support - stronger signal)


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
        "XLP", "XLU", "XLV", "XLY","SPY"
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

    "AI_US_Sectors_Basic": [
        "XLE",  # Energy (1998)
        "XLF",  # Financials (1998)
        "XLK",  # Technology (1998)
        "XLI",  # Industrials (1998)
        "XLU",  # Utilities (1998)
        "XLV",  # Health Care (1998)
        "XLP",  # Consumer Staples (1998)
        "XLB",  # Materials (1998)
        "XLY",  # Consumer Discretionary (1998)
    ],
    
    "AI_US_Style_Factors": [
        "SPY",  # S&P 500 (1993)
        "QQQ",  # Nasdaq 100 (1999)
        "IWM",  # Russell 2000 (Small-Cap) (2000)
        "VTV",  # Vanguard Value (2004)
        "VUG",  # Vanguard Growth (2004)
    ],

    "AI_Global_Developed": [
        "EFA",  # EAFE (Broad Developed ex-US) (2001)
        "EWJ",  # Japan (1996)
        "EWG",  # Germany (1996)
        "EWU",  # United Kingdom (1996)
        "EWC",  # Canada (1996)
        "EWA",  # Australia (1996)
    ],

    "AI_Emerging_Markets": [
        "EEM",  # MSCI Emerging Markets (Broad) (2003)
        "EWZ",  # Brazil (2000)
        "FXI",  # China (2004)
        "EWY",  # South Korea (2000)
        "EWT",  # Taiwan (2000)
    ],
    
    "AI_Real_Assets": [
        "GLD",  # Gold (2004)
        "IYR",  # US Real Estate (2000)
        "VNQ",  # Vanguard Real Estate (2004)
        "XME",  # Metals & Mining (2006)*
        "GDX",  # Gold Miners (2006)*
        # *Note: GDX/XME started in 2006. They will be excluded from the 
        # initial 2005-2010 bake-off but will enter the rotation later. 
    ], 
}

# Safe assets (for bear market rotation)
SAFE_ASSETS = [
    "TLT", "IEF", "IEI", "SHY",  # Treasuries
    "GLD",  # Gold (shown in trades)
    "TIPX", "AGG", "BND"  # Bonds
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
    # Check if multi-bucket mode is enabled
    is_multi_bucket = False
    active_universes = None
    
    # Check ACTIVE_UNIVERSES first (new way)
    if 'ACTIVE_UNIVERSES' in globals() and isinstance(globals()['ACTIVE_UNIVERSES'], list):
        active_universes = globals()['ACTIVE_UNIVERSES']
        if len(active_universes) > 1:
            is_multi_bucket = True
    # Also check if ACTIVE_UNIVERSE is a list (user convenience)
    elif isinstance(ACTIVE_UNIVERSE, list):
        active_universes = ACTIVE_UNIVERSE
        if len(active_universes) > 1:
            is_multi_bucket = True
    
    # Validate multi-bucket configuration
    if is_multi_bucket and active_universes:
        # Validate allocations
        total_allocation = sum(allocation for _, allocation in active_universes)
        if abs(total_allocation - 1.0) > 0.001:
            raise ValueError(f"Allocations must sum to 1.0, got {total_allocation}")
        # Validate universe names
        for universe_name, _ in active_universes:
            if universe_name not in UNIVERSES:
                raise ValueError(f"Unknown universe: {universe_name}")
    
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
        "stormguard_credit_risk_fast": STORMGUARD_CREDIT_RISK_FAST,
        "stormguard_credit_risk_slow": STORMGUARD_CREDIT_RISK_SLOW,
        "stormguard_breadth_period": STORMGUARD_BREADTH_PERIOD,
        "polymorphic_metric": POLYMORPHIC_METRIC,
        "polymorphic_initial_years": POLYMORPHIC_INITIAL_YEARS,
        "polymorphic_reeval_years": POLYMORPHIC_REEVAL_YEARS,
        "polymorphic_fallback_momentum": POLYMORPHIC_FALLBACK_MOMENTUM,
        "polymorphic_min_history_years": POLYMORPHIC_MIN_HISTORY_YEARS,
        "enable_momentum_persistence": ENABLE_MOMENTUM_PERSISTENCE,
        "momentum_persistence_min_diff": MOMENTUM_PERSISTENCE_MIN_DIFF,
        "momentum_persistence_periods": MOMENTUM_PERSISTENCE_PERIODS,
        "enable_popndrop_filter": ENABLE_POPNDROP_FILTER,
        "popndrop_max_return": POPNDROP_MAX_RETURN,
        "enable_volatility_adjustment": ENABLE_VOLATILITY_ADJUSTMENT,
        "volatility_adjustment_period": VOLATILITY_ADJUSTMENT_PERIOD,
        "volatility_max_threshold": VOLATILITY_MAX_THRESHOLD,
        "volatility_adjustment_mult": VOLATILITY_ADJUSTMENT_MULT,
        "enable_price_action_filter": ENABLE_PRICE_ACTION_FILTER,
        "price_action_filter_type": PRICE_ACTION_FILTER_TYPE,
        "price_action_lookback_days": PRICE_ACTION_LOOKBACK_DAYS,
        "price_action_relative_close_threshold": PRICE_ACTION_RELATIVE_CLOSE_THRESHOLD,
        "stormguard_velocity_enable": STORMGUARD_VELOCITY_ENABLE,
        "stormguard_velocity_roc_period": STORMGUARD_VELOCITY_ROC_PERIOD,
        "stormguard_velocity_zscore_threshold": STORMGUARD_VELOCITY_ZSCORE_THRESHOLD,
        "stormguard_velocity_volatility_window": STORMGUARD_VELOCITY_VOLATILITY_WINDOW,
        "stormguard_velocity_min_dwell_days": STORMGUARD_VELOCITY_MIN_DWELL_DAYS,
        "stormguard_velocity_min_watch_dwell": STORMGUARD_VELOCITY_MIN_WATCH_DWELL,
        "stormguard_velocity_watch_timeout_days": STORMGUARD_VELOCITY_WATCH_TIMEOUT_DAYS,
        "stormguard_volatility_watch_threshold": STORMGUARD_VOLATILITY_WATCH_THRESHOLD,
        "stormguard_bear_exit_price_threshold": STORMGUARD_BEAR_EXIT_PRICE_THRESHOLD,
        "stormguard_min_bear_duration": STORMGUARD_MIN_BEAR_DURATION,
        "stormguard_bear_exit_require_breadth": STORMGUARD_BEAR_EXIT_REQUIRE_BREADTH,
        "stormguard_bear_exit_require_majority": STORMGUARD_BEAR_EXIT_REQUIRE_MAJORITY,
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
        "is_multi_bucket": is_multi_bucket,
        "active_universes": active_universes,
    }


def get_typed_config() -> StrategyConfig:
    """Return typed configuration object (preferred over dict)."""
    return config_from_dict(get_config())
