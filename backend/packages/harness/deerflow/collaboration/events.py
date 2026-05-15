"""Collaboration stream event type definitions.

LangGraph custom stream mode 事件——前端/客户端通过 SSE 订阅。
事件按阶段分组：research / analysis / hitl / compose / error。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict


class EventType(str, Enum):
    """协作流事件类型。"""

    # ── Research 阶段 ──
    RESEARCH_STARTED = "research_started"
    RESEARCH_PLAN_READY = "research_plan_ready"
    SCOUT_DISPATCHED = "scout_dispatched"
    SCOUT_RESULT = "scout_result"
    CRITIQUE_STARTED = "critique_started"
    CHALLENGE_ISSUED = "challenge_issued"
    REBUTTAL_STARTED = "rebuttal_started"
    REBUTTAL_RECEIVED = "rebuttal_received"
    ADJUDICATION_STARTED = "adjudication_started"
    RULING_READY = "ruling_ready"
    RESEARCH_COMPLETED = "research_completed"

    # ── Analysis 阶段 ──
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_PLAN_READY = "analysis_plan_ready"
    SYNTHESIS_PROGRESS = "synthesis_progress"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    ANALYSIS_COMPLETED = "analysis_completed"

    # ── HITL ──
    HITL_WAITING = "hitl_waiting"
    HITL_DECISION_RECEIVED = "hitl_decision_received"

    # ── Report ──
    COMPOSE_STARTED = "compose_started"
    COMPOSE_COMPLETED = "compose_completed"

    # ── System ──
    PHASE_TRANSITION = "phase_transition"
    ERROR = "error"
    WORKFLOW_COMPLETED = "workflow_completed"


class StreamEvent(TypedDict, total=False):
    """通用流式事件结构。

    LangGraph custom stream 要求每个事件是 dict。
    StreamWriter 会将此写入 SSE channel。
    """

    type: str
    """事件类型，对应 EventType 的值。"""
    phase: str
    """当前阶段: research / analysis / hitl / compose。"""
    data: dict[str, Any]
    """事件负载数据。"""
    timestamp: float
    """事件时间戳。"""
    message: str
    """人类可读的消息摘要。"""


# ═══════════════════════════════════════════════════════════════════════════════
# Event builder helper
# ═══════════════════════════════════════════════════════════════════════════════


def make_event(
    event_type: EventType,
    *,
    phase: str = "",
    data: dict[str, Any] | None = None,
    message: str = "",
) -> StreamEvent:
    """创建标准化流式事件。"""
    import time

    return StreamEvent(
        type=event_type.value,
        phase=phase,
        data=data or {},
        timestamp=time.time(),
        message=message,
    )
