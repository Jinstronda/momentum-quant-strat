"""Data loading and caching module using yfinance."""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pandas as pd
import yfinance as yf


class DataLoader:
    """Load and cache price data using yfinance."""
    
    def __init__(self, data_dir: str = "data", cache_enabled: bool = True):
        """
        Initialize data loader.
        
        Args:
            data_dir: Directory for caching parquet files
            cache_enabled: Whether to use parquet caching
        """
        self.data_dir = Path(data_dir)
        self.cache_enabled = cache_enabled
        
        if cache_enabled:
            self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        return self.data_dir / f"{symbol}.parquet"
    
    def _load_from_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available."""
        if not self.cache_enabled:
            return None
        
        cache_path = self._get_cache_path(symbol)
        if cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                df.index = pd.to_datetime(df.index).tz_localize(None)
                return df
            except Exception as e:
                print(f"Warning: Failed to load cache for {symbol}: {e}")
                return None
        return None
    
    def _save_to_cache(self, symbol: str, df: pd.DataFrame) -> None:
        """Save data to cache."""
        if not self.cache_enabled:
            return
        
        try:
            cache_path = self._get_cache_path(symbol)
            df.to_parquet(cache_path)
        except Exception as e:
            print(f"Warning: Failed to save cache for {symbol}: {e}")
    
    def fetch_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False,
        include_volume: bool = False
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single symbol.
        
        Args:
            symbol: Ticker symbol
            start_date: Start date for data
            end_date: End date for data
            force_refresh: Force download even if cached
            
        Returns:
            DataFrame with OHLCV data indexed by date
        """
        # Try cache first unless force refresh
        if not force_refresh:
            cached_df = self._load_from_cache(symbol)
            if cached_df is not None:
                # Ensure cache index is timezone-naive for comparison
                if cached_df.index.tz is not None:
                    cached_df.index = cached_df.index.tz_localize(None)
                
                # Filter to requested date range
                mask = (cached_df.index >= start_date) & (cached_df.index <= end_date)
                filtered = cached_df[mask]
                
                # If we have enough data in cache, use it
                if not filtered.empty and filtered.index.min() <= start_date:
                    return filtered
        
        # Download from yfinance
        print(f"Downloading {symbol} from {start_date.date()} to {end_date.date()}...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                auto_adjust=True,  # Use adjusted prices
                actions=False       # Don't need dividends/splits
            )
            
            if df.empty:
                raise ValueError(f"No data returned for {symbol}")
            
            # Keep only OHLCV columns
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.index.name = 'Date'
            
            # Convert timezone-aware index to timezone-naive
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # Save to cache
            self._save_to_cache(symbol, df)
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to fetch {symbol}: {e}")
    
    def fetch_universe(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Fetch data for multiple symbols and return as wide DataFrame.
        
        Args:
            symbols: List of ticker symbols
            start_date: Start date for data
            end_date: End date for data
            force_refresh: Force download even if cached
            
        Returns:
            DataFrame with multi-level columns (symbol, field) indexed by date
        """
        all_data = {}
        
        for symbol in symbols:
            try:
                df = self.fetch_symbol(symbol, start_date, end_date, force_refresh)
                all_data[symbol] = df
            except Exception as e:
                print(f"Warning: Skipping {symbol} due to error: {e}")
                continue
        
        if not all_data:
            raise ValueError("No data could be fetched for any symbol")
        
        # Combine into multi-level DataFrame
        combined = pd.concat(all_data, axis=1, keys=all_data.keys())
        combined.sort_index(inplace=True)
        
        # Forward fill missing data (e.g., for holidays)
        combined = combined.ffill()
        
        return combined
    
    def get_close_prices(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Get only close prices for multiple symbols.
        
        Args:
            symbols: List of ticker symbols
            start_date: Start date for data
            end_date: End date for data
            force_refresh: Force download even if cached
            
        Returns:
            DataFrame with symbols as columns, dates as index
        """
        universe_data = self.fetch_universe(symbols, start_date, end_date, force_refresh)
        
        # Extract close prices
        close_prices = pd.DataFrame()
        for symbol in symbols:
            if (symbol, 'Close') in universe_data.columns:
                close_prices[symbol] = universe_data[(symbol, 'Close')]
        
        return close_prices
    
    def get_symbol_with_volume(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        force_refresh: bool = False
    ) -> tuple:
        """
        Get close prices and volume for a single symbol.
        
        Used for StormGuard filter components (SPY, VIX).
        
        Args:
            symbol: Ticker symbol
            start_date: Start date for data
            end_date: End date for data
            force_refresh: Force download even if cached
            
        Returns:
            Tuple of (close_prices: pd.Series, volume: pd.Series)
        """
        df = self.fetch_symbol(symbol, start_date, end_date, force_refresh)
        return df['Close'], df['Volume']
