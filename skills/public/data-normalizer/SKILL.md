---
name: data-normalizer
description: Normalize data from heterogeneous sources (web pages, PDFs, CSV, JSON APIs) into a unified tabular format. Use this skill whenever scout-collected data from multiple sources needs to be standardized before cross-validation or analysis. Handles unit conversion, date format normalization, schema alignment, and missing value imputation.
allowed-tools:
  - python

---

# Data Normalizer Skill

## Overview

This skill normalizes raw data collected from diverse sources into a consistent, analysis-ready tabular format. Multi-source research inevitably produces data in different shapes, units, and schemas — this skill bridges those gaps.

## Core Capabilities

- **Unit normalization**: Convert between imperial/metric, currencies, percentages
- **Date/time standardization**: Parse and normalize to ISO 8601
- **Schema alignment**: Map heterogeneous fields to a common schema
- **Missing value handling**: Flag and impute missing data points
- **Deduplication**: Identify and merge duplicate records across sources
- **Type coercion**: Ensure consistent dtypes (numeric, string, datetime)

## Workflow

### Step 1: Identify Sources and Target Schema

Define the target schema that all sources should conform to:

```python
import pandas as pd

target_schema = {
    "product_name": "string",
    "price": "float",
    "currency": "string",
    "source": "string",
    "collected_at": "datetime",
    "specs": "dict",
}
```

### Step 2: Load and Inspect Each Source

```python
sources = [
    {"name": "web_scrape", "path": "/mnt/user-data/workspace/raw_scrape.json"},
    {"name": "csv_export", "path": "/mnt/user-data/uploads/pricing.csv"},
]

dataframes = []
for src in sources:
    df = load_source(src["path"])
    print(f"Source {src['name']}: {df.shape}, columns={list(df.columns)}")
    dataframes.append(df)
```

### Step 3: Normalize and Merge

Apply unit conversion and schema alignment, then merge into a single clean DataFrame. Flag any data points that couldn't be normalized for manual review.

## Output Format

Return normalized data as a JSON-serializable dict:

```json
{
  "normalized_data": [...],
  "schema": {...},
  "normalization_log": {
    "sources_processed": 3,
    "rows_normalized": 120,
    "rows_flagged": 5,
    "unit_conversions": ["USD→CNY", "inch→mm"],
    "issues": ["missing price for 3 products"]
  }
}
```
