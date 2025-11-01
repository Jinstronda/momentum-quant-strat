# 1 - Large Cap 2005 - 2025. Only ROC
,Value
Initial Capital,100000.0
Final Equity,134876.91259069898
Total Return (%),34.876912590698986
CAGR (%),1.5096218019274854
Volatility (%),25.934077016191786
Sharpe Ratio,0.05820996833567518
Max Drawdown (%),-68.45710363054948
Calmar Ratio,0.02205208403315804
Win Rate (%),51.8982309679984
Avg Win (%),1.0499091930037192
Avg Loss (%),-1.120423315322499
Total Trades,5032.0
Very bad compared to the SPY

# 2 - Large Cap 2005 to 2025 using Moving Average of 20 days and 50 days with derivative of 1 day
Very bad
Value
Initial Capital,100000.0
Final Equity,59479.90710864931
Total Return (%),-40.52009289135069
CAGR (%),-2.568233088658889
Volatility (%),17.803430996936548
Sharpe Ratio,-0.144254952267392
Max Drawdown (%),-66.76602181147253
Calmar Ratio,0.038466169152788804
Win Rate (%),39.81315841780958
Avg Win (%),0.860776566622927
Avg Loss (%),-0.9094651429398344
Total Trades,5032.0

# 3 - Large Cap 2005 to 2025 using 20/50 EMA with derivative of 10 days
Testing longer derivative lookback to reduce whipsaws

---

## How to Test Different Configurations

### Momentum Indicators

Edit `src/config.py` to choose momentum type and period:

```python
# Rate of Change (most responsive, high turnover)
MOMENTUM_TYPE = "ROC"
MOMENTUM_PERIOD = 63  # 3-month

# Double EMA - EMA(EMA) (smoothest, slow, low turnover)
MOMENTUM_TYPE = "Double_EMA"
MOMENTUM_PERIOD = 126  # 6-month for major trends

# DEMA - Technical (2*EMA - EMA(EMA)) (balanced)
MOMENTUM_TYPE = "DEMA"  
MOMENTUM_PERIOD = 63  # 3-month
```

### Rebalancing Frequency

```python
# Weekly rebalancing (every Monday)
REBALANCE_FREQUENCY = "weekly"
REBALANCE_WEEKDAY = 0  # 0=Monday

# Monthly rebalancing (first trading day of month)
REBALANCE_FREQUENCY = "monthly"
```

Then run: `conda deactivate; uv run python main.py`

Each run creates a timestamped folder with the configuration in the name (e.g., `ROC63d_W` or `DEMA21d_M`).


## 20251101_191246_US_Large_Cap_Double_EMA63d_W_Top1
**Date:** 2025-11-01 19:13:41

**Configuration:**
- Universe: US_Large_Cap
- Momentum: Double_EMA (63d)
- Rebalance: weekly
- EMA Filter: ON (20/50/10d)

**Results:**
- CAGR: 4.23%
- Sharpe: 0.32
- Max DD: -34.73%
- Total Return: 128.84%
- Path: `output\20251101_191246_US_Large_Cap_Double_EMA63d_W_Top1`


## 20251101_191744_US_Large_Cap_Double_EMA63d_M_Top1
**Date:** 2025-11-01 19:18:04

**Configuration:**
- Universe: US_Large_Cap
- Momentum: Double_EMA (63d)
- Rebalance: monthly
- EMA Filter: ON (20/50/10d)

**Results:**
- CAGR: 3.59%
- Sharpe: 0.25
- Sortino: 0.27
- Calmar: 0.08
- Max DD: -46.80%
- Total Return: 102.14%
- Path: `output\20251101_191744_US_Large_Cap_Double_EMA63d_M_Top1`

