"""HITL Gate — 人类审批门节点。

LangGraph 2.0 interrupt() + Command(resume=...) 实现。
在 Analysis 完成后暂停图执行，等待人类审批。
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Literal

from langgraph.types import Command, interrupt

from deerflow.collaboration.state import CollaborationState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# HITL Gate 数据结构
# ═══════════════════════════════════════════════════════════════════════════════

HITL_DECISIONS = ("approve", "modify", "replan")
"""有效的审批决定。"""

STALE_TIMEOUT_SECONDS = 30 * 60
"""审批超时（30 分钟），超时后提示状态可能过期。"""


def build_approval_payload(state: CollaborationState) -> dict:
    """从当前 State 构建审批包——展示给人类的审批界面数据。

    包含：数据点数量、质量分、关键发现、未解决问题。
    """
    brief = state.get("validated_brief", {}) or {}
    report = state.get("synthesis_report", {}) or {}
    quality = state.get("research_quality_score")

    return {
        "message": "分析已完成，请审阅并决定下一步",
        "decisions": [
            {"value": "approve", "label": "批准 — 生成最终报告"},
            {"value": "modify", "label": "修改 — 重新合成分析"},
            {"value": "replan", "label": "重新规划 — 回到研究阶段"},
        ],
        "summary": {
            "research_quality_score": quality,
            "verified_data_points": len(brief.get("verified_data_points", [])),
            "unresolved_issues": brief.get("unresolved", []),
            "key_findings": _extract_key_findings(report),
        },
        "timestamp": time.time(),
        "stale_after_seconds": STALE_TIMEOUT_SECONDS,
    }


def _extract_key_findings(report: dict) -> list[str]:
    """从 synthesis_report 中提取关键发现摘要。"""
    findings: list[str] = []
    recommendations = report.get("recommendations", [])
    for rec in recommendations[:3]:
        if isinstance(rec, dict):
            findings.append(str(rec.get("action", "")))
        else:
            findings.append(str(rec))
    if not findings and report.get("executive_summary"):
        findings.append(str(report["executive_summary"])[:200])
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# HITL Gate Node
# ═══════════════════════════════════════════════════════════════════════════════


def hitl_gate_node(state: CollaborationState) -> dict | Command:
    """HITL Gate — 暂停图执行，等待人类审批。

    LangGraph 2.0 interrupt() 行为：
    - 第一次进入：暂停图，抛出 GraphInterrupt，checkpoint 写入持久化存储
    - resume 后第二次进入：从 checkpoint 恢复，state 已有 review_decision

    审批决定流向：
    - "approve" → report_composer（提交报告）
    - "modify" → analysis_subgraph（重新合成）
    - "replan" → research_subgraph（重新规划）

    幂等性检查：如果 state 已有 review_decision，直接返回（可能是 resume 后再次命中）。
    """
    # 幂等性：如果已做出 terminal 决策（approve），跳过 interrupt 防止重复处理
    # modify/replan 触发子图重跑后会重新进入此节点，需重新审批——不清除旧值，
    # 新的 interrupt 结果会直接覆盖 review_decision
    existing_decision = state.get("review_decision")
    if existing_decision and existing_decision not in ("modify", "replan"):
        logger.info("HITL: 已有审批决定 '%s'，跳过 interrupt", existing_decision)
        return {}

    # 构建审批界面数据
    approval_payload = build_approval_payload(state)

    # Stale 检查：审批包的时间戳是否过期
    approval_payload["_stale_check"] = {
        "generated_at": time.time(),
        "stale_after": STALE_TIMEOUT_SECONDS,
    }

    logger.info("HITL: 暂停图，等待人类审批。数据点: %d, 质量分: %s",
                approval_payload["summary"]["verified_data_points"],
                approval_payload["summary"]["research_quality_score"])

    # LangGraph 2.0 interrupt() — 暂停图执行
    decision = interrupt(approval_payload)

    # ↓ 以下代码在 Command(resume=...) 后执行 ↓

    logger.info("HITL: 收到审批决定 '%s'，恢复图执行", decision)

    # 校验决定有效性
    if decision not in HITL_DECISIONS:
        logger.warning("HITL: 无效决定 '%s'，默认结束", decision)
        return {}

    return {"review_decision": decision}
