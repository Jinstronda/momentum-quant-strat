"""Shared utilities for backtest execution - eliminates duplication."""

from typing import Dict, Tuple, Optional, List
from datetime import datetime
import pandas as pd

from src.data import DataLoader
from src.strategy import MomentumStrategy


def load_filter_data(
    config: Dict,
    loader: DataLoader,
    extended_start: datetime,
    end_date: datetime
) -> Tuple[
    Optional[pd.Series], Optional[pd.DataFrame], Optional[pd.Series],
    Optional[pd.Series], Optional[pd.Series], Optional[pd.Series],
    Optional[pd.Series]
]:
    """
    Load all filter data (SPY, VIX, HYG, IEF, RSP, safe assets).
    
    Returns:
        Tuple of (spy_prices, safe_prices, spy_volume, vix_prices,
                  hyg_prices, ief_prices, rsp_prices)
    """
    spy_prices = None
    safe_prices = None
    spy_volume = None
    vix_prices = None
    hyg_prices = None
    ief_prices = None
    rsp_prices = None
    
    filter_type = config.get('filter_type', 'NONE')
    
    if filter_type == 'SAFETY_SWITCH':
        print("Loading SPY for Safety Switch filter...")
        spy_prices, _ = loader.get_symbol_with_volume('SPY', extended_start, end_date)
        print("[OK] SPY loaded\n")
        
        safe_assets = config.get('safe_assets', [])
        if safe_assets:
            print(f"Loading {len(safe_assets)} safe assets...")
            safe_prices = loader.get_close_prices(safe_assets, extended_start, end_date)
            print(f"[OK] Safe assets loaded: {', '.join(safe_assets)}\n")
    
    elif filter_type in ['STORMGUARD', 'STORMGUARD_VELOCITY']:
        filter_name = "STORMGUARD-VELOCITY (3-State)" if filter_type == 'STORMGUARD_VELOCITY' else "STORMGUARD (5-Component)"
        print(f"Loading data for {filter_name}...")
        
        spy_prices, spy_volume = loader.get_symbol_with_volume('SPY', extended_start, end_date)
        vix_prices, _ = loader.get_symbol_with_volume('^VIX', extended_start, end_date)
        hyg_prices, _ = loader.get_symbol_with_volume('HYG', extended_start, end_date)
        ief_prices, _ = loader.get_symbol_with_volume('IEF', extended_start, end_date)
        rsp_prices, _ = loader.get_symbol_with_volume('RSP', extended_start, end_date)
        
        print("[OK] Loaded SPY, VIX, HYG, IEF, RSP (5 metrics)\n")
        
        safe_assets = config.get('safe_assets', [])
        if safe_assets:
            print(f"Loading {len(safe_assets)} safe assets...")
            safe_prices = loader.get_close_prices(safe_assets, extended_start, end_date)
            print(f"[OK] Safe assets loaded: {', '.join(safe_assets)}\n")
    
    return spy_prices, safe_prices, spy_volume, vix_prices, hyg_prices, ief_prices, rsp_prices


def create_strategy_from_config(config: Dict, actual_momentum_type: str) -> MomentumStrategy:
    """Create MomentumStrategy instance from config dict."""
    return MomentumStrategy(
        momentum_type=actual_momentum_type,
        momentum_period=config.get('momentum_period', 21),
        top_n=config.get('top_n', 1),
        filter_type=config.get('filter_type', 'NONE'),
        ema_short=config.get('ema_short_period', 20),
        ema_long=config.get('ema_long_period', 50),
        ema_derivative_lookback=config.get('ema_derivative_lookback', 10),
        safety_sma_short=config.get('safety_sma_short', 50),
        safety_sma_long=config.get('safety_sma_long', 200),
        stormguard_dema_fast=config.get('stormguard_volatility_threshold', 20.0),
        polymorphic_metric=config.get('polymorphic_metric', 'Sharpe'),
        polymorphic_initial_years=config.get('polymorphic_initial_years', 5),
        polymorphic_reeval_years=config.get('polymorphic_reeval_years', 2),
        initial_capital=config['initial_capital'],
        enable_momentum_persistence=config.get('enable_momentum_persistence', False),
        momentum_persistence_min_diff=config.get('momentum_persistence_min_diff', 0.02),
        momentum_persistence_periods=config.get('momentum_persistence_periods', 2),
        enable_popndrop_filter=config.get('enable_popndrop_filter', False),
        popndrop_max_return=config.get('popndrop_max_return', 0.15),
        enable_volatility_adjustment=config.get('enable_volatility_adjustment', False),
        volatility_adjustment_period=config.get('volatility_adjustment_period', 63),
        volatility_max_threshold=config.get('volatility_max_threshold', 0.25),
        volatility_adjustment_mult=config.get('volatility_adjustment_mult', 0.8),
        enable_price_action_filter=config.get('enable_price_action_filter', False),
        price_action_filter_type=config.get('price_action_filter_type', 'EMA20_LOW'),
        price_action_lookback_days=config.get('price_action_lookback_days', 21),
        price_action_relative_close_threshold=config.get('price_action_relative_close_threshold', 0.5)
    )


def load_ohlc_if_needed(
    config: Dict,
    loader: DataLoader,
    symbols: List[str],
    extended_start: datetime,
    end_date: datetime
) -> Optional[pd.DataFrame]:
    """Load OHLC data if price action filter is enabled."""
    if not config.get('enable_price_action_filter', False):
        return None
    
    print(f"Loading OHLC data for price action filter ({config.get('price_action_filter_type')})...")
    prices_ohlc = loader.get_ohlc_prices(symbols, extended_start, end_date)
    print("[OK] OHLC data loaded\n")
    return prices_ohlc

