"""Rebalance schedule generation with market calendar support."""

from datetime import datetime, timedelta
from typing import List
import pandas as pd
import pandas_market_calendars as mcal


def get_rebalance_dates(
    start_date: datetime,
    end_date: datetime,
    weekday: int = 0,
    market: str = 'NYSE'
) -> List[datetime]:
    """
    Generate rebalance dates for a given weekday, respecting market holidays.
    
    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        weekday: Day of week (0=Monday, 1=Tuesday, ..., 4=Friday)
        market: Market calendar to use (default: NYSE)
        
    Returns:
        List of rebalance dates (datetime objects)
    """
    # Get market calendar
    calendar = mcal.get_calendar(market)
    
    # Get valid trading days in the date range
    schedule = calendar.schedule(
        start_date=start_date,
        end_date=end_date
    )
    
    trading_days = schedule.index.to_list()
    
    # Filter for specified weekday
    rebalance_dates = []
    for date in trading_days:
        # Check if this is the desired weekday
        if date.weekday() == weekday:
            rebalance_dates.append(date.to_pydatetime())
    
    return rebalance_dates


def get_valid_trading_days(
    start_date: datetime,
    end_date: datetime,
    market: str = 'NYSE'
) -> List[datetime]:
    """
    Get all valid trading days in a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        market: Market calendar to use
        
    Returns:
        List of valid trading days
    """
    calendar = mcal.get_calendar(market)
    schedule = calendar.schedule(start_date=start_date, end_date=end_date)
    return [d.to_pydatetime() for d in schedule.index]


def get_next_trading_day(
    date: datetime,
    market: str = 'NYSE'
) -> datetime:
    """
    Get the next valid trading day after a given date.
    
    Args:
        date: Reference date
        market: Market calendar to use
        
    Returns:
        Next valid trading day
    """
    calendar = mcal.get_calendar(market)
    
    # Look ahead up to 10 days to find next trading day
    for i in range(1, 11):
        next_date = date + timedelta(days=i)
        schedule = calendar.schedule(start_date=next_date, end_date=next_date)
        if not schedule.empty:
            return schedule.index[0].to_pydatetime()
    
    raise ValueError(f"No trading day found within 10 days of {date}")


def align_dates_to_trading_days(
    dates: List[datetime],
    market: str = 'NYSE',
    how: str = 'previous'
) -> List[datetime]:
    """
    Align dates to valid trading days.
    
    Args:
        dates: List of dates to align
        market: Market calendar to use
        how: 'previous' to use previous trading day, 'next' for next trading day
        
    Returns:
        List of aligned trading days
    """
    calendar = mcal.get_calendar(market)
    aligned = []
    
    for date in dates:
        # Check if date is already a trading day
        schedule = calendar.schedule(start_date=date, end_date=date)
        
        if not schedule.empty:
            # Already a trading day
            aligned.append(date)
        else:
            # Find nearest trading day
            if how == 'next':
                next_day = get_next_trading_day(date, market)
                aligned.append(next_day)
            else:  # previous
                # Look back up to 10 days
                for i in range(1, 11):
                    prev_date = date - timedelta(days=i)
                    schedule = calendar.schedule(start_date=prev_date, end_date=prev_date)
                    if not schedule.empty:
                        aligned.append(schedule.index[0].to_pydatetime())
                        break
    
    return aligned


def create_rebalance_schedule(
    start_date: datetime,
    end_date: datetime,
    weekday: int = 0,
    lookback_periods: int = 21,
    market: str = 'NYSE'
) -> pd.DataFrame:
    """
    Create a complete rebalance schedule with signal calculation dates.
    
    This ensures no lookahead bias by calculating signals based on data
    available only up to the day before rebalancing.
    
    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        weekday: Day of week for rebalancing (0=Monday)
        lookback_periods: Number of periods needed for indicator calculation
        market: Market calendar to use
        
    Returns:
        DataFrame with columns: rebalance_date, signal_date, data_start_date
    """
    # Get rebalance dates
    rebalance_dates = get_rebalance_dates(start_date, end_date, weekday, market)
    
    calendar = mcal.get_calendar(market)
    
    schedule_data = []
    
    for rebal_date in rebalance_dates:
        # Signal should be calculated using data up to previous trading day
        # to avoid lookahead bias
        prev_day = rebal_date - timedelta(days=1)
        schedule_prev = calendar.schedule(start_date=prev_day, end_date=prev_day)
        
        # If previous day is not a trading day, get the last trading day before it
        if schedule_prev.empty:
            for i in range(2, 11):
                check_date = rebal_date - timedelta(days=i)
                schedule_check = calendar.schedule(start_date=check_date, end_date=check_date)
                if not schedule_check.empty:
                    signal_date = schedule_check.index[0].to_pydatetime()
                    break
        else:
            signal_date = schedule_prev.index[0].to_pydatetime()
        
        # Determine data start date (need enough history for indicator)
        # Get trading days before signal date
        data_end_for_calc = signal_date
        data_start_for_calc = signal_date - timedelta(days=lookback_periods * 2)  # Generous buffer
        
        schedule_data.append({
            'rebalance_date': rebal_date,
            'signal_date': signal_date,
            'data_start_date': data_start_for_calc
        })
    
    schedule_df = pd.DataFrame(schedule_data)
    
    return schedule_df
