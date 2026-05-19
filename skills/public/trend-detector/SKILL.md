---
name: trend-detector
description: Detect and analyze trends in time-series market data. Use this skill to identify emerging patterns, seasonal effects, growth trajectories, and inflection points. Supports moving averages, exponential smoothing, linear regression, and decomposition.
allowed-tools:
  - python

---

# Trend Detector Skill

## Overview

This skill provides statistical trend detection and analysis for time-series market data. It identifies directional movements, seasonal patterns, growth rates, and inflection points — separating signal from noise in market intelligence data.

## Core Capabilities

- **Moving averages**: Simple (SMA), exponential (EMA), and weighted (WMA) smoothing
- **Trend decomposition**: Decompose into trend + seasonal + residual components
- **Growth rate analysis**: CAGR, period-over-period, and sequential growth
- **Inflection point detection**: Identify statistically significant trend changes
- **Seasonality detection**: Auto-detect seasonal patterns (weekly, monthly, quarterly)
- **Forecast projection**: Simple trend extrapolation with confidence bands
- **Correlation analysis**: Detect leading/lagging relationships between series

## Workflow

### Step 1: Prepare Time Series

```python
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose

data = pd.DataFrame({
    "date": pd.date_range("2024-01", periods=24, freq="ME"),
    "sales": [...],
    "search_interest": [...],
    "competitor_launches": [...],
})
data.set_index("date", inplace=True)
```

### Step 2: Decompose and Detect

```python
# Decomposition
result = seasonal_decompose(data["sales"], model="multiplicative", period=12)
trend = result.trend
seasonal = result.seasonal
residual = result.resid

# CAGR
n_years = len(data) / 12
cagr = (data["sales"].iloc[-1] / data["sales"].iloc[0]) ** (1 / n_years) - 1

# Linear trend test (Mann-Kendall)
from pymannkendall import original_test
mk_result = original_test(data["sales"])
```

### Step 3: Interpret Results

Classify trends as:
- **Strong uptrend**: Positive slope, p < 0.01, CAGR > 10%
- **Moderate uptrend**: Positive slope, p < 0.05
- **Stable/Flat**: p > 0.05
- **Downtrend**: Negative slope, p < 0.05

## Output Format

```json
{
  "series": "NEV Sales China",
  "period": "2024-01 to 2026-01",
  "trend": {
    "direction": "strong_uptrend",
    "cagr_pct": 28.5,
    "mann_kendall_p": 0.0003,
    "slope": 12500,
    "slope_unit": "units/month"
  },
  "seasonality": {
    "detected": true,
    "period": 12,
    "peak_months": [3, 9],
    "trough_months": [1, 7]
  },
  "inflection_points": [
    {"date": "2025-06", "type": "acceleration", "confidence": 0.92}
  ],
  "forecast_6m": {
    "point_estimate": 285000,
    "ci_lower": 265000,
    "ci_upper": 305000
  }
}
```
