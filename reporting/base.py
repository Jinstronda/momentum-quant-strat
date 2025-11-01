"""Base reporter class with initialization and data saving methods."""

from pathlib import Path
from typing import Dict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class BaseReporter:
    """Base class for backtest reporting with data saving methods."""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize reporter with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set plotting style
        sns.set_style("darkgrid")
        plt.rcParams['figure.figsize'] = (12, 6)
    
    def save_metrics(
        self,
        metrics: Dict[str, float],
        filename: str = "metrics.csv"
    ) -> None:
        """Save performance metrics to CSV."""
        metrics_df = pd.DataFrame([metrics]).T
        metrics_df.columns = ['Value']
        
        output_path = self.output_dir / filename
        metrics_df.to_csv(output_path)
        print(f"Metrics saved to {output_path}")
    
    def save_trades(
        self,
        trades: pd.DataFrame,
        filename: str = "trades.csv"
    ) -> None:
        """Save trade log to CSV."""
        if trades.empty:
            print("No trades to save")
            return
        
        output_path = self.output_dir / filename
        trades.to_csv(output_path, index=False)
        print(f"Trades saved to {output_path}")
    
    def save_equity_curve(
        self,
        equity_curve: pd.DataFrame,
        filename: str = "equity_curve.csv"
    ) -> None:
        """Save equity curve to CSV."""
        output_path = self.output_dir / filename
        equity_curve.to_csv(output_path)
        print(f"Equity curve saved to {output_path}")
    
    def save_filter_history(
        self,
        filter_history: pd.DataFrame,
        filename: str = "filter_history.csv"
    ) -> None:
        """Save polymorphic filter history to CSV."""
        if filter_history is None or filter_history.empty:
            print("No filter history to save (not using polymorphic momentum)")
            return
        
        output_path = self.output_dir / filename
        filter_history.to_csv(output_path, index=False)
        print(f"Filter history saved to {output_path}")

