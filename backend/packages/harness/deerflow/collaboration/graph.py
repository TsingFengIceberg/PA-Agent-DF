"""Parent Graph — Nested SubGraph 组装。

Parent Graph 职责：
- 挂载 Research SubGraph 和 Analysis SubGraph（Nested SubGraph 模式）
- HITL Gate（人类审批门）
- Report Composer（最终报告生成）
- 子图异常降级处理
- 条件路由

架构：
┌──────────────────────────────────────────────────────┐
│                    Parent Graph                       │
│                                                       │
│  Research SubGraph ──→ Analysis SubGraph               │
│       (state_out)         (state_in)                  │
│                                  │                    │
│                           HITL Gate                    │
│                                  │                    │
│                          Report Composer               │
└──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from langgraph.constants import END
from langgraph.graph import StateGraph

from deerflow.collaboration.nodes.analysis_nodes import report_composer_node
from deerflow.collaboration.nodes.hitl_gate import hitl_gate_node
from deerflow.collaboration.state import CollaborationState
from deerflow.collaboration.subgraphs.analysis_subgraph import build_analysis_subgraph
from deerflow.collaboration.subgraphs.research_subgraph import build_research_subgraph
from deerflow.collaboration.subgraphs.state_mapping import (
    map_analysis_to_parent,
    map_parent_to_analysis,
    map_parent_to_research,
    map_research_to_parent,
)

if TYPE_CHECKING:
    from langgraph.graph import CompiledStateGraph

logger = logging.getLogger(__name__)


# ── Parent 层节点 ──


def error_handler_node(state: CollaborationState) -> dict:
    """Parent 层错误处理 — 子图异常降级。Sprint 4 实现。"""
    raise NotImplementedError("error_handler_node — Sprint 4 实现")


# ── 条件路由 ─────────────────────────────────────────────────────────────────


def route_after_research(state: CollaborationState) -> Literal["analysis_subgraph", "error_handler"]:
    """Research 完成后的路径选择。

    如果 Research SubGraph 异常（collaboration_error 不为空），
    跳到错误处理而非继续 Analysis。
    """
    if state.get("collaboration_error"):
        logger.warning("Research SubGraph error, routing to error_handler")
        return "error_handler"
    return "analysis_subgraph"


def route_after_analysis(state: CollaborationState) -> Literal["hitl_gate", "error_handler"]:
    """Analysis 完成后的路径选择。"""
    if state.get("collaboration_error"):
        logger.warning("Analysis SubGraph error, routing to error_handler")
        return "error_handler"
    return "hitl_gate"


def route_after_hitl(state: CollaborationState) -> Literal["report_composer", "research_subgraph", "analysis_subgraph", "__end__"]:
    """HITL 审批后的路径选择。

    - approve → Report Composer
    - modify → Analysis SubGraph（重新合成）
    - replan → Research SubGraph（重新规划）
    """
    decision = state.get("review_decision")
    if decision == "approve":
        return "report_composer"
    elif decision == "modify":
        return "analysis_subgraph"
    elif decision == "replan":
        return "research_subgraph"
    return "__end__"


# ── Parent Graph 构建 ────────────────────────────────────────────────────────


def build_collaboration_graph() -> CompiledStateGraph:
    """构建 Parent Graph (Nested SubGraph 架构)。

    LangGraph Nested SubGraph 关键 API：
    - add_node("name", compiled_subgraph, state_in=fn, state_out=fn)
      - state_in: ParentState → dict（传入子图前投影）
      - state_out: (ChildState, ParentState) → dict（子图输出后写回父图）
    - 子图必须先 .compile() 才能挂载
    - 父子图共享 checkpointer 实例
    - 每 SubGraph 使用独立 checkpoint_ns 防止并行碰撞

    返回编译后的协作图，由 make_lead_agent() 或 langgraph.json 加载。
    """
    builder = StateGraph(CollaborationState)

    # ── SubGraph 挂载 ──
    # 关键：build_*_subgraph() 返回的是 CompiledStateGraph，
    # 可以直接传给 add_node() 作为嵌套子图。
    research_subgraph = build_research_subgraph()
    analysis_subgraph = build_analysis_subgraph()

    builder.add_node(
        "research_subgraph",
        research_subgraph,  # type: ignore[arg-type]
        state_in=map_parent_to_research,
        state_out=map_research_to_parent,
    )

    builder.add_node(
        "analysis_subgraph",
        analysis_subgraph,  # type: ignore[arg-type]
        state_in=map_parent_to_analysis,
        state_out=map_analysis_to_parent,
    )

    # ── Parent 层节点 ──
    builder.add_node("hitl_gate", hitl_gate_node)
    builder.add_node("report_composer", report_composer_node)
    builder.add_node("error_handler", error_handler_node)

    # ── 边与路由 ──
    builder.set_entry_point("research_subgraph")

    builder.add_conditional_edges(
        "research_subgraph",
        route_after_research,
        {
            "analysis_subgraph": "analysis_subgraph",
            "error_handler": "error_handler",
        },
    )

    builder.add_conditional_edges(
        "analysis_subgraph",
        route_after_analysis,
        {
            "hitl_gate": "hitl_gate",
            "error_handler": "error_handler",
        },
    )

    # HITL → approve/compose | modify/analysis | replan/research
    builder.add_conditional_edges(
        "hitl_gate",
        route_after_hitl,
        {
            "report_composer": "report_composer",
            "analysis_subgraph": "analysis_subgraph",
            "research_subgraph": "research_subgraph",
            "__end__": END,
        },
    )

    builder.add_edge("report_composer", END)
    builder.add_edge("error_handler", END)

    return builder.compile()
