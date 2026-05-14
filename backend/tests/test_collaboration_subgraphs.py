"""Sprint 1 — SubGraph 独立编译 + State Mapping 纯函数单元测试。

验证三个图（Parent + Research + Analysis）可独立编译，
State Mapping 4 个纯函数正确性。
"""

from __future__ import annotations

import pytest

from deerflow.collaboration.state import (
    AnalysisSubGraphState,
    CollaborationState,
    ResearchSubGraphState,
)
from deerflow.collaboration.subgraphs.analysis_subgraph import build_analysis_subgraph
from deerflow.collaboration.subgraphs.research_subgraph import build_research_subgraph
from deerflow.collaboration.subgraphs.state_mapping import (
    map_analysis_to_parent,
    map_parent_to_analysis,
    map_parent_to_research,
    map_research_to_parent,
)


# ═══════════════════════════════════════════════════════════════════════════════
# State Schema 结构验证
# ═══════════════════════════════════════════════════════════════════════════════


class TestStateSchema:
    """验证三层 State TypedDict 的结构完整性。"""

    def test_collaboration_state_fields(self):
        """Parent State 包含所有必需字段。"""
        annotations = CollaborationState.__annotations__
        assert "validated_brief" in annotations
        assert "research_quality_score" in annotations
        assert "unresolved_issues" in annotations
        assert "synthesis_report" in annotations
        assert "review_decision" in annotations
        assert "collaboration_error" in annotations
        # 继承自 AgentState
        assert "messages" in annotations

    def test_research_subgraph_state_fields(self):
        """Research SubGraph State 包含对抗式批判相关字段。"""
        annotations = ResearchSubGraphState.__annotations__
        assert "research_plan" in annotations
        assert "scout_results" in annotations
        assert "challenges" in annotations
        assert "rebuttals" in annotations
        assert "debate_round" in annotations
        assert "ruling" in annotations
        assert "pi_override_log" in annotations
        assert "validated_brief" in annotations
        assert "error" in annotations

    def test_analysis_subgraph_state_fields(self):
        """Analysis SubGraph State 包含分析相关字段。"""
        annotations = AnalysisSubGraphState.__annotations__
        assert "validated_brief" in annotations
        assert "analysis_plan" in annotations
        assert "analysis_results" in annotations
        assert "synthesis_report" in annotations
        assert "internal_review_passed" in annotations
        assert "error" in annotations

    def test_state_isolation(self):
        """三层 State 的字段不互相污染。

        确保 Research 和 Analysis 的内部字段不会出现在对方 State 中。
        """
        research_fields = set(ResearchSubGraphState.__annotations__)
        analysis_fields = set(AnalysisSubGraphState.__annotations__)
        # 共享字段（设计如此）
        shared = {"messages", "validated_brief", "research_quality_score", "unresolved_issues", "error"}
        research_only = research_fields - shared
        analysis_only = analysis_fields - shared
        # Research 私有的对抗式批判字段不应出现在 Analysis 中
        research_specific = {"research_plan", "scout_results", "challenges", "rebuttals", "debate_round", "ruling", "pi_override_log"}
        for field in research_specific:
            assert field not in analysis_only, f"Research-specific field '{field}' leaked into AnalysisSubGraphState"


# ═══════════════════════════════════════════════════════════════════════════════
# SubGraph 独立编译
# ═══════════════════════════════════════════════════════════════════════════════


class TestSubGraphCompilation:
    """验证每个 SubGraph 可独立编译。"""

    def test_research_subgraph_compiles(self):
        """Research SubGraph 独立编译成功，节点和边正确连接。"""
        graph = build_research_subgraph()
        assert graph is not None
        nodes = graph.get_graph().nodes
        # 6 个节点已注册
        assert "pi_agent" in nodes
        assert "data_scout" in nodes
        assert "critic_agent" in nodes
        assert "meta_judge" in nodes
        assert "pi_review" in nodes
        assert "error_handler" in nodes

    def test_analysis_subgraph_compiles(self):
        """Analysis SubGraph 独立编译成功。"""
        graph = build_analysis_subgraph()
        assert graph is not None
        nodes = graph.get_graph().nodes
        assert "analyst_lead" in nodes
        assert "synthesizer" in nodes
        assert "internal_reviewer" in nodes
        assert "error_handler" in nodes

    def test_subgraphs_are_compiled(self):
        """SubGraph 返回的是 CompiledStateGraph，可以直接挂载到父图。"""
        research = build_research_subgraph()
        analysis = build_analysis_subgraph()
        # CompiledStateGraph 具有 get_graph() 方法
        assert hasattr(research, "get_graph")
        assert hasattr(analysis, "get_graph")


