---
name: spec-comparator
description: Compare product specifications across competitors and generate structured comparison matrices. Use this skill when research requires side-by-side product analysis, feature gap identification, or competitive positioning based on technical specifications.
allowed-tools:
  - python
  - read_file
  - write_file

---

# Spec Comparator Skill

## Overview

This skill generates structured product specification comparisons from multi-source research data. It normalizes specs across different naming conventions, identifies feature gaps, and produces comparison matrices suitable for competitive analysis reports.

## Core Capabilities

- **Spec normalization**: Map different naming conventions to a common spec taxonomy (e.g., "screen size" vs "display" vs "panel size")
- **Unit standardization**: Convert all measurements to consistent units
- **Gap analysis**: Identify features present in competitors but missing in the target product
- **Advantage quantification**: Compute spec superiority scores (e.g., "Camera MP: +20% vs category average")
- **Matrix generation**: Produce structured comparison tables in Markdown and JSON
- **Category grouping**: Organize specs into logical groups (display, performance, camera, battery, etc.)

## Workflow

### Step 1: Define Comparison Scope

Identify the products and spec categories to compare:

```python
products = ["iPhone 17", "Huawei Mate 70 Pro", "Samsung S25 Ultra"]
categories = ["display", "processor", "camera", "battery", "storage", "price"]
```

### Step 2: Normalize Specifications

Load raw spec data and normalize across naming conventions and units:

```python
normalized = normalize_specs(raw_data, taxonomy=SPEC_TAXONOMY)
# "6.7 inches" and "17.0 cm" → both become 17.02 cm
# "5000mAh" and "5Ah" → both become 5000mAh
```

### Step 3: Generate Comparison Matrix

Compute per-category advantage scores and generate the final matrix. Highlight significant advantages (>15% difference) and parity zones (<5% difference).

## Output Format

```json
{
  "products": ["iPhone 17", "Huawei Mate 70 Pro", "Samsung S25 Ultra"],
  "categories": ["display", "camera", "battery", "price"],
  "matrix": [
    {
      "spec": "Screen Size",
      "category": "display",
      "unit": "inch",
      "values": {"iPhone 17": 6.3, "Huawei Mate 70 Pro": 6.82, "Samsung S25 Ultra": 6.9},
      "winner": "Huawei Mate 70 Pro",
      "advantage_pct": 8.3
    }
  ],
  "gap_analysis": {
    "iPhone 17": {"missing": ["periscope zoom"], "advantages": ["processor efficiency"]},
    "Huawei Mate 70 Pro": {"missing": [], "advantages": ["battery capacity", "screen size"]},
    "Samsung S25 Ultra": {"missing": [], "advantages": ["S Pen", "update policy"]}
  },
  "overall_rankings": [
    {"rank": 1, "product": "Samsung S25 Ultra", "score": 92},
    {"rank": 2, "product": "Huawei Mate 70 Pro", "score": 89},
    {"rank": 3, "product": "iPhone 17", "score": 85}
  ]
}
```
