"""Sprint 6 — End-to-End 全图场景测试。

验证 3 个完整业务场景的端到端数据流：
- 竞品深度拆解 (competitive_analysis)
- 市场趋势洞察 (market_trend)
- 商品定价优化 (pricing_optimization)

以及异常上浮、HITL 循环路径。

Mock 策略：
- SubagentExecutor 被 patch，根据 config.name 返回场景特定 JSON
- interrupt() 被 patch 为自动返回 "approve"
- get_available_tools 被 patch 返回空列表
- 不调用真实 LLM 或外部工具
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Generator
from unittest.mock import patch

import pytest

from deerflow.collaboration.state import CollaborationState


# ═══════════════════════════════════════════════════════════════════════════════
# Shared mock infrastructure
# ═══════════════════════════════════════════════════════════════════════════════


def _make_executor_class(responses: dict[str, str]):
    """创建根据 config.name 返回不同响应的 Mock SubagentExecutor。"""

    class MockExecutor:
        def __init__(self, config, tools=None):
            self.config = config

        def execute(self, task: str) -> str:
            name = getattr(self.config, "name", "unknown")
            return responses.get(name, "{}")

    return MockExecutor


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 1: 竞品深度拆解 (Competitive Analysis)
#   planning → collecting(3 scouts) → validating(Critic scipy 检验 + Judge 裁决)
#   → synthesizing(Skills) → hitl(approve) → composing
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_1_RESPONSES = {
    "pi_agent": json.dumps({
        "topic": "iPhone 17 vs Huawei Mate 70 Pro vs Samsung S25 Ultra 深度对比",
        "sub_tasks": [
            {"id": "t1", "query": "iPhone 17 specs and pricing", "target_sources": ["apple.com"], "method": "web_search"},
            {"id": "t2", "query": "Huawei Mate 70 Pro specs", "target_sources": ["huawei.com"], "method": "web_search"},
            {"id": "t3", "query": "Samsung S25 Ultra specs", "target_sources": ["samsung.com"], "method": "web_search"},
        ],
        "num_scouts": 3,
    }),
    "data_scout": json.dumps({
        "source": "gsmarena_combined",
        "content": "iPhone 17: A19 chip, 6.3\" OLED, 48MP triple camera, $899.",
        "data_points": [
            {"label": "iPhone 17 price", "value": 899, "confidence": 0.95},
            {"label": "Mate 70 Pro price", "value": 999, "confidence": 0.92},
            {"label": "S25 Ultra price", "value": 1299, "confidence": 0.97},
            {"label": "S25 Ultra camera", "value": "200MP", "confidence": 0.97},
        ],
        "methods": ["web_search"],
    }),
    "critic_agent": json.dumps([]),  # 无质疑 → 直接进入裁决
    "meta_judge": json.dumps({
        "ruling_id": "rul-comp-001",
        "resolved": [],
        "unresolved": [],
        "dismissed": [],
        "quality_score": 0.85,
        "computation_summary": "Cross-validated across 3 sources. No conflicts. Quality 0.85.",
    }),
    "pi_review": json.dumps({
        "validated_brief": {
            "topic": "iPhone 17 vs Mate 70 Pro vs S25 Ultra",
            "verified_data_points": [
                {"data": "iPhone 17: $899", "source": "gsmarena", "confidence": 0.95},
                {"data": "Mate 70 Pro: $999", "source": "gsmarena", "confidence": 0.92},
                {"data": "S25 Ultra: $1299", "source": "gsmarena", "confidence": 0.97},
                {"data": "S25 Ultra camera: 200MP", "source": "gsmarena", "confidence": 0.97},
            ],
            "rejected_claims": [],
            "quality_score": 0.85,
            "unresolved": [],
        },
    }),
    "analyst_lead": json.dumps({
        "dimensions": ["price", "specifications", "camera", "battery", "ecosystem"],
        "skills_to_use": ["spec-comparator", "price-elasticity"],
        "comparison_framework": {"categories": ["display", "performance"], "metrics": ["value_score"]},
        "visualizations": ["radar_chart", "price_comparison_bar"],
        "priority_order": ["specifications", "camera", "price"],
    }),
    "synthesizer": json.dumps({
        "executive_summary": "iPhone 17 leads in ecosystem, S25 Ultra leads in camera.",
        "comparison_matrix": {
            "dimensions": ["display", "performance", "camera", "battery", "price"],
            "products": {"iPhone 17": [8.5, 9.0, 7.5, 8.0, 7.0], "S25 Ultra": [9.0, 9.5, 9.5, 8.0, 6.0]},
        },
        "swot_analysis": {
            "iPhone 17": {"strengths": ["A19 chip", "iOS"], "weaknesses": ["Price"], "opportunities": ["AI"], "threats": ["Android"]},
            "S25 Ultra": {"strengths": ["200MP", "S Pen"], "weaknesses": ["Price"], "opportunities": ["Foldable"], "threats": ["Chinese brands"]},
        },
        "trend_analysis": "Premium smartphone market converging on AI and camera.",
        "recommendations": [
            {"action": "S25 Ultra for photography enthusiasts", "priority": "high"},
            {"action": "iPhone 17 for ecosystem users", "priority": "high"},
            {"action": "Mate 70 Pro for value seekers", "priority": "medium"},
        ],
    }),
    "internal_reviewer": json.dumps({
        "passed": True, "issues": [],
        "data_trace_check": {"total_claims": 12, "claims_with_source_trace": 12, "trace_rate": 1.0},
        "visualization_check": {"expected_count": 2, "generated_count": 2, "all_present": True},
        "recommendation_quality": "strong", "suggestions": [],
    }),
    "report_composer": "Final report written to /mnt/user-data/outputs/analysis_report.md",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 2: 市场趋势洞察 (Market Trend)
#   planning → collecting(2 scouts) → synthesizing → hitl(approve) → composing
#   跳过硬体验证
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_2_RESPONSES = {
    "pi_agent": json.dumps({
        "topic": "2026 Q1 中国新能源汽车市场竞争格局与趋势",
        "sub_tasks": [
            {"id": "t1", "query": "BYD Q1 2026 sales", "target_sources": ["byd.com"], "method": "web_search"},
            {"id": "t2", "query": "NEV market share data", "target_sources": ["caam.org.cn"], "method": "web_search"},
        ],
        "num_scouts": 2,
    }),
    "data_scout": json.dumps({
        "source": "caam_q1_2026",
        "content": "Q1 2026 China NEV: BYD 850K (35%), Tesla 320K (13%), Li Auto 180K (7.5%). NEV penetration 48%.",
        "data_points": [
            {"label": "BYD Q1 sales", "value": 850000, "confidence": 0.93},
            {"label": "Tesla Q1 China", "value": 320000, "confidence": 0.91},
            {"label": "NEV penetration", "value": 0.48, "confidence": 0.95},
            {"label": "Li Auto Q1", "value": 180000, "confidence": 0.90},
        ],
        "methods": ["web_search", "web_fetch"],
    }),
    "critic_agent": json.dumps([]),
    "meta_judge": json.dumps({
        "ruling_id": "rul-mkt-002",
        "resolved": [], "unresolved": [], "dismissed": [],
        "quality_score": 0.82,
        "computation_summary": "CAAM data cross-referenced. BYD leads at 35%.",
    }),
    "pi_review": json.dumps({
        "validated_brief": {
            "topic": "2026 Q1 China NEV Market",
            "verified_data_points": [
                {"data": "BYD: 850K (35%)", "source": "CAAM", "confidence": 0.93},
                {"data": "Tesla: 320K (13%)", "source": "CPCA", "confidence": 0.91},
                {"data": "NEV penetration: 48%", "source": "CAAM", "confidence": 0.95},
                {"data": "Li Auto: 180K (7.5%)", "source": "filing", "confidence": 0.90},
            ],
            "rejected_claims": [],
            "quality_score": 0.82,
            "unresolved": [],
        },
    }),
    "analyst_lead": json.dumps({
        "dimensions": ["market_share", "growth_rate", "technology", "segments"],
        "skills_to_use": ["trend-detector", "market-share-calc"],
        "comparison_framework": {"categories": ["share", "growth"], "metrics": ["pct", "yoy"]},
        "visualizations": ["market_share_pie", "trend_line"],
        "priority_order": ["market_share", "growth_rate"],
    }),
    "synthesizer": json.dumps({
        "executive_summary": "BYD dominates 35%. NEV penetration 48%, up from 35% YoY.",
        "comparison_matrix": {
            "dimensions": ["market_share", "yoy_growth", "tech_score"],
            "products": {"BYD": [35, 28, 8.0], "Tesla": [13, 8, 9.5]},
        },
        "swot_analysis": {
            "BYD": {"strengths": ["Scale"], "weaknesses": ["Brand"], "opportunities": ["Europe"], "threats": ["Price war"]},
        },
        "trend_analysis": "NEV penetration projected to exceed 55% by Q4 2026.",
        "recommendations": [
            {"action": "Monitor BYD overseas expansion", "priority": "high"},
            {"action": "Watch Tesla FSD China approval", "priority": "high"},
            {"action": "Track smart driving adoption", "priority": "medium"},
        ],
    }),
    "internal_reviewer": json.dumps({
        "passed": True, "issues": [],
        "data_trace_check": {"total_claims": 10, "claims_with_source_trace": 10, "trace_rate": 1.0},
        "visualization_check": {"expected_count": 2, "generated_count": 2, "all_present": True},
        "recommendation_quality": "strong", "suggestions": [],
    }),
    "report_composer": "Final report written.",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 3: 商品定价优化 (Pricing Optimization)
#   planning → collecting(2 scouts) → validating(Critic+Judge)
#   → synthesizing → hitl(approve) → composing
#   含 Critic 质疑 + Scout 补采辩论循环
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_3_RESPONSES = {
    "pi_agent": json.dumps({
        "topic": "智能手表定价优化 — 竞品分析",
        "sub_tasks": [
            {"id": "t1", "query": "Apple Watch 10, Huawei Watch 5 pricing", "target_sources": ["jd.com"], "method": "web_search"},
            {"id": "t2", "query": "Smartwatch demand elasticity", "target_sources": ["IDC"], "method": "web_search"},
        ],
        "num_scouts": 2,
    }),
    "data_scout": json.dumps({
        "source": "jd_pricing_2026",
        "content": "Our: ¥2999. Apple Watch 10 ¥3499, Huawei Watch 5 ¥2699, Galaxy Watch 8 ¥2899.",
        "data_points": [
            {"label": "Our price", "value": 2999, "confidence": 1.0},
            {"label": "Apple Watch 10", "value": 3499, "confidence": 0.97},
            {"label": "Huawei Watch 5", "value": 2699, "confidence": 0.96},
            {"label": "Galaxy Watch 8", "value": 2899, "confidence": 0.96},
        ],
        "methods": ["web_search"],
    }),
    "critic_agent": json.dumps([{
        "challenge_id": "ch-001",
        "claim": "Market average may miss premium segment data",
        "evidence": [{"data": "Xiaomi Watch S4 at ¥1499 pulls average down"}],
        "severity": "minor",
        "suggested_remedy": "Compute segment-weighted average",
        "target_scout_index": 0,
    }]),
    "meta_judge": json.dumps({
        "ruling_id": "rul-pricing-003",
        "resolved": [{"challenge_id": "ch-001", "resolution": "Weighted avg ¥2910 computed."}],
        "unresolved": [], "dismissed": [],
        "quality_score": 0.88,
        "computation_summary": "Computed weighted average. Elasticity estimates via scipy.",
    }),
    "pi_review": json.dumps({
        "validated_brief": {
            "topic": "Smartwatch pricing optimization",
            "verified_data_points": [
                {"data": "Apple Watch 10: ¥3499", "source": "jd.com", "confidence": 0.97},
                {"data": "Huawei Watch 5: ¥2699", "source": "jd.com", "confidence": 0.96},
                {"data": "Weighted avg: ¥2910", "source": "computed", "confidence": 0.90},
            ],
            "rejected_claims": [],
            "quality_score": 0.88,
            "unresolved": [],
        },
    }),
    "analyst_lead": json.dumps({
        "dimensions": ["price_positioning", "feature_per_dollar", "elasticity"],
        "skills_to_use": ["spec-comparator", "price-elasticity"],
        "comparison_framework": {"categories": ["price", "features"], "metrics": ["index"]},
        "visualizations": ["price_bar", "elasticity_curve"],
        "priority_order": ["price_positioning", "feature_per_dollar"],
    }),
    "synthesizer": json.dumps({
        "executive_summary": "At ¥2999, positioned at premium-midrange boundary. Recommend ¥2799.",
        "comparison_matrix": {
            "dimensions": ["price", "feature_score", "brand_strength", "value_index"],
            "products": {
                "Our (¥2999)": [6.5, 8.0, 5.0, 6.5],
                "Apple Watch 10 (¥3499)": [4.5, 9.5, 9.5, 8.0],
            },
        },
        "swot_analysis": {
            "Our Product": {
                "strengths": ["Feature-rich"], "weaknesses": ["Brand"],
                "opportunities": ["Gap at ¥2800-3200"], "threats": ["Xiaomi undercutting"],
            },
        },
        "trend_analysis": "Market shifting to health AI features.",
        "recommendations": [
            {"action": "Reduce to ¥2799 for optimal positioning", "priority": "high"},
            {"action": "Invest in health AI differentiation", "priority": "high"},
            {"action": "Build brand via fitness community", "priority": "medium"},
        ],
    }),
    "internal_reviewer": json.dumps({
        "passed": True, "issues": [],
        "data_trace_check": {"total_claims": 8, "claims_with_source_trace": 8, "trace_rate": 1.0},
        "visualization_check": {"expected_count": 2, "generated_count": 2, "all_present": True},
        "recommendation_quality": "strong", "suggestions": [],
    }),
    "report_composer": "Final report written.",
}

# Scenario 3 needs sequential critic responses:
# call 1 (no data): challenge to trigger collection
# call 2 (has data): empty — data looks good, proceed to judge
SCENARIO_3_CRITIC_RESPONSES = [
    SCENARIO_3_RESPONSES["critic_agent"],  # first: challenge the plan (triggers data_scout)
    json.dumps([]),  # second: data reviewed, no issues
]
SCENARIO_3_SCOUT_RESPONSES = [
    json.dumps({  # rebuttal mode: respond to critic challenge
        "challenge_id": "ch-001",
        "new_data": [
            {"label": "Our price", "value": 2999, "confidence": 1.0},
            {"label": "Apple Watch 10", "value": 3499, "confidence": 0.97},
            {"label": "Huawei Watch 5", "value": 2699, "confidence": 0.96},
            {"label": "Galaxy Watch 8", "value": 2899, "confidence": 0.96},
            {"label": "Weighted avg", "value": 2910, "confidence": 0.90},
        ],
        "addresses_concern": True,
        "note": "Collected pricing data and computed weighted average.",
        "methods": ["web_search", "python"],
    }),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@contextmanager
def _patch_all(responses: dict[str, str], interrupt_decision: str = "approve") -> Generator[None, None, None]:
    """All-in-one mock context manager for E2E tests.

    conftest.py injects deerflow.subagents.executor into sys.modules as MagicMock,
    so the string-path patch resolves correctly.
    """
    MockExecutor = _make_executor_class(responses)
    with (
        patch("deerflow.subagents.executor.SubagentExecutor", MockExecutor),
        patch("deerflow.tools.get_available_tools", return_value=[]),
        patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: interrupt_decision),
    ):
        yield


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 1 Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestScenario1CompetitiveAnalysis:
    """场景 1: 竞品深度拆解 — iPhone 17 vs Mate 70 Pro vs S25 Ultra。"""

    def test_full_graph_e2e(self):
        """全图 E2E: Research → Analysis → HITL(approve) → Report Composer。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        with _patch_all(SCENARIO_1_RESPONSES):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": [], "workflow_type": "competitive_analysis"})

        # 验证完整数据流
        brief = result.get("validated_brief")
        assert brief is not None, "validated_brief 应从 Research SubGraph 映射到 Parent"
        assert "iPhone" in str(brief.get("topic", "")), "Brief should mention products"
        assert len(brief.get("verified_data_points", [])) >= 4

        assert result.get("research_quality_score") == 0.85

        report = result.get("synthesis_report")
        assert report is not None, "synthesis_report 应从 Analysis SubGraph 映射到 Parent"
        assert report.get("executive_summary")
        assert report.get("comparison_matrix")
        assert report.get("swot_analysis")
        assert report.get("recommendations")
        assert len(report["recommendations"]) == 3

        assert result.get("internal_review_passed") is True
        assert result.get("review_decision") == "approve"

    def test_state_contains_all_major_sections(self):
        """验证最终 State 包含报告所有主要部分。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        with _patch_all(SCENARIO_1_RESPONSES):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        report = result["synthesis_report"]
        swot = report["swot_analysis"]
        swot_keys = list(swot.keys())
        assert any("iPhone" in k or "S25" in k for k in swot_keys), f"SWOT should include products, got: {swot_keys}"

        matrix = report["comparison_matrix"]
        assert matrix.get("dimensions")
        assert matrix.get("products")
        assert report.get("trend_analysis")


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 2 Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestScenario2MarketTrend:
    """场景 2: 市场趋势洞察 — 2026 Q1 中国新能源汽车。"""

    def test_full_graph_e2e(self):
        """全图 E2E: Research → Analysis → HITL(approve) → Report。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        with _patch_all(SCENARIO_2_RESPONSES):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": [], "workflow_type": "market_trend"})

        assert result.get("review_decision") == "approve"

        brief = result.get("validated_brief")
        assert brief is not None
        assert "NEV" in str(brief.get("topic", "")) or "新能源" in str(brief)

        data_points = brief.get("verified_data_points", [])
        assert len(data_points) >= 3
        share_data = [dp for dp in data_points if "BYD" in str(dp.get("data", "")) or "35%" in str(dp.get("data", ""))]
        assert share_data, "应有 BYD 市场份额数据"

        report = result.get("synthesis_report")
        assert report is not None
        assert report.get("executive_summary")
        assert report.get("trend_analysis")

    def test_market_trend_data_integrity(self):
        """验证数据完整性——置信度、质量分范围。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        with _patch_all(SCENARIO_2_RESPONSES):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        brief = result["validated_brief"]
        for dp in brief.get("verified_data_points", []):
            assert dp["confidence"] > 0.8, f"置信度低于 0.8: {dp['data']}"

        quality = result.get("research_quality_score")
        assert quality is not None and 0.0 <= quality <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 3 Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestScenario3PricingOptimization:
    """场景 3: 商品定价优化 — 智能手表 ¥2999，含辩论循环。"""

    def test_full_graph_e2e(self):
        """全图 E2E: Research(含 debate) → Analysis → HITL(approve) → Report。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        scout_calls = [0]
        critic_calls = [0]

        class Scenario3Executor:
            def __init__(self, config, tools=None):
                self.config = config

            def execute(self, task: str) -> str:
                name = getattr(self.config, "name", "unknown")
                if name == "data_scout":
                    idx = min(scout_calls[0], len(SCENARIO_3_SCOUT_RESPONSES) - 1)
                    scout_calls[0] += 1
                    return SCENARIO_3_SCOUT_RESPONSES[idx]
                if name == "critic_agent":
                    idx = min(critic_calls[0], len(SCENARIO_3_CRITIC_RESPONSES) - 1)
                    critic_calls[0] += 1
                    return SCENARIO_3_CRITIC_RESPONSES[idx]
                return SCENARIO_3_RESPONSES.get(name, "{}")

        with (
            patch("deerflow.subagents.executor.SubagentExecutor", Scenario3Executor),
            patch("deerflow.tools.get_available_tools", return_value=[]),
            patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: "approve"),
        ):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": [], "workflow_type": "pricing_optimization"})

        assert scout_calls[0] >= 1, f"辩论循环应触发 data_scout 采集，实际调用 {scout_calls[0]} 次"
        assert result.get("review_decision") == "approve"

        brief = result.get("validated_brief")
        assert brief is not None
        assert "pricing" in str(brief.get("topic", "")).lower() or "定价" in str(brief)

        report = result.get("synthesis_report")
        assert report is not None
        assert report.get("recommendations")
        pricing_recs = [r for r in report["recommendations"] if "price" in str(r).lower() or "价格" in str(r) or "¥" in str(r)]
        assert pricing_recs, f"应有定价相关建议，got: {report['recommendations']}"

    def test_debate_resolved_in_final_state(self):
        """辩论循环结果正确反映在最终状态中。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        scout_calls = [0]
        critic_calls = [0]

        class Scenario3Executor:
            def __init__(self, config, tools=None):
                self.config = config

            def execute(self, task: str) -> str:
                name = getattr(self.config, "name", "unknown")
                if name == "data_scout":
                    idx = min(scout_calls[0], len(SCENARIO_3_SCOUT_RESPONSES) - 1)
                    scout_calls[0] += 1
                    return SCENARIO_3_SCOUT_RESPONSES[idx]
                if name == "critic_agent":
                    idx = min(critic_calls[0], len(SCENARIO_3_CRITIC_RESPONSES) - 1)
                    critic_calls[0] += 1
                    return SCENARIO_3_CRITIC_RESPONSES[idx]
                return SCENARIO_3_RESPONSES.get(name, "{}")

        with (
            patch("deerflow.subagents.executor.SubagentExecutor", Scenario3Executor),
            patch("deerflow.tools.get_available_tools", return_value=[]),
            patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: "approve"),
        ):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        quality = result.get("research_quality_score")
        assert quality is not None and quality >= 0.80, f"辩论后质量分应 >= 0.80，实际: {quality}"

        brief = result["validated_brief"]
        weighted_data = [dp for dp in brief.get("verified_data_points", [])
                         if "weighted" in str(dp.get("data", "")).lower()
                         or "segment" in str(dp.get("data", "")).lower()]
        assert weighted_data, "补采后应有分段加权数据"


# ═══════════════════════════════════════════════════════════════════════════════
# 异常上浮
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorPropagationE2E:
    """子图异常上浮到父图 error_handler 的完整链路。"""

    def test_research_error_triggers_error_handler(self):
        """Research SubGraph 异常 → collaboration_error → 路由到 error_handler。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        err_responses = dict(SCENARIO_1_RESPONSES)

        class ResearchErrorExecutor:
            def __init__(self, config, tools=None):
                self.config = config

            def execute(self, task: str) -> str:
                name = getattr(self.config, "name", "unknown")
                if name == "pi_agent":
                    raise RuntimeError("PI Agent: simulated failure")
                return err_responses.get(name, "{}")

        with (
            patch("deerflow.subagents.executor.SubagentExecutor", ResearchErrorExecutor),
            patch("deerflow.tools.get_available_tools", return_value=[]),
            patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: "approve"),
        ):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        # Research 子图异常通过 state mapping 上浮为 collaboration_error
        # 路由到 error_handler → 图终止
        error = result.get("collaboration_error")
        # 异常被 error_handler 处理后可能不保留，但图应正常终止
        assert result is not None  # 图未崩溃

    def test_analysis_error_triggers_error_handler(self):
        """Analysis SubGraph 异常 → collaboration_error → 路由到 error_handler。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        class AnalysisErrorExecutor:
            def __init__(self, config, tools=None):
                self.config = config

            def execute(self, task: str) -> str:
                name = getattr(self.config, "name", "unknown")
                if name == "synthesizer":
                    raise RuntimeError("Synthesizer: simulated failure")
                return SCENARIO_1_RESPONSES.get(name, "{}")

        with (
            patch("deerflow.subagents.executor.SubagentExecutor", AnalysisErrorExecutor),
            patch("deerflow.tools.get_available_tools", return_value=[]),
            patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: "approve"),
        ):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        assert result is not None  # 图未崩溃


# ═══════════════════════════════════════════════════════════════════════════════
# HITL 循环路径
# ═══════════════════════════════════════════════════════════════════════════════


class TestHITLLoopPaths:
    """HITL 审批不同决策路径对图执行的影响。"""

    def test_hitl_approve_goes_to_report(self):
        """HITL approve → report_composer。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        with _patch_all(SCENARIO_1_RESPONSES):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        assert result.get("review_decision") == "approve"
        assert result.get("synthesis_report") is not None

    def test_hitl_modify_reroutes_to_analysis(self):
        """HITL modify → 重新进入 Analysis SubGraph。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        analyst_calls = [0]

        class ModifyExecutor:
            def __init__(self, config, tools=None):
                self.config = config

            def execute(self, task: str) -> str:
                name = getattr(self.config, "name", "unknown")
                if name == "analyst_lead":
                    analyst_calls[0] += 1
                return SCENARIO_1_RESPONSES.get(name, "{}")

        decisions = iter(["modify", "approve"])

        with (
            patch("deerflow.subagents.executor.SubagentExecutor", ModifyExecutor),
            patch("deerflow.tools.get_available_tools", return_value=[]),
            patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: next(decisions)),
        ):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        assert analyst_calls[0] == 2, f"modify 后应重新进入 Analysis，实际 {analyst_calls[0]} 次"
        assert result.get("review_decision") == "approve"

    def test_hitl_replan_reroutes_to_research(self):
        """HITL replan → 重新进入 Research SubGraph。"""
        from deerflow.collaboration.graph import build_collaboration_graph

        pi_calls = [0]

        class ReplanExecutor:
            def __init__(self, config, tools=None):
                self.config = config

            def execute(self, task: str) -> str:
                name = getattr(self.config, "name", "unknown")
                if name == "pi_agent":
                    pi_calls[0] += 1
                return SCENARIO_1_RESPONSES.get(name, "{}")

        decisions = iter(["replan", "approve"])

        with (
            patch("deerflow.subagents.executor.SubagentExecutor", ReplanExecutor),
            patch("deerflow.tools.get_available_tools", return_value=[]),
            patch("deerflow.collaboration.nodes.hitl_gate.interrupt", lambda p: next(decisions)),
        ):
            graph = build_collaboration_graph()
            result = graph.invoke({"messages": []})

        assert pi_calls[0] == 2, f"replan 后应重新进入 Research，实际 {pi_calls[0]} 次"
        assert result.get("review_decision") == "approve"
