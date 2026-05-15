"""Role permission definitions — 四权分立 + 8 角色权限矩阵。

将架构文档 Section 4.4 的权限设计编码为可被 PermissionGuardMiddleware 消费的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# 抽象操作定义
# ═══════════════════════════════════════════════════════════════════════════════


class Action(str, Enum):
    """角色可执行的抽象操作——不是具体工具名，而是语义化的权限。

    PermissionGuardMiddleware 将具体工具映射到这些操作，
    再检查当前角色是否拥有该操作的权限。
    """

    # ── 采集类 ──
    PLAN_RESEARCH = "plan_research"        # 制定研究计划
    READ_DATA = "read_data"                # 读取已有文件/数据
    SEARCH_WEB = "search_web"              # 搜索外部数据
    FETCH_WEB = "fetch_web"                # 抓取网页
    PYTHON_COMPUTE = "python_compute"      # Python 计算/数据处理

    # ── 质疑类 ──
    CHALLENGE = "challenge"               # 提出质疑（必须附证据）
    RESPOND_TO_CRITIC = "respond_to_critic"  # 回应 Critic 质疑（必须附新数据）

    # ── 裁决类 ──
    ADJUDICATE = "adjudicate"             # 独立裁决
    RUN_VERIFICATION = "run_verification"  # 运行验证计算

    # ── 审核类 ──
    REVIEW_RULING = "review_ruling"        # 审核裁决书
    OVERRIDE_RULING = "override_ruling"    # 推翻裁决

    # ── 分析类 ──
    PLAN_ANALYSIS = "plan_analysis"        # 规划分析维度
    SYNTHESIZE = "synthesize"              # 多维合成
    GENERATE_CHARTS = "generate_charts"    # 生成可视化
    REVIEW_ANALYSIS = "review_analysis"    # 分析内审

    # ── 输出类 ──
    COMPOSE_REPORT = "compose_report"      # 组合报告
    WRITE_OUTPUT = "write_output"          # 写输出文件


# ═══════════════════════════════════════════════════════════════════════════════
# 角色 → 操作 映射
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RoleDefinition:
    """一个角色的完整权限定义。

    Attributes:
        name: 角色标识（与 SubagentConfig.name 对应）
        allowed_actions: 允许执行的操作集合
        evidence_required: 哪些操作必须附带证据（如 Critic 的 challenge）
        audit_required: 哪些操作必须记录审计日志（如 PI 的 override_ruling）
        max_instances: 该角色最多并行实例数
    """

    name: str
    allowed_actions: frozenset[Action]
    evidence_required: frozenset[Action] = field(default_factory=frozenset)
    audit_required: frozenset[Action] = field(default_factory=frozenset)
    max_instances: int = 1

    def can(self, action: Action) -> bool:
        return action in self.allowed_actions

    def requires_evidence(self, action: Action) -> bool:
        return action in self.evidence_required

    def requires_audit(self, action: Action) -> bool:
        return action in self.audit_required


# ═══════════════════════════════════════════════════════════════════════════════
# 8 角色权限矩阵
# ═══════════════════════════════════════════════════════════════════════════════

ROLES: dict[str, RoleDefinition] = {
    # ── Research SubGraph ──
    "pi_agent": RoleDefinition(
        name="pi_agent",
        allowed_actions=frozenset({
            Action.PLAN_RESEARCH,
            Action.READ_DATA,
            Action.REVIEW_RULING,
            Action.OVERRIDE_RULING,
        }),
        audit_required=frozenset({Action.OVERRIDE_RULING}),
    ),
    "data_scout": RoleDefinition(
        name="data_scout",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.SEARCH_WEB,
            Action.FETCH_WEB,
            Action.PYTHON_COMPUTE,
            Action.RESPOND_TO_CRITIC,
            Action.WRITE_OUTPUT,
        }),
        evidence_required=frozenset({Action.RESPOND_TO_CRITIC}),
        max_instances=4,  # Send API 并行 2-4 个 Scout
    ),
    "critic_agent": RoleDefinition(
        name="critic_agent",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.PYTHON_COMPUTE,
            Action.CHALLENGE,
        }),
        evidence_required=frozenset({Action.CHALLENGE}),
    ),
    "meta_judge": RoleDefinition(
        name="meta_judge",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.PYTHON_COMPUTE,
            Action.ADJUDICATE,
            Action.RUN_VERIFICATION,
        }),
        evidence_required=frozenset({Action.ADJUDICATE}),
    ),
    "pi_review": RoleDefinition(
        name="pi_review",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.REVIEW_RULING,
            Action.OVERRIDE_RULING,
        }),
        audit_required=frozenset({Action.OVERRIDE_RULING}),
    ),

    # ── Research SubGraph 内部 ──
    "error_handler": RoleDefinition(
        name="error_handler",
        allowed_actions=frozenset({Action.READ_DATA}),
        max_instances=1,
    ),

    # ── Analysis SubGraph ──
    "analyst_lead": RoleDefinition(
        name="analyst_lead",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.PLAN_ANALYSIS,
        }),
    ),
    "synthesizer": RoleDefinition(
        name="synthesizer",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.PYTHON_COMPUTE,
            Action.SYNTHESIZE,
            Action.GENERATE_CHARTS,
            Action.WRITE_OUTPUT,
        }),
        max_instances=1,
    ),
    "internal_reviewer": RoleDefinition(
        name="internal_reviewer",
        allowed_actions=frozenset({
            Action.READ_DATA,
            Action.PYTHON_COMPUTE,
            Action.REVIEW_ANALYSIS,
        }),
    ),

    # ── Parent Graph ──
    "report_composer": RoleDefinition(
        name="report_composer",
        allowed_actions=frozenset({
            Action.COMPOSE_REPORT,
            Action.WRITE_OUTPUT,
            Action.PYTHON_COMPUTE,
        }),
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# 操作 → 工具 映射
# ═══════════════════════════════════════════════════════════════════════════════

# 将抽象 Action 映射到 DeerFlow 具体工具名。
# 这里使用工具名前缀匹配——例如 "web_search" 会匹配所有搜索类工具。
ACTION_TOOL_MAP: dict[Action, list[str]] = {
    Action.PLAN_RESEARCH: [],
    Action.READ_DATA: ["read_file", "ls", "glob", "grep"],
    Action.SEARCH_WEB: ["web_search", "tavily_search", "firecrawl_search"],
    Action.FETCH_WEB: ["web_fetch", "tavily_fetch", "firecrawl_scrape", "jina_reader"],
    Action.PYTHON_COMPUTE: ["python", "bash"],
    Action.CHALLENGE: [],
    Action.RESPOND_TO_CRITIC: ["web_search", "web_fetch", "firecrawl_search", "firecrawl_scrape"],
    Action.ADJUDICATE: [],
    Action.RUN_VERIFICATION: ["python", "bash"],
    Action.REVIEW_RULING: [],
    Action.OVERRIDE_RULING: [],
    Action.PLAN_ANALYSIS: [],
    Action.SYNTHESIZE: ["python", "bash"],
    Action.GENERATE_CHARTS: ["python", "bash", "write_file"],
    Action.REVIEW_ANALYSIS: ["python", "bash", "read_file"],
    Action.COMPOSE_REPORT: ["write_file", "bash"],
    Action.WRITE_OUTPUT: ["write_file", "present_files"],
}

# 工具前缀 → Action 的反向索引：便于中间件快速查找工具对应的操作
TOOL_TO_ACTION: dict[str, Action] = {}
for _action, _tools in ACTION_TOOL_MAP.items():
    for _tool in _tools:
        TOOL_TO_ACTION[_tool] = _action


def get_role(role_name: str) -> RoleDefinition | None:
    """查找角色定义。"""
    return ROLES.get(role_name)


def find_action_for_tool(tool_name: str) -> Action | None:
    """根据工具名查找对应的抽象操作。

    支持精确匹配和前缀匹配。
    """
    if tool_name in TOOL_TO_ACTION:
        return TOOL_TO_ACTION[tool_name]
    # 前缀匹配
    for tool_prefix, action in TOOL_TO_ACTION.items():
        if tool_name.startswith(tool_prefix):
            return action
    return None
