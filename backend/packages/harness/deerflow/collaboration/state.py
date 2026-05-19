"""Three-layer state definitions for the PA-Agent-DF collaboration system.

State Architecture
------------------
CollaborationState (Parent Graph)
  └── 管理 8 角色协作流全生命周期，包含 HITL 审批、子图异常上浮
ResearchSubGraphState (Research SubGraph, 独立 namespace)
  └── PI → Scouts(Send) → Critic ⇄ Scouts → Meta-Judge → PI Review
AnalysisSubGraphState (Analysis SubGraph, 独立 namespace)
  └── Analyst Lead → Synthesizer → Internal Reviewer

关键设计：
- 父子 State 严格隔离：SubGraph 不直接读取 ParentState，通过 state_in 投影传入
- 累加字段使用 Annotated[list, add] reducer：多轮/并行结果自动合并
- 异常上浮：子图 error 字段通过 state_out 映射到父图，不抛异常跨越边界
"""

from operator import add as op_add
from typing import Annotated, NotRequired, TypedDict

from langchain.agents import AgentState


# ═══════════════════════════════════════════════════════════════════════════════
# Parent Graph State
# ═══════════════════════════════════════════════════════════════════════════════


class CollaborationState(AgentState):
    """Parent Graph 的完整协作状态。

    LangGraph 要求所有图 State 包含 ``messages`` 字段，
    AgentState 已提供，因此这里只声明协作特有字段。

    State Mapping 规范（Section 4.3）：
    - Research SubGraph 输出 → Parent.validated_brief
    - Parent.validated_brief → Analysis SubGraph 输入
    - 子图异常通过 collaboration_error 字段上浮
    """

    # ── 工作流配置 ──
    workflow_type: NotRequired[str | None]  # competitive_analysis / market_trend / pricing_optimization
    max_scouts: NotRequired[int | None]  # Data Scout 并行数量

    # ── Research SubGraph 输出 ──
    validated_brief: NotRequired[dict | None]
    """Research SubGraph 的精炼输出，包含已验证的数据点、来源、置信度。"""
    research_quality_score: NotRequired[float | None]
    """Meta-Judge 计算的研究质量分 (0.0-1.0)。"""

    # ── 累加字段：多轮质疑-补采循环的结果 ──
    unresolved_issues: Annotated[list[dict], op_add]
    """Critic 质疑后无法在 2 轮内解决的遗留问题。每个元素包含 issue/evidence/source。"""

    # ── Analysis SubGraph 输出 ──
    synthesis_report: NotRequired[dict | None]
    """Synthesizer 生成的完整分析报告（对比矩阵、SWOT、趋势、建议）。"""
    internal_review_passed: NotRequired[bool | None]

    # ── HITL Gate ──
    review_decision: NotRequired[str | None]  # "approve" | "modify" | "replan"
    review_comment: NotRequired[str | None]

    # ── 异常上浮 ──
    collaboration_error: NotRequired[str | None]
    """子图异常通过 state_out 映射到此字段，父图条件边降级处理。"""

    # ── 协作 Memory（跨 run 持久化，通过 checkpointer）──
    source_credibility_memory: NotRequired[dict | None]
    """Source credibility scores accumulated across research runs."""
    product_knowledge_memory: NotRequired[dict | None]
    """Validated product data points accumulated across research runs."""


# ═══════════════════════════════════════════════════════════════════════════════
# Research SubGraph State（独立 namespace）
# ═══════════════════════════════════════════════════════════════════════════════


class ResearchSubGraphState(AgentState):
    """Research SubGraph 的内部 State。

    完全独立于 ParentState。SubGraph 编译时使用自己的 State Schema，
    通过 state_in/state_out 映射函数与父图交换数据。

    工作流：planning → collecting ⇄ (critique → recollect) → adjudicating → output

    角色权限约束（四权分立）：
    - PI：规划 + 分发 + 审核裁决（可推翻但需审计）
    - Scout：采集 + 回应质疑（不可质疑/裁决）
    - Critic：质疑（必须附证据，不可自行采集）
    - Judge：裁决（只看证据不站队，不可采集/质疑/合成）
    """

    # ── PI 规划阶段 ──
    research_plan: NotRequired[dict | None]
    """PI 拆解的研究任务计划，包含 query/target_sources/sub_tasks。"""

    # ── Scout 采集结果（Send API Fan-out 并行，累加合并）──
    scout_results: Annotated[list[dict], op_add]
    """Data Scout 返回的结构化采集结果，每项含 source/content/data_points/timestamp。"""
    scout_task: NotRequired[dict | None]
    """Send API 传入的单个采集任务 {id, query, target_sources, method}。"""

    # ── 对抗式批判（ClawdLab 核心协议）──
    challenges: Annotated[list[dict], op_add]
    """Critic Agent 的结构化质疑列表。每条含 claim/evidence/suggested_remedy。"""
    rebuttals: Annotated[list[dict], op_add]
    """Scout 定向补采后的回应，对应 challenge_id。"""
    debate_round: NotRequired[int | None]
    """当前质疑-补采轮次（最多 2 轮）。"""

    # ── 裁决阶段 ──
    ruling: NotRequired[dict | None]
    """Meta-Judge 独立裁决书，含 verdict/resolved_issues/unresolved_issues/quality_score。"""
    pi_override_log: NotRequired[list[dict] | None]
    """PI 推翻裁决的审计日志。每条含 overridden_ruling/reason/timestamp。"""

    # ── Research 输出 ──
    validated_brief: NotRequired[dict | None]
    """精炼后的研究简报，传递给 Analysis SubGraph。"""
    research_quality_score: NotRequired[float | None]

    # ── 协作 Memory（父图传入的跨 run 记忆）──
    source_credibility_memory: NotRequired[dict | None]
    """Source credibility scores passed from parent state (read-only input)."""
    product_knowledge_memory: NotRequired[dict | None]
    """Product knowledge passed from parent state (read-only input)."""

    # ── 异常 ──
    error: NotRequired[str | None]


# ═══════════════════════════════════════════════════════════════════════════════
# Analysis SubGraph State（独立 namespace）
# ═══════════════════════════════════════════════════════════════════════════════


class AnalysisSubGraphState(AgentState):
    """Analysis SubGraph 的内部 State。

    接收 Research 的精炼输出，执行多维度分析和报告合成。
    不包含采集/批判相关字段——只关心分析结果。

    工作流：analyzing → synthesizing → internal_review → output
    """

    # ── 输入（来自 Parent，通过 state_in 映射）──
    validated_brief: NotRequired[dict | None]
    research_quality_score: NotRequired[float | None]
    unresolved_issues: Annotated[list[dict], op_add]

    # ── 分析阶段 ──
    analysis_plan: NotRequired[dict | None]
    """Analyst Lead 的分析计划，指定对比维度/模型/可视化要求。"""
    analysis_results: Annotated[list[dict], op_add]
    """Synthesizer 各维度分析结果的累加。每项含 dimension/data/insight/visualization_path。"""

    # ── 合成输出 ──
    synthesis_report: NotRequired[dict | None]
    """包含 comparison_matrix、swot_analysis、trend_analysis、recommendations。"""

    # ── 内审 ──
    internal_review_passed: NotRequired[bool | None]
    review_feedback: NotRequired[str | None]

    # ── 异常 ──
    error: NotRequired[str | None]
