"""Typed configuration dataclass for type safety and cleaner code."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Tuple, Optional


@dataclass
class StrategyConfig:
    """Typed configuration for backtest strategy."""
    
    # Backtest period
    start_date: datetime
    end_date: datetime
    
    # Momentum settings
    momentum_type: str
    momentum_period: int
    top_n: int
    
    # Rebalancing
    rebalance_frequency: str
    rebalance_weekday: int
    
    # Filter settings
    filter_type: str
    ema_short_period: int
    ema_long_period: int
    ema_derivative_lookback: int
    safety_sma_short: int
    safety_sma_long: int
    
    # StormGuard settings
    stormguard_volatility_threshold: float
    stormguard_volatility_watch_threshold: float
    stormguard_false_alarm_days: int
    stormguard_early_return_threshold: float
    stormguard_credit_risk_fast: int
    stormguard_credit_risk_slow: int
    stormguard_breadth_period: int
    stormguard_bear_exit_price_threshold: float
    stormguard_min_bear_duration: int
    stormguard_bear_exit_require_breadth: bool
    stormguard_bear_exit_require_majority: bool
    
    # StormGuard Velocity settings
    stormguard_velocity_enable: bool
    stormguard_velocity_roc_period: int
    stormguard_velocity_zscore_threshold: float
    stormguard_velocity_volatility_window: int
    stormguard_velocity_min_dwell_days: int
    stormguard_velocity_min_watch_dwell: int
    stormguard_velocity_watch_timeout_days: int
    
    # Polymorphic settings
    polymorphic_metric: str
    polymorphic_initial_years: int
    polymorphic_reeval_years: int
    polymorphic_fallback_momentum: str
    polymorphic_min_history_years: int
    
    # Advanced trade filters
    enable_momentum_persistence: bool
    momentum_persistence_min_diff: float
    momentum_persistence_periods: int
    enable_popndrop_filter: bool
    popndrop_max_return: float
    enable_volatility_adjustment: bool
    volatility_adjustment_period: int
    volatility_max_threshold: float
    volatility_adjustment_mult: float
    enable_price_action_filter: bool
    price_action_filter_type: str
    price_action_lookback_days: int
    
    # Universes and assets
    universes: Dict[str, List[str]]
    safe_assets: List[str]
    
    # System settings
    data_dir: str
    cache_enabled: bool
    market_calendar: str
    output_dir: str
    experiments_log: str
    
    # Trading costs
    initial_capital: float
    commission_pct: float
    slippage_pct: float
    
    # Multi-bucket settings
    is_multi_bucket: bool
    active_universes: Optional[List[Tuple[str, float]]] = None


def config_from_dict(config_dict: Dict) -> StrategyConfig:
    """Convert dict config to typed StrategyConfig."""
    return StrategyConfig(
        start_date=config_dict['start_date'],
        end_date=config_dict['end_date'],
        momentum_type=config_dict['momentum_type'],
        momentum_period=config_dict['momentum_period'],
        top_n=config_dict['top_n'],
        rebalance_frequency=config_dict['rebalance_frequency'],
        rebalance_weekday=config_dict['rebalance_weekday'],
        filter_type=config_dict['filter_type'],
        ema_short_period=config_dict['ema_short_period'],
        ema_long_period=config_dict['ema_long_period'],
        ema_derivative_lookback=config_dict['ema_derivative_lookback'],
        safety_sma_short=config_dict['safety_sma_short'],
        safety_sma_long=config_dict['safety_sma_long'],
        stormguard_volatility_threshold=config_dict['stormguard_volatility_threshold'],
        stormguard_volatility_watch_threshold=config_dict['stormguard_volatility_watch_threshold'],
        stormguard_false_alarm_days=config_dict['stormguard_false_alarm_days'],
        stormguard_early_return_threshold=config_dict['stormguard_early_return_threshold'],
        stormguard_credit_risk_fast=config_dict['stormguard_credit_risk_fast'],
        stormguard_credit_risk_slow=config_dict['stormguard_credit_risk_slow'],
        stormguard_breadth_period=config_dict['stormguard_breadth_period'],
        stormguard_bear_exit_price_threshold=config_dict['stormguard_bear_exit_price_threshold'],
        stormguard_min_bear_duration=config_dict['stormguard_min_bear_duration'],
        stormguard_bear_exit_require_breadth=config_dict['stormguard_bear_exit_require_breadth'],
        stormguard_bear_exit_require_majority=config_dict['stormguard_bear_exit_require_majority'],
        stormguard_velocity_enable=config_dict['stormguard_velocity_enable'],
        stormguard_velocity_roc_period=config_dict['stormguard_velocity_roc_period'],
        stormguard_velocity_zscore_threshold=config_dict['stormguard_velocity_zscore_threshold'],
        stormguard_velocity_volatility_window=config_dict['stormguard_velocity_volatility_window'],
        stormguard_velocity_min_dwell_days=config_dict['stormguard_velocity_min_dwell_days'],
        stormguard_velocity_min_watch_dwell=config_dict['stormguard_velocity_min_watch_dwell'],
        stormguard_velocity_watch_timeout_days=config_dict['stormguard_velocity_watch_timeout_days'],
        polymorphic_metric=config_dict['polymorphic_metric'],
        polymorphic_initial_years=config_dict['polymorphic_initial_years'],
        polymorphic_reeval_years=config_dict['polymorphic_reeval_years'],
        polymorphic_fallback_momentum=config_dict['polymorphic_fallback_momentum'],
        polymorphic_min_history_years=config_dict['polymorphic_min_history_years'],
        enable_momentum_persistence=config_dict['enable_momentum_persistence'],
        momentum_persistence_min_diff=config_dict['momentum_persistence_min_diff'],
        momentum_persistence_periods=config_dict['momentum_persistence_periods'],
        enable_popndrop_filter=config_dict['enable_popndrop_filter'],
        popndrop_max_return=config_dict['popndrop_max_return'],
        enable_volatility_adjustment=config_dict['enable_volatility_adjustment'],
        volatility_adjustment_period=config_dict['volatility_adjustment_period'],
        volatility_max_threshold=config_dict['volatility_max_threshold'],
        volatility_adjustment_mult=config_dict['volatility_adjustment_mult'],
        enable_price_action_filter=config_dict['enable_price_action_filter'],
        price_action_filter_type=config_dict['price_action_filter_type'],
        price_action_lookback_days=config_dict['price_action_lookback_days'],
        universes=config_dict['universes'],
        safe_assets=config_dict['safe_assets'],
        data_dir=config_dict['data_dir'],
        cache_enabled=config_dict['cache_enabled'],
        market_calendar=config_dict['market_calendar'],
        output_dir=config_dict['output_dir'],
        experiments_log=config_dict['experiments_log'],
        initial_capital=config_dict['initial_capital'],
        commission_pct=config_dict['commission_pct'],
        slippage_pct=config_dict['slippage_pct'],
        is_multi_bucket=config_dict['is_multi_bucket'],
        active_universes=config_dict.get('active_universes'),
    )

