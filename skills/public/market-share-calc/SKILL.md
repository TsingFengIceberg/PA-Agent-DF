---
name: market-share-calc
description: Calculate market share distribution and market concentration metrics from revenue or unit sales data. Use this skill for competitive landscape analysis, market structure assessment, and identifying market leaders vs. fragmented segments.
allowed-tools:
  - python

---

# Market Share Calculator Skill

## Overview

This skill computes market share distributions and market concentration metrics. It transforms raw revenue/unit data into structured market intelligence including share percentages, concentration ratios, Herfindahl-Hirschman Index (HHI), and market structure classification.

## Core Capabilities

- **Market share calculation**: Revenue-based and unit-based share percentages
- **Concentration ratios**: CR4 (top 4) and CR8 (top 8) concentration metrics
- **HHI computation**: Herfindahl-Hirschman Index for regulatory/market structure analysis
- **Market structure classification**: Perfect competition → Monopolistic → Oligopoly → Monopoly
- **Share shift analysis**: Year-over-year share changes to identify gainers and losers
- **Segment breakdown**: Share by price tier, region, or product category

## Market Structure Reference

| HHI Range | Structure | Characteristics |
|-----------|-----------|-----------------|
| < 1500 | Competitive | Many players, low concentration |
| 1500–2500 | Moderately Concentrated | Mid-tier consolidation |
| > 2500 | Highly Concentrated | Few dominant players |

## Workflow

### Step 1: Load and Validate Data

```python
import pandas as pd
import numpy as np

data = pd.DataFrame({
    "company": ["Apple", "Samsung", "Huawei", "Xiaomi", "Others"],
    "revenue": [215, 195, 98, 52, 140],  # in billions
    "units": [235, 272, 150, 185, 450],   # in millions
})
```

### Step 2: Calculate Shares and Concentration

```python
total_revenue = data["revenue"].sum()
data["revenue_share"] = data["revenue"] / total_revenue * 100

# CR4 = sum of top 4 shares
cr4 = data.nlargest(4, "revenue_share")["revenue_share"].sum()

# HHI = sum of squared market shares (0-100 scale → 0-10000)
hhi = sum((s / 100) ** 2 * 10000 for s in data["revenue_share"])
```

### Step 3: Classify and Report

## Output Format

```json
{
  "market": "Global Smartphone 2026 Q1",
  "total_market_size": {"revenue_bn": 700, "units_mn": 1292},
  "shares": [
    {"company": "Apple", "revenue_share": 30.7, "unit_share": 18.2},
    {"company": "Samsung", "revenue_share": 27.9, "unit_share": 21.1},
    {"company": "Huawei", "revenue_share": 14.0, "unit_share": 11.6},
    {"company": "Xiaomi", "revenue_share": 7.4, "unit_share": 14.3}
  ],
  "concentration": {
    "cr4": 80.0,
    "hhi": 1985,
    "structure": "Moderately Concentrated"
  },
  "share_shifts": [
    {"company": "Huawei", "change_pct": 3.2, "direction": "gaining"},
    {"company": "Apple", "change_pct": -1.1, "direction": "losing"}
  ]
}
```
