---
name: swot-generator
description: Generate structured SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis from validated research data. Use this skill as the final synthesis step in competitive analysis to produce an evidence-backed strategic assessment with actionable recommendations.
allowed-tools:
  - python
  - write_file

---

# SWOT Generator Skill

## Overview

This skill produces evidence-backed SWOT analyses from validated research data. Unlike generic SWOT generators that rely on LLM general knowledge, this skill requires structured research input and ties every quadrant entry to specific data points with source attribution.

## Core Capabilities

- **Evidence-grounded quadrants**: Every SWOT entry must cite at least one data point from research
- **Weighted prioritization**: Rank entries by impact and confidence
- **Cross-quadrant linkage**: Connect Strengths→Opportunities (leverage) and Weaknesses→Threats (vulnerabilities)
- **Strategic recommendations**: Generate TOWS matrix (SO, WO, ST, WT strategies)
- **Markdown export**: Produce publication-ready SWOT report with tables and charts

## SWOT Framework

### Strengths (Internal, Positive)
- What advantages does the product/company have?
- What unique resources or capabilities?
- What do competitors and customers see as strengths?
- **Requirement**: Each strength backed by spec comparison or market data

### Weaknesses (Internal, Negative)
- What disadvantages or gaps exist?
- What do competitors do better?
- What resource limitations exist?
- **Requirement**: Each weakness backed by gap analysis or benchmark data

### Opportunities (External, Positive)
- What market trends can be exploited?
- What competitor weaknesses create openings?
- What technology or regulatory changes are favorable?
- **Requirement**: Each opportunity backed by trend analysis or market data

### Threats (External, Negative)
- What competitive moves threaten position?
- What market shifts create risk?
- What regulatory or supply chain risks exist?
- **Requirement**: Each threat backed by market intelligence or trend data

## Workflow

### Step 1: Ingest Research Data

Load validated_brief, comparison matrices, trend analysis, and market share data.

### Step 2: Generate SWOT Entries

For each quadrant, extract and rank entries from the research data. Assign impact (1-5) and confidence (0-1) scores.

### Step 3: Build TOWS Matrix

Map strategic options:
- **SO Strategies**: Use strengths to capture opportunities
- **WO Strategies**: Overcome weaknesses to pursue opportunities
- **ST Strategies**: Use strengths to mitigate threats
- **WT Strategies**: Minimize weaknesses to avoid threats

### Step 4: Generate Report

Produce a Markdown report with SWOT table, TOWS strategies, and an executive summary.

## Output Format

```json
{
  "subject": "iPhone 17 Competitive Position",
  "generated_at": "2026-05-19T10:00:00Z",
  "quadrants": {
    "strengths": [
      {
        "entry": "Industry-leading A19 processor performance",
        "impact": 5,
        "confidence": 0.95,
        "evidence": ["Geekbench: +18% vs Snapdragon 8 Gen 4", "Source: anandtech.com"]
      }
    ],
    "weaknesses": [
      {
        "entry": "Battery capacity 15-20% smaller than Android flagships",
        "impact": 4,
        "confidence": 0.92,
        "evidence": ["4000mAh vs 5000mAh (S25 Ultra)", "Source: gsmarena.com"]
      }
    ],
    "opportunities": [
      {
        "entry": "NEV market integration — Apple CarPlay dominance in EV dashboards",
        "impact": 4,
        "confidence": 0.70,
        "evidence": ["78% EV buyers consider CarPlay mandatory", "Source: consumer survey n=1200"]
      }
    ],
    "threats": [
      {
        "entry": "Huawei HarmonyOS ecosystem lock-in in China market",
        "impact": 4,
        "confidence": 0.85,
        "evidence": ["Huawei domestic share +3.2pp YoY", "Source: IDC Q1 2026"]
      }
    ]
  },
  "tows_strategies": {
    "so": ["Leverage processor lead to position as AI-capable device for NEV integration"],
    "wo": ["Invest in battery density R&D partnership to close gap within 2 generations"],
    "st": ["Double down on iOS ecosystem stickiness to counter HarmonyOS lock-in"],
    "wt": ["Develop China-specific pricing strategy acknowledging domestic brand advantage"]
  },
  "overall_confidence": 0.87
}
```
