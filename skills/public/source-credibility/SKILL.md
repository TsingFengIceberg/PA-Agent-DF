---
name: source-credibility
description: Evaluate the credibility of data sources used in research. Use this skill during evidence review and cross-validation phases to assess source authority, recency, corroboration, and potential bias. Critical for adversarial critique workflows where claims must be backed by verified sources.
allowed-tools:
  - python
  - read_file

---

# Source Credibility Skill

## Overview

This skill provides a systematic methodology for evaluating the credibility of information sources. It is designed for adversarial review contexts where every data point must be traceable to a reliable source. The skill computes a credibility score based on multiple dimensions and flags sources that fail to meet quality thresholds.

## Core Capabilities

- **Authority scoring**: Evaluate domain expertise, publisher reputation, author credentials
- **Recency check**: Verify data timeliness against a configurable freshness window
- **Corroboration**: Cross-reference claims across independent sources
- **Bias detection**: Identify potential conflicts of interest, funding sources, editorial stance
- **Methodology audit**: Assess data collection methods, sample sizes, statistical rigor
- **Contradiction flagging**: Detect when sources directly contradict each other

## Credibility Dimensions

Each source is scored on 5 dimensions (0.0–1.0):

| Dimension | Weight | Criteria |
|-----------|--------|----------|
| Authority | 0.25 | Publisher reputation, author expertise |
| Accuracy | 0.30 | Cross-referenced claims, factual consistency |
| Recency | 0.15 | Publication date vs. freshness requirement |
| Objectivity | 0.15 | Bias indicators, commercial interest, funding |
| Methodology | 0.15 | Sample size, data collection method, peer review |

## Workflow

### Step 1: Extract Source Metadata

For each source cited in research data, extract:
- URL/domain, publisher, author
- Publication/update date
- Cited claims and evidence
- Data collection methodology (if stated)

### Step 2: Score Each Dimension

```python
credibility_scores = []
for source in sources:
    scores = {
        "source_id": source["id"],
        "authority": score_authority(source),
        "accuracy": score_accuracy(source, all_sources),  # cross-reference
        "recency": score_recency(source, freshness_days=365),
        "objectivity": score_objectivity(source),
        "methodology": score_methodology(source),
    }
    scores["composite"] = compute_weighted_score(scores)
    credibility_scores.append(scores)
```

### Step 3: Flag and Report

Sources with composite score below 0.4 are flagged as unreliable. Sources scoring 0.4–0.6 are marked as "use with caution." Flag contradictions between sources for Meta-Judge review.

## Output Format

```json
{
  "sources_evaluated": 5,
  "credibility_scores": [
    {
      "source_id": "src_1",
      "url": "https://example.com/report",
      "composite": 0.82,
      "authority": 0.9,
      "accuracy": 0.85,
      "recency": 0.7,
      "objectivity": 0.8,
      "methodology": 0.85,
      "verdict": "reliable"
    }
  ],
  "contradictions": [
    {
      "claim": "iPhone 17 battery is 4000mAh",
      "source_a": "src_2",
      "source_b": "src_4",
      "resolution_note": "Different regional variants"
    }
  ],
  "overall_credibility": 0.76
}
```
