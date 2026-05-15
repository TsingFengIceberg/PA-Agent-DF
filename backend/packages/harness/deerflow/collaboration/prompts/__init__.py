"""Role system prompts for Research and Analysis SubGraphs.

Research SubGraph:
    PI Agent: research planning + dispatch + ruling review
    Data Scout: parallel collection + Critic rebuttal
    Critic Agent: adversarial evidence-backed challenge
    Meta-Judge: computation-backed independent adjudication

Analysis SubGraph:
    Analyst Lead: analysis planning + dimension selection + Skill dispatch
    Synthesizer: multi-dimensional analysis + visualization + recommendations
    Internal Reviewer: analysis quality assurance
    Report Composer: final Markdown report generation
"""

from deerflow.collaboration.prompts.analysis_prompts import (
    ANALYST_LEAD_PROMPT,
    INTERNAL_REVIEWER_PROMPT,
    REPORT_COMPOSER_PROMPT,
    SYNTHESIZER_PROMPT,
)
from deerflow.collaboration.prompts.research_prompts import (
    CRITIC_AGENT_PROMPT,
    DATA_SCOUT_PROMPT,
    META_JUDGE_PROMPT,
    PI_AGENT_PROMPT,
)

__all__ = [
    # Research
    "PI_AGENT_PROMPT",
    "DATA_SCOUT_PROMPT",
    "CRITIC_AGENT_PROMPT",
    "META_JUDGE_PROMPT",
    # Analysis
    "ANALYST_LEAD_PROMPT",
    "SYNTHESIZER_PROMPT",
    "INTERNAL_REVIEWER_PROMPT",
    "REPORT_COMPOSER_PROMPT",
]
