"""Adversarial critique debate state machine.

ClawdLab 核心协议：Critic（检察官）质疑 → Scout（执行者）补采 → Judge（法官）裁决
最多 2 轮质疑-补采循环，不可修复的数据标记为 unresolved_issues。

状态机:
  IDLE → CRITIQUING → [needs_rebuttal?] → REBUTTAL → CRITIQUING (round+1)
                    → [no_issues / max_rounds] → ADJUDICATING → COMPLETE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deerflow.collaboration.protocols.messages import Challenge, Rebuttal, Ruling


class DebatePhase(str, Enum):
    """对抗式批判的四个阶段。"""
    IDLE = "idle"                # 初始状态
    CRITIQUING = "critiquing"    # Critic 审查 scout_results
    REBUTTAL = "rebuttal"        # Scout 定向补采
    ADJUDICATING = "adjudicating"  # Meta-Judge 独立裁决
    COMPLETE = "complete"        # 批判流程结束


MAX_DEBATE_ROUNDS = 2
"""最多 2 轮质疑-补采循环。超过 2 轮未解决的问题标记为 unresolved。"""


@dataclass
class DebateState:
    """对抗式批判状态机。

    挂载在 ResearchSubGraphState.debate_round 和
    ResearchSubGraphState.challenges/rebuttals 之上。
    状态变更逻辑由这个类封装，保持节点函数简洁。
    """

    phase: DebatePhase = DebatePhase.IDLE
    current_round: int = 0
    challenges: list[Challenge] = field(default_factory=list)
    rebuttals: list[Rebuttal] = field(default_factory=list)

    @property
    def can_continue(self) -> bool:
        """是否可以再一轮。"""
        return self.current_round < MAX_DEBATE_ROUNDS

    @property
    def has_challenges(self) -> bool:
        """是否有待解决的质疑。"""
        return len(self.challenges) > 0

    def needs_rebuttal(self) -> bool:
        """是否还有未回应的挑战——触发补采阶段。"""
        if not self.challenges:
            return False
        if not self.can_continue:
            return False
        challenged_ids = {c.challenge_id for c in self.challenges}
        rebutted_ids = {r.challenge_id for r in self.rebuttals}
        return bool(challenged_ids - rebutted_ids)

    def advance_to_critique(self, challenges: list[Challenge]) -> list[Challenge]:
        """进入质疑阶段。

        Returns:
            需要被补采的 challenges（排除已回应且不严重的）。

        Raises:
            ValueError: 如果已超过最大轮次。
        """
        if not self.can_continue:
            raise ValueError(f"已达最大轮次 {MAX_DEBATE_ROUNDS}，不能继续质疑")
        self.phase = DebatePhase.CRITIQUING
        self.current_round += 1
        self.challenges = challenges
        return [c for c in challenges if c.severity != "minor"]

    def advance_to_rebuttal(self, rebuttals: list[Rebuttal]) -> None:
        """进入补采阶段，记录 Scout 回应。"""
        self.phase = DebatePhase.REBUTTAL
        self.rebuttals.extend(rebuttals)

    def advance_to_adjudication(self) -> int:
        """进入裁决阶段。

        Returns:
            仍未解决的质疑数量。
        """
        self.phase = DebatePhase.ADJUDICATING
        rebutted_ids = {r.challenge_id for r in self.rebuttals}
        return sum(1 for c in self.challenges if c.challenge_id not in rebutted_ids)

    def complete(self, ruling: Ruling) -> int:
        """完成批判流程。

        Returns:
            遗留未解决问题的数量（来自 ruling.unresolved）。
        """
        self.phase = DebatePhase.COMPLETE
        return len(ruling.unresolved)


def create_debate_state() -> DebateState:
    """创建初始辩论状态。"""
    return DebateState(phase=DebatePhase.IDLE, current_round=0)
