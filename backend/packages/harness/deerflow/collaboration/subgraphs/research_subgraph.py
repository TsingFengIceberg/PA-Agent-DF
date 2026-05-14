"""Research SubGraph — 对抗式批判验证研究流程。

工作流：
  PI Agent（规划+分发）
    → Send API Fan-out → Data Scouts（并行采集）
    → Critic Agent（对抗式质疑，必须附证据）
    → [有问题] → Scouts 定向补采（rebuttal，最多2轮）
    → [没问题] → Meta-Judge（独立裁决）
    → PI Review（审核裁决书，可推翻但需审计）
    → ValidatedBrief

四权分立：
  - 质疑权（Critic）: 必须附证据，不可自行采集
  - 执行权（Scout）: 可采集+回应质疑，不可质疑/裁决
  - 裁决权（Judge）: 只看证据不站队，不可采集/质疑/合成
  - 监督权（PI）: 可推翻裁决（需审计）
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from langgraph.constants import END
from langgraph.types import Send
from langgraph.graph import StateGraph

from deerflow.collaboration.state import ResearchSubGraphState

if TYPE_CHECKING:
    from langgraph.graph import CompiledStateGraph

logger = logging.getLogger(__name__)

# ── 节点声明（Sprint 2 实现具体逻辑）──────────────────────────────────────────


def pi_agent_node(state: ResearchSubGraphState) -> dict:
    """PI Agent — 规划研究任务 + Send API Fan-out 分发到 Scouts。

    Sprint 2 实现：结构化任务拆解 + 并行 Scout 调度。
    """
    raise NotImplementedError("pi_agent_node — Sprint 2 实现")


def data_scout_node(state: ResearchSubGraphState) -> dict:
    """Data Scout — 并行采集数据 + 回应 Critic 质疑。

    Send API 并行分发，每个 Scout 独立上下文，结果通过 Annotated[list, add] 累加。
    """
    raise NotImplementedError("data_scout_node — Sprint 2 实现")


def critic_agent_node(state: ResearchSubGraphState) -> dict:
    """Critic Agent — 对抗式质疑（ClawdLab 核心协议）。

    每条质疑必须附带 evidence（引用具体数据点、来源对比）。
    不可自行采集新数据，只能基于已有 scout_results 进行质疑。
    """
    raise NotImplementedError("critic_agent_node — Sprint 2 实现")


def meta_judge_node(state: ResearchSubGraphState) -> dict:
    """Meta-Judge — 独立裁决。

    只看 Critic 的 challenge 和 Scout 的 rebuttal，不看身份。
    裁决基于计算工具输出（统计检验/交叉验证），不基于"多数意见"。
    """
    raise NotImplementedError("meta_judge_node — Sprint 2 实现")


def pi_review_node(state: ResearchSubGraphState) -> dict:
    """PI Review — 审核裁决书。

    - 批准 → 生成 validated_brief，传递到 Analysis SubGraph
    - 推翻 → 记录 pi_override_log，返回裁决理由
    """
    raise NotImplementedError("pi_review_node — Sprint 2 实现")


def error_handler_node(state: ResearchSubGraphState) -> dict:
    """错误处理 — 子图异常上浮。

    将内部异常信息写入 error 字段，通过 state_out 映射到父图。
    """
    raise NotImplementedError("error_handler_node — Sprint 2 实现")


# ── 条件路由 ─────────────────────────────────────────────────────────────────


def route_after_critic(state: ResearchSubGraphState) -> Literal["data_scout", "meta_judge"]:
    """Critic 之后的路径选择。

    返回 "data_scout" 触发定向补采（最多 2 轮），
    返回 "meta_judge" 进入裁决阶段。

    Sprint 2 实现完整路由逻辑。
    """
    debate_round = state.get("debate_round", 0) or 0
    challenges = state.get("challenges", [])

    if challenges and debate_round < 2:
        return "data_scout"
    return "meta_judge"


def route_after_pi_review(state: ResearchSubGraphState) -> Literal["__end__", "error_handler"]:
    """PI 审核后的路径选择。"""
    if state.get("error"):
        return "error_handler"
    return "__end__"


# ── SubGraph 构建 ────────────────────────────────────────────────────────────


def build_research_subgraph() -> CompiledStateGraph:
    """构建 Research SubGraph（独立编译）。

    返回编译后的子图，由 Parent Graph 通过 add_node(subgraph, state_in=fn, state_out=fn) 挂载。

    LangGraph 要求子图必须先 .compile() 才能挂载到父图。
    """
    builder = StateGraph(ResearchSubGraphState)

    # 节点注册
    builder.add_node("pi_agent", pi_agent_node)
    builder.add_node("data_scout", data_scout_node)
    builder.add_node("critic_agent", critic_agent_node)
    builder.add_node("meta_judge", meta_judge_node)
    builder.add_node("pi_review", pi_review_node)
    builder.add_node("error_handler", error_handler_node)

    # 边
    builder.set_entry_point("pi_agent")
    builder.add_edge("pi_agent", "critic_agent")
    builder.add_conditional_edges("critic_agent", route_after_critic, {
        "data_scout": "data_scout",
        "meta_judge": "meta_judge",
    })
    builder.add_edge("data_scout", "critic_agent")  # 定向补采后回到 Critic
    builder.add_edge("meta_judge", "pi_review")
    builder.add_conditional_edges("pi_review", route_after_pi_review, {
        "__end__": END,
        "error_handler": "error_handler",
    })
    builder.add_edge("error_handler", END)

    return builder.compile()
