"""State Mapping 纯函数 — SubGraph ⇄ Parent Graph 间的数据投影。

关键设计：
- 纯函数，无副作用：不修改输入 state，只返回 dict
- 严格投影：子图只能看到 state_in 传入的字段，不能访问父图其他字段
- 异常上浮：子图 error 字段通过 state_out 映射到父图 collaboration_error
- 单向数据流：Research → Parent → Analysis，子图间不直接通信
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deerflow.collaboration.state import AnalysisSubGraphState, CollaborationState, ResearchSubGraphState


# ═══════════════════════════════════════════════════════════════════════════════
# Research SubGraph → Parent
# ═══════════════════════════════════════════════════════════════════════════════


def map_research_to_parent(
    child_state: ResearchSubGraphState,
    parent_state: CollaborationState,  # noqa: ARG001 保留参数以符合 state_out 签名规范
) -> dict:
    """Research SubGraph 输出 → Parent State 投影。

    只传递精炼结果，不暴露 Research 内部字段（如 challenges/rebuttals/debate_round）。
    """
    result: dict = {}

    validated_brief = child_state.get("validated_brief")
    if validated_brief is not None:
        result["validated_brief"] = validated_brief

    quality_score = child_state.get("research_quality_score")
    if quality_score is not None:
        result["research_quality_score"] = quality_score

    # unresolved_issues 是累加字段，直接传递已有列表
    unresolved = child_state.get("unresolved_issues")
    if unresolved:
        result["unresolved_issues"] = unresolved

    # 异常上浮：子图内部 error → 父图 collaboration_error
    error = child_state.get("error")
    if error is not None:
        result["collaboration_error"] = error

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Parent → Research SubGraph
# ═══════════════════════════════════════════════════════════════════════════════


def map_parent_to_research(parent_state: CollaborationState) -> dict:
    """Parent State → Research SubGraph 输入投影。

    仅在 HITL replan（重新规划）时使用，将父图配置传递给 Research。
    """
    result: dict = {}

    workflow_type = parent_state.get("workflow_type")
    if workflow_type is not None:
        result["workflow_type"] = workflow_type  # type: ignore[typeddict-unknown-key]

    max_scouts = parent_state.get("max_scouts")
    if max_scouts is not None:
        result["max_scouts"] = max_scouts  # type: ignore[typeddict-unknown-key]

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Parent → Analysis SubGraph
# ═══════════════════════════════════════════════════════════════════════════════


def map_parent_to_analysis(parent_state: CollaborationState) -> dict:
    """Parent State → Analysis SubGraph 输入投影。

    将 Research 的精炼输出传递给 Analysis，Research 内部状态不可见。
    """
    result: dict = {}

    validated_brief = parent_state.get("validated_brief")
    if validated_brief is not None:
        result["validated_brief"] = validated_brief

    quality_score = parent_state.get("research_quality_score")
    if quality_score is not None:
        result["research_quality_score"] = quality_score

    unresolved = parent_state.get("unresolved_issues")
    if unresolved:
        result["unresolved_issues"] = unresolved

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Analysis SubGraph → Parent
# ═══════════════════════════════════════════════════════════════════════════════


def map_analysis_to_parent(
    child_state: AnalysisSubGraphState,
    parent_state: CollaborationState,  # noqa: ARG001
) -> dict:
    """Analysis SubGraph 输出 → Parent State 投影。

    传递合成报告和内审结果，Analysis 内部中间结果不暴露。
    """
    result: dict = {}

    synthesis_report = child_state.get("synthesis_report")
    if synthesis_report is not None:
        result["synthesis_report"] = synthesis_report

    review_passed = child_state.get("internal_review_passed")
    if review_passed is not None:
        result["internal_review_passed"] = review_passed

    # 异常上浮
    error = child_state.get("error")
    if error is not None:
        result["collaboration_error"] = error

    return result
