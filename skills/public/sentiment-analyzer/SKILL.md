---
name: sentiment-analyzer
description: Analyze sentiment in product reviews, news articles, and social media commentary. Use this skill when research involves consumer perception, brand reputation, or market sentiment toward products/companies. Supports multi-source aggregation and trend-over-time analysis.
allowed-tools:
  - python

---

# Sentiment Analyzer Skill

## Overview

This skill analyzes textual sentiment from product reviews, news articles, and social media to quantify consumer and market perception. It produces structured sentiment scores, key theme extraction, and temporal sentiment trends.

## Core Capabilities

- **Polarity scoring**: Positive/negative/neutral classification with confidence scores
- **Aspect-based sentiment**: Sentiment broken down by product feature (battery, camera, price, etc.)
- **Theme extraction**: Identify recurring topics and their associated sentiment
- **Temporal trends**: Track sentiment shifts over time
- **Multi-source aggregation**: Combine and compare sentiment across platforms (Twitter, Reddit, reviews, news)
- **Language detection**: Handle multilingual input

## Workflow

### Step 1: Load and Preprocess Text Data

```python
import pandas as pd

texts = load_text_corpus([
    "/mnt/user-data/workspace/reviews.json",
    "/mnt/user-data/workspace/news_articles.json",
])

# Clean and normalize
texts = [clean_text(t) for t in texts]
```

### Step 2: Analyze Sentiment

Run sentiment analysis on the corpus. Use lexicon-based methods for speed on large corpora, or ML-based for nuanced analysis on smaller sets.

### Step 3: Aggregate and Report

Group results by source, aspect, and time period. Generate summary statistics:
- Overall sentiment score (-1.0 to 1.0)
- Per-aspect breakdown
- Top positive and negative themes
- Sentiment volatility over time

## Output Format

```json
{
  "overall_sentiment": 0.32,
  "confidence": 0.85,
  "aspect_breakdown": {
    "battery": {"score": 0.6, "mentions": 45},
    "camera": {"score": 0.8, "mentions": 67},
    "price": {"score": -0.3, "mentions": 89}
  },
  "top_positive_themes": ["camera quality", "battery life"],
  "top_negative_themes": ["price point", "heating issues"],
  "temporal_trend": [
    {"date": "2026-01", "score": 0.2},
    {"date": "2026-02", "score": 0.35}
  ],
  "sources_analyzed": 3,
  "total_texts_processed": 520
}
```