# ═══════════════════════════════════════════════════════════════════════════════
# State Mapping 纯函数 — Research ⇄ Parent
# ═══════════════════════════════════════════════════════════════════════════════


class TestResearchStateMapping:
    """测试 Research SubGraph ↔ Parent 的 State Mapping 纯函数。"""

    def test_map_research_to_parent_passes_validated_brief(self):
        """Research 的 validated_brief 正确映射到 Parent。"""
        child = _make_research_state(validated_brief={"key_finding": "test", "data_points": 5})
        parent = _make_parent_state()
        result = map_research_to_parent(child, parent)
        assert result["validated_brief"]["key_finding"] == "test"

    def test_map_research_to_parent_passes_quality_score(self):
        """Research 的 research_quality_score 正确映射。"""
        child = _make_research_state(research_quality_score=0.85)
        parent = _make_parent_state()
        result = map_research_to_parent(child, parent)
        assert result["research_quality_score"] == 0.85

    def test_map_research_to_parent_floats_error(self):
        """Research 的 error → Parent 的 collaboration_error。"""
        child = _make_research_state(error="Scout: connection timeout")
        parent = _make_parent_state()
        result = map_research_to_parent(child, parent)
        assert result["collaboration_error"] == "Scout: connection timeout"

    def test_map_research_to_parent_no_internal_leak(self):
        """Research 内部字段（challenges/rebuttals）不泄露到 Parent。"""
        child: ResearchSubGraphState = {  # type: ignore[typeddict-unknown-key]
            "messages": [],
            "challenges": [{"claim": "data suspicious"}],  # type: ignore[typeddict-unknown-key]
            "rebuttals": [{"response": "verified"}],  # type: ignore[typeddict-unknown-key]
            "debate_round": 2,
        }
        parent = _make_parent_state()
        result = map_research_to_parent(child, parent)
        assert "challenges" not in result
        assert "rebuttals" not in result
        assert "debate_round" not in result

    def test_map_research_to_parent_is_pure(self):
        """State Mapping 是纯函数：不修改输入参数。"""
        child = _make_research_state(validated_brief={"data": 1})
        parent = _make_parent_state()
        parent_copy = dict(parent)  # type: ignore[typeddict-unknown-key]
        child_copy = dict(child)  # type: ignore[typeddict-unknown-key]

        map_research_to_parent(child, parent)

        assert dict(parent) == parent_copy, "parent_state 被修改了！"  # type: ignore[typeddict-unknown-key]
        assert dict(child) == child_copy, "child_state 被修改了！"  # type: ignore[typeddict-unknown-key]

    def test_map_parent_to_research_is_pure(self):
        """map_parent_to_research 是纯函数。"""
        parent = _make_parent_state(workflow_type="competitive_analysis", max_scouts=3)
        parent_copy = dict(parent)  # type: ignore[typeddict-unknown-key]

        map_parent_to_research(parent)

        assert dict(parent) == parent_copy, "parent_state 被修改了！"  # type: ignore[typeddict-unknown-key]

    def test_map_parent_to_research_passes_config(self):
        """Parent 的工作流配置正确传入 Research。"""
        parent = _make_parent_state(workflow_type="competitive_analysis", max_scouts=3)
        result = map_parent_to_research(parent)
        assert result["workflow_type"] == "competitive_analysis"  # type: ignore[typeddict-unknown-key]
        assert result["max_scouts"] == 3  # type: ignore[typeddict-unknown-key]


# ═══════════════════════════════════════════════════════════════════════════════
# State Mapping 纯函数 — Analysis ⇄ Parent
# ═══════════════════════════════════════════════════════════════════════════════


