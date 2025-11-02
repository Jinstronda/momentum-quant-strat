# How to Add New Price Action Filters

The architecture is designed to make adding new filters trivial. Here's the complete process.

## Example: Adding "EMA20_DEFENDED" Filter

This filter checks that Low touched EMA(20) AND the bar closed in the upper 50% of its range (buyers defended support).

### Step 1: Add Filter Function to `indicators.py`

```python
def check_ema20_defended_entry(
    symbol: str,
    prices_ohlc: pd.DataFrame,
    signal_date,
    lookback_days: int = 21,
    relative_close_threshold: float = 0.5
) -> bool:
    """
    Enhanced filter: Low ≤ EMA(20) AND closed in upper half of range.
    
    RelativeClose = (Close - Low) / (High - Low)
    """
    # Get OHLC data
    close_prices = prices_ohlc[(symbol, 'Close')]
    high_prices = prices_ohlc[(symbol, 'High')]
    low_prices = prices_ohlc[(symbol, 'Low')]
    
    # Filter to signal date
    close_up_to_date = close_prices[close_prices.index <= signal_date]
    high_up_to_date = high_prices[high_prices.index <= signal_date]
    low_up_to_date = low_prices[low_prices.index <= signal_date]
    
    # Calculate EMA(20)
    ema20 = close_up_to_date.ewm(span=20, adjust=False, min_periods=20).mean()
    
    # Calculate RelativeClose
    range_size = high_up_to_date - low_up_to_date
    range_size = range_size.replace(0, 0.001)
    relative_close = (close_up_to_date - low_up_to_date) / range_size
    
    # Check lookback window
    lookback_start = signal_date - pd.Timedelta(days=lookback_days * 2)
    
    for date in common_dates:
        low_touched = low_lookback.loc[date] <= ema20_lookback.loc[date]
        closed_strong = relative_close_lookback.loc[date] > relative_close_threshold
        
        if low_touched and closed_strong:
            return True
    
    return False
```

**Key pattern**: Always check data exists, calculate indicator, check condition, return bool.

### Step 2: Import in `strategy.py`

```python
from src.indicators import (
    # ... existing imports
    check_ema20_defended_entry,  # Add your new filter
)
```

### Step 3: Add to Filter Dispatcher in `strategy.py`

In the `_apply_entry_filters()` method:

```python
if self.price_action_filter_type == "EMA20_LOW":
    passes_filter = check_ema20_low_entry(...)
elif self.price_action_filter_type == "EMA20_DEFENDED":  # Add your filter
    passes_filter = check_ema20_defended_entry(
        candidate, prices_ohlc, signal_date,
        self.price_action_lookback_days,
        self.price_action_relative_close_threshold  # Any custom params
    )
```

### Step 4: Add Configuration in `config.py`

```python
PRICE_ACTION_FILTER_TYPE = "EMA20_DEFENDED"  # Add to options
PRICE_ACTION_RELATIVE_CLOSE_THRESHOLD = 0.5  # Any new parameters
```

Export in `get_config()`:
```python
"price_action_filter_type": PRICE_ACTION_FILTER_TYPE,
"price_action_relative_close_threshold": PRICE_ACTION_RELATIVE_CLOSE_THRESHOLD,
```

### Step 5: Add Strategy Parameter

In `MomentumStrategy.__init__()`:

```python
def __init__(
    self,
    # ... existing params
    price_action_relative_close_threshold: float = 0.5,  # Add param
):
    # Store it
    self.price_action_relative_close_threshold = price_action_relative_close_threshold
```

### Step 6: Update `backtest_utils.py`

In `create_strategy_from_config()`:

```python
return MomentumStrategy(
    # ... existing params
    price_action_relative_close_threshold=config.get('price_action_relative_close_threshold', 0.5),
)
```

### Step 7: Update README

Add documentation explaining the new filter.

## That's It!

**Total work**: ~50 lines across 5 files. The architecture handles the rest automatically.

---

## More Filter Ideas

### RSI Oversold
```python
def check_rsi_oversold_entry(symbol, prices_ohlc, signal_date, lookback_days=21, rsi_threshold=30):
    # Calculate RSI
    # Check if RSI < 30 in last N days
    # Return bool
```

### Volume Spike Confirmation
```python
def check_volume_spike_entry(symbol, prices_ohlc, signal_date, volume_multiplier=1.5):
    # Check if volume > 1.5x average when touching EMA
    # Confirms institutional interest
```

### Breakout Retest
```python
def check_breakout_retest_entry(symbol, prices_ohlc, signal_date, lookback_days=21):
    # Find recent breakout above resistance
    # Check if price retested breakout level (now support)
```

### Composite Filter
```python
def check_strong_entry_composite(symbol, prices_ohlc, signal_date):
    # Combine multiple conditions:
    # - Low touched EMA(20)
    # - Closed in upper 75% of range
    # - Volume > average
    # - RSI > 40 (not oversold, but healthy pullback)
```

## Template for New Filters

```python
def check_YOUR_FILTER_NAME(
    symbol: str,
    prices_ohlc: pd.DataFrame,
    signal_date,
    lookback_days: int = 21,
    # your custom params
) -> bool:
    """
    Brief description of what this checks.
    
    Args:
        symbol: Symbol to check
        prices_ohlc: OHLC data with multi-level columns
        signal_date: Date to evaluate
        lookback_days: Lookback window
        # your params
        
    Returns:
        True if entry conditions met, False otherwise
    """
    # 1. Validate data exists
    if symbol not in prices_ohlc.columns.get_level_values(0):
        return False
    
    # 2. Extract needed price data
    close = prices_ohlc[(symbol, 'Close')]
    # ... get High, Low, Volume if needed
    
    # 3. Filter to signal_date
    close_up_to_date = close[close.index <= signal_date]
    
    # 4. Check data sufficiency
    if len(close_up_to_date) < minimum_required:
        return False
    
    # 5. Calculate your indicator
    indicator = calculate_something(close_up_to_date)
    
    # 6. Check condition in lookback window
    lookback_start = signal_date - pd.Timedelta(days=lookback_days * 2)
    indicator_lookback = indicator[indicator.index >= lookback_start]
    
    # 7. Find if ANY day met your condition
    for date in indicator_lookback.index:
        if your_condition_here:
            return True
    
    return False
```

## Testing Your Filter

```python
# In tests/test_price_action_filters.py

def test_your_filter():
    # Create sample OHLC data
    dates = pd.date_range('2020-01-01', periods=100)
    data = {
        ('SPY', 'Close'): np.random.randn(100).cumsum() + 100,
        ('SPY', 'High'): ...,
        ('SPY', 'Low'): ...,
    }
    prices_ohlc = pd.DataFrame(data, index=dates)
    
    # Test passing case
    result = check_your_filter('SPY', prices_ohlc, dates[-1])
    assert result == True  # or False depending on test case
```

## Adding to Documentation

Update README.md under "Price Action Entry Filter" section to document:
- What the filter checks
- When to use it vs. other filters
- Expected impact on results
- Configuration example

---

**Key principle**: Filters are pure functions. They take data, return a boolean. No side effects, no state. Easy to test, easy to combine.

