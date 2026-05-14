"""Role system prompts for Research SubGraph.

PI Agent: research planning + dispatch + ruling review
Data Scout: parallel collection + Critic rebuttal
Critic Agent: adversarial evidence-backed challenge
Meta-Judge: computation-backed independent adjudication
"""

from deerflow.collaboration.prompts.research_prompts import (
    CRITIC_AGENT_PROMPT,
    DATA_SCOUT_PROMPT,
    META_JUDGE_PROMPT,
    PI_AGENT_PROMPT,
)

__all__ = [
    "PI_AGENT_PROMPT",
    "DATA_SCOUT_PROMPT",
    "CRITIC_AGENT_PROMPT",
    "META_JUDGE_PROMPT",
]
