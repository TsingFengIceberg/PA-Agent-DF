---
name: price-elasticity
description: Calculate price elasticity of demand using historical pricing and sales data. Use this skill for pricing optimization analysis, demand forecasting, and competitive pricing strategy. Supports both point elasticity and arc elasticity calculations with confidence intervals.
allowed-tools:
  - python

---

# Price Elasticity Skill

## Overview

This skill computes price elasticity of demand — the responsiveness of quantity demanded to price changes. It is essential for pricing optimization, revenue forecasting, and competitive positioning analysis.

## Core Capabilities

- **Point elasticity**: Calculate at specific price points: E = (ΔQ/Q) / (ΔP/P)
- **Arc elasticity**: Midpoint formula for discrete price changes: E = (ΔQ/avg_Q) / (ΔP/avg_P)
- **Cross elasticity**: Measure demand response to competitor price changes
- **Regression analysis**: Fit demand curves using linear and log-linear models
- **Confidence intervals**: Bootstrap-based uncertainty estimation
- **Revenue optimization**: Find revenue-maximizing price point from elasticity curve
- **Segment analysis**: Elasticity by customer segment, region, or channel

## Workflow

### Step 1: Prepare Data

Load historical pricing and quantity data. Minimum requirements: price and quantity time series with at least 10 data points.

```python
import pandas as pd
import numpy as np
from scipy import stats

data = pd.DataFrame({
    "date": [...],
    "price": [...],
    "quantity": [...],
    "competitor_price": [...]  # optional, for cross-elasticity
})
```

### Step 2: Compute Elasticity

```python
# Arc elasticity (preferred for discrete data)
p_avg = (data["price"].iloc[-1] + data["price"].iloc[0]) / 2
q_avg = (data["quantity"].iloc[-1] + data["quantity"].iloc[0]) / 2
delta_p = data["price"].iloc[-1] - data["price"].iloc[0]
delta_q = data["quantity"].iloc[-1] - data["quantity"].iloc[0]

elasticity = (delta_q / q_avg) / (delta_p / p_avg)
```

### Step 3: Interpret and Recommend

| Elasticity | Classification | Pricing Strategy |
|-----------|---------------|------------------|
| \|E\| > 1 | Elastic | Price decrease → revenue increase |
| \|E\| < 1 | Inelastic | Price increase → revenue increase |
| \|E\| = 1 | Unit elastic | Revenue maximized |

## Output Format

```json
{
  "product": "Smart Watch X",
  "elasticity": -1.42,
  "classification": "elastic",
  "confidence_interval": [-1.65, -1.19],
  "cross_elasticity": {
    "competitor_a": 0.35,
    "competitor_b": 0.18
  },
  "revenue_optimal_price": 2699.0,
  "current_price": 2999.0,
  "recommendation": "Decrease price to ¥2699 for ~8% revenue increase",
  "method": "arc_elasticity",
  "data_points": 24,
  "r_squared": 0.87
}
```
