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


## 20251101_192835_US_Large_Cap_Double_EMA63d_M_Top1
**Date:** 2025-11-01 19:28:52

**Configuration:**
- Universe: US_Large_Cap
- Momentum: Double_EMA (63d)
- Rebalance: monthly
- Filter: SAFETY_SWITCH (SPY 50/200d SMA)

**Results:**
- CAGR: 8.72%
- Sharpe: 0.64
- Sortino: 0.66
- Calmar: 0.26
- Max DD: -33.68%
- Total Return: 430.63%
- Path: `output\20251101_192835_US_Large_Cap_Double_EMA63d_M_Top1`


## 20251101_193021_US_Large_Cap_Double_EMA63d_M_Top1
**Date:** 2025-11-01 19:30:38

**Configuration:**
- Universe: US_Large_Cap
- Momentum: Double_EMA (63d)
- Rebalance: monthly
- Filter: SAFETY_SWITCH (SPY 50/200d SMA)

**Results:**
- CAGR: 8.72%
- Sharpe: 0.64
- Sortino: 0.66
- Calmar: 0.26
- Max DD: -33.68%
- Total Return: 430.63%
- Path: `output\20251101_193021_US_Large_Cap_Double_EMA63d_M_Top1`


## 20251101_193145_US_Large_Cap_Double_EMA63d_W_Top1
**Date:** 2025-11-01 19:32:28

**Configuration:**
- Universe: US_Large_Cap
- Momentum: Double_EMA (63d)
- Rebalance: weekly
- Filter: SAFETY_SWITCH (SPY 20/50d SMA)

**Results:**
- CAGR: 3.84%
- Sharpe: 0.31
- Sortino: 0.31
- Calmar: 0.12
- Max DD: -32.91%
- Total Return: 112.39%
- Path: `output\20251101_193145_US_Large_Cap_Double_EMA63d_W_Top1`


## 20251101_194017_Developed_Countries_Double_EMA63d_W_Top1
**Date:** 2025-11-01 19:41:34

**Configuration:**
- Universe: Developed_Countries
- Momentum: Double_EMA (63d)
- Rebalance: weekly
- Filter: SAFETY_SWITCH (SPY 20/50d) + 12 safe assets

**Results:**
- CAGR: 7.52%
- Sharpe: 0.44
- Sortino: 0.57
- Calmar: 0.17
- Max DD: -45.52%
- Total Return: 325.68%
- Path: `output\20251101_194017_Developed_Countries_Double_EMA63d_W_Top1`


## 20251101_194703_Developed_Countries_DEMA63d_W_Top1
**Date:** 2025-11-01 19:48:02

**Configuration:**
- Universe: Developed_Countries
- Momentum: DEMA (63d)
- Rebalance: weekly
- Filter: SAFETY_SWITCH (SPY 20/50d) + 12 safe assets

**Results:**
- CAGR: 6.29%
- Sharpe: 0.37
- Sortino: 0.48
- Calmar: 0.13
- Max DD: -48.30%
- Total Return: 237.88%
- Path: `output\20251101_194703_Developed_Countries_DEMA63d_W_Top1`


## 20251101_200838_Developed_Countries_POLYMORPHIC63d_M_Top1
**Date:** 2025-11-01 20:09:09

**Configuration:**
- Universe: Developed_Countries
- Momentum: POLYMORPHIC (63d)
- Rebalance: monthly
- Filter: SAFETY_SWITCH (SPY 50/200d) + 12 safe assets

**Results:**
- CAGR: 6.91%
- Sharpe: 0.41
- Sortino: 0.53
- Calmar: 0.15
- Max DD: -47.25%
- Total Return: 279.52%
- Path: `output\20251101_200838_Developed_Countries_POLYMORPHIC63d_M_Top1`


## 20251101_201106_Developed_Countries_POLYMORPHIC63d_M_Top1
**Date:** 2025-11-01 20:11:35

**Configuration:**
- Universe: Developed_Countries
- Momentum: POLYMORPHIC (63d)
- Rebalance: monthly
- Filter: SAFETY_SWITCH (SPY 50/200d) + 12 safe assets

**Results:**
- CAGR: 2.88%
- Sharpe: 0.19
- Sortino: 0.20
- Calmar: 0.07
- Max DD: -41.37%
- Total Return: 76.36%
- Path: `output\20251101_201106_Developed_Countries_POLYMORPHIC63d_M_Top1`


## 20251101_202032_US_Large_Cap_POLYMORPHIC63d_W_Top1
**Date:** 2025-11-01 20:21:43

**Configuration:**
- Universe: US_Large_Cap
- Momentum: POLYMORPHIC (63d)
- Rebalance: weekly
- Filter: SAFETY_SWITCH (SPY 50/200d) + 12 safe assets

**Results:**
- CAGR: 8.87%
- Sharpe: 0.63
- Sortino: 0.64
- Calmar: 0.24
- Max DD: -36.66%
- Total Return: 446.02%
- Path: `output\20251101_202032_US_Large_Cap_POLYMORPHIC63d_W_Top1`


## 20251101_202804_AI_US_Large_Cap_POLYMORPHIC63d_W_Top1
**Date:** 2025-11-01 20:29:23

**Configuration:**
- Universe: AI_US_Large_Cap
- Momentum: POLYMORPHIC (63d)
- Rebalance: weekly
- Filter: SAFETY_SWITCH (SPY 50/200d) + 12 safe assets

**Results:**
- CAGR: 5.79%
- Sharpe: 0.30
- Sortino: 0.35
- Calmar: 0.17
- Max DD: -35.08%
- Total Return: 135.91%
- Path: `output\20251101_202804_AI_US_Large_Cap_POLYMORPHIC63d_W_Top1`