class TestAnalysisStateMapping:
    """测试 Analysis SubGraph ↔ Parent 的 State Mapping 纯函数。"""

    def test_map_parent_to_analysis_receives_brief(self):
        """Analysis 接收到 Parent 中的 validated_brief。"""
        parent = _make_parent_state(validated_brief={"finding": "important"}, research_quality_score=0.9)
        result = map_parent_to_analysis(parent)
        assert result["validated_brief"]["finding"] == "important"
        assert result["research_quality_score"] == 0.9

    def test_map_parent_to_analysis_receives_unresolved(self):
        """Analysis 接收到未解决问题列表。"""
        parent = _make_parent_state(unresolved_issues=[{"issue": "conflicting_data"}])
        result = map_parent_to_analysis(parent)
        assert len(result["unresolved_issues"]) == 1  # type: ignore[arg-type]

    def test_map_analysis_to_parent_passes_report(self):
        """Analysis 的 synthesis_report 正确映射到 Parent。"""
        child: AnalysisSubGraphState = {  # type: ignore[typeddict-unknown-key]
            "messages": [],
            "synthesis_report": {"comparison_matrix": {}, "swot": {}},  # type: ignore[typeddict-unknown-key]
            "internal_review_passed": True,  # type: ignore[typeddict-unknown-key]
        }
        parent = _make_parent_state()
        result = map_analysis_to_parent(child, parent)
        assert result["synthesis_report"]["comparison_matrix"] == {}
        assert result["internal_review_passed"] is True

    def test_map_analysis_to_parent_floats_error(self):
        """Analysis 的 error → Parent 的 collaboration_error。"""
        child: AnalysisSubGraphState = {  # type: ignore[typeddict-unknown-key]
            "messages": [],
            "internal_review_passed": False,  # type: ignore[typeddict-unknown-key]
            "error": "Synthesizer: skill execution failed",  # type: ignore[typeddict-unknown-key]
        }
        parent = _make_parent_state()
        result = map_analysis_to_parent(child, parent)
        assert result["collaboration_error"] == "Synthesizer: skill execution failed"

    def test_map_analysis_to_parent_no_internal_leak(self):
        """Analysis 内部字段（analysis_plan/results）不泄露到 Parent。"""
        child: AnalysisSubGraphState = {  # type: ignore[typeddict-unknown-key]
            "messages": [],
            "analysis_plan": {"dimensions": ["price", "features"]},  # type: ignore[typeddict-unknown-key]
            "analysis_results": [{"dimension": "price", "data": "..."}],  # type: ignore[typeddict-unknown-key]
        }
        parent = _make_parent_state()
        result = map_analysis_to_parent(child, parent)
        assert "analysis_plan" not in result
        assert "analysis_results" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# State Mapping 纯函数 — 空值处理
# ═══════════════════════════════════════════════════════════════════════════════


class TestStateMappingEmptyValues:
    """验证 State Mapping 正确处理 None/空值——不向返回 dict 写入不必要字段。"""

    def test_map_research_empty_state(self):
        """空的 Research State 映射返回空 dict。"""
        child: ResearchSubGraphState = {"messages": []}  # type: ignore[typeddict-unknown-key]
        parent = _make_parent_state()
        result = map_research_to_parent(child, parent)
        assert result == {}  # 不写入任何字段

    def test_map_parent_empty_state(self):
        """空的 Parent State 映射返回空 dict。"""
        parent: CollaborationState = {"messages": []}  # type: ignore[typeddict-unknown-key]
        result = map_parent_to_analysis(parent)
        assert result == {}

    def test_map_analysis_empty_state(self):
        """空的 Analysis State 映射返回空 dict。"""
        child: AnalysisSubGraphState = {"messages": []}  # type: ignore[typeddict-unknown-key]
        parent = _make_parent_state()
        result = map_analysis_to_parent(child, parent)
        assert result == {}

    def test_none_values_not_written(self):
        """None 值不应写入返回 dict——只写有意义的值。"""
        child = _make_research_state(
            validated_brief=None,
            research_quality_score=None,
            error=None,
        )
        parent = _make_parent_state()
        result = map_research_to_parent(child, parent)
        assert "validated_brief" not in result
        assert "research_quality_score" not in result
        assert "collaboration_error" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# 测试辅助函数
# ═══════════════════════════════════════════════════════════════════════════════


def _make_parent_state(**overrides) -> CollaborationState:
    """创建 Parent State 的测试辅助。"""
    base: dict = {
        "messages": [],
    }
    base.update(overrides)
    return base  # type: ignore[return-value]


def _make_research_state(**overrides) -> ResearchSubGraphState:
    """创建 Research SubGraph State 的测试辅助。"""
    base: dict = {
        "messages": [],
    }
    base.update(overrides)
    return base  # type: ignore[return-value]
