"""Sprint 2 — Research SubGraph node unit tests.

Mock SubagentExecutor to verify node input/output contracts without real LLM calls.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from deerflow.collaboration.state import ResearchSubGraphState


# ═══════════════════════════════════════════════════════════════════════════════
# Mock SubagentExecutor — 避免实际 LLM 调用
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock SubagentExecutor 和 get_available_tools，避免实际依赖。"""
    mock_executor = MagicMock()
    mock_executor.return_value.execute.return_value = '{"result": "mocked"}'

    mock_tools = MagicMock()
    mock_tools.return_value = [MagicMock()]

    with (
        patch("deerflow.subagents.executor.SubagentExecutor", mock_executor),
        patch("deerflow.tools.get_available_tools", mock_tools),
    ):
        yield {"executor": mock_executor, "tools": mock_tools}


def _make_state(**overrides) -> ResearchSubGraphState:
    """构建测试用 ResearchSubGraphState。"""
    base: dict = {"messages": []}
    base.update(overrides)
    return base  # type: ignore[return-value]


# ═══════════════════════════════════════════════════════════════════════════════
# PI Agent Node
# ═══════════════════════════════════════════════════════════════════════════════


class TestPIAgentNode:
    def test_returns_research_plan(self, mock_dependencies):
        """PI 节点返回 research_plan。"""
        from deerflow.collaboration.nodes.research_nodes import pi_agent_node

        state = _make_state()
        result = pi_agent_node(state)
        assert "research_plan" in result

    def test_handles_executor_error(self, mock_dependencies):
        """PI 节点处理异常。"""
        from deerflow.collaboration.nodes.research_nodes import pi_agent_node

        mock_dependencies["executor"].return_value.execute.side_effect = RuntimeError("Subagent crash")
        state = _make_state()
        result = pi_agent_node(state)
        assert "error" in result
        assert "PI Agent" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# Data Scout Node
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataScoutNode:
    def test_returns_scout_results_in_collection_mode(self, mock_dependencies):
        """首次采集模式返回 scout_results。"""
        from deerflow.collaboration.nodes.research_nodes import data_scout_node

        state = _make_state(research_plan={"topic": "test"})
        result = data_scout_node(state)
        assert "scout_results" in result

    def test_returns_rebuttals_in_rebuttal_mode(self, mock_dependencies):
        """补采模式返回 rebuttals。"""
        from deerflow.collaboration.nodes.research_nodes import data_scout_node

        state = _make_state(
            challenges=[{"challenge_id": "ch-001", "claim": "conflict"}],
            rebuttals=[],
        )
        result = data_scout_node(state)
        assert "rebuttals" in result

    def test_handles_executor_error(self, mock_dependencies):
        """Scout 节点处理异常。"""
        from deerflow.collaboration.nodes.research_nodes import data_scout_node

        mock_dependencies["executor"].return_value.execute.side_effect = RuntimeError("Network timeout")
        state = _make_state()
        result = data_scout_node(state)
        assert "error" in result
        assert "Data Scout" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# Critic Agent Node
# ═══════════════════════════════════════════════════════════════════════════════


class TestCriticAgentNode:
    def test_returns_challenges(self, mock_dependencies):
        """Critic 返回 challenges 列表。"""
        from deerflow.collaboration.nodes.research_nodes import critic_agent_node

        state = _make_state(scout_results=[{"data": "test"}])
        result = critic_agent_node(state)
        assert "challenges" in result
        assert "debate_round" in result

    def test_empty_scout_results_returns_empty_challenges(self, mock_dependencies):
        """无 scout_results 时返回空列表。"""
        from deerflow.collaboration.nodes.research_nodes import critic_agent_node

        state = _make_state(scout_results=[])
        result = critic_agent_node(state)
        assert result["challenges"] == []

    def test_handles_executor_error(self, mock_dependencies):
        """Critic 节点处理异常。"""
        from deerflow.collaboration.nodes.research_nodes import critic_agent_node

        mock_dependencies["executor"].return_value.execute.side_effect = RuntimeError("LLM timeout")
        state = _make_state(scout_results=[{"data": "test"}])
        result = critic_agent_node(state)
        assert "error" in result
        assert "Critic Agent" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# Meta-Judge Node
# ═══════════════════════════════════════════════════════════════════════════════


class TestMetaJudgeNode:
    def test_returns_ruling_and_quality_score(self, mock_dependencies):
        """Meta-Judge 返回 ruling 和 quality_score。"""
        from deerflow.collaboration.nodes.research_nodes import meta_judge_node

        state = _make_state(
            scout_results=[{"data": "test"}],
            challenges=[{"challenge_id": "ch-001"}],
            rebuttals=[{"challenge_id": "ch-001", "addresses_concern": True}],
        )
        result = meta_judge_node(state)
        assert "ruling" in result
        assert "research_quality_score" in result

    def test_handles_executor_error(self, mock_dependencies):
        """Meta-Judge 节点处理异常。"""
        from deerflow.collaboration.nodes.research_nodes import meta_judge_node

        mock_dependencies["executor"].return_value.execute.side_effect = RuntimeError("Computation error")
        state = _make_state()
        result = meta_judge_node(state)
        assert "error" in result
        assert "Meta-Judge" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# PI Review Node
# ═══════════════════════════════════════════════════════════════════════════════


class TestPIReviewNode:
    def test_returns_validated_brief(self, mock_dependencies):
        """PI Review 返回 validated_brief。"""
        from deerflow.collaboration.nodes.research_nodes import pi_review_node

        state = _make_state(
            ruling={"quality_score": 0.85, "resolved": ["ch-001"]},
        )
        result = pi_review_node(state)
        assert "validated_brief" in result

    def test_handles_executor_error(self, mock_dependencies):
        """PI Review 节点处理异常。"""
        from deerflow.collaboration.nodes.research_nodes import pi_review_node

        mock_dependencies["executor"].return_value.execute.side_effect = RuntimeError("Review crash")
        state = _make_state()
        result = pi_review_node(state)
        assert "error" in result
        assert "PI Review" in result["error"]


# ═══════════════════════════════════════════════════════════════════════════════
# Error Handler Node
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorHandlerNode:
    def test_returns_empty_dict(self):
        """Error handler 返回空 dict——错误已在 state.error 中。"""
        from deerflow.collaboration.nodes.research_nodes import error_handler_node

        state = _make_state(error="Something went wrong")
        result = error_handler_node(state)
        assert result == {}

    def test_handles_missing_error_field(self):
        """无 error 字段也能运行。"""
        from deerflow.collaboration.nodes.research_nodes import error_handler_node

        state = _make_state()
        result = error_handler_node(state)
        assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# Node Integration — 节点间数据传递
# ═══════════════════════════════════════════════════════════════════════════════


class TestNodeDataFlow:
    """验证节点间通过 State dict 传递数据的契约。"""

    def test_pi_output_consumable_by_critic(self, mock_dependencies):
        """PI 输出的 research_plan 可被 Critic 节点消费。"""
        from deerflow.collaboration.nodes.research_nodes import critic_agent_node, pi_agent_node

        state = _make_state()
        pi_result = pi_agent_node(state)

        # PI 输出写入 state
        updated_state = _make_state(**pi_result)
        # Critic 可以正常消费
        critic_result = critic_agent_node(updated_state)
        assert "challenges" in critic_result

    def test_critic_output_consumable_by_scout(self, mock_dependencies):
        """Critic 输出的 challenges 可被 Scout 消费（补采模式）。"""
        from deerflow.collaboration.nodes.research_nodes import critic_agent_node, data_scout_node

        state = _make_state(scout_results=[{"data": "test"}])
        critic_result = critic_agent_node(state)

        updated_state = _make_state(**critic_result, scout_results=[{"data": "test"}])
        scout_result = data_scout_node(updated_state)
        assert "rebuttals" in scout_result or "scout_results" in scout_result

    def test_judge_output_consumable_by_pi_review(self, mock_dependencies):
        """Meta-Judge 输出的 ruling 可被 PI Review 消费。"""
        from deerflow.collaboration.nodes.research_nodes import meta_judge_node, pi_review_node

        state = _make_state(
            scout_results=[{"data": "test"}],
            challenges=[{"challenge_id": "ch-001"}],
            rebuttals=[{"challenge_id": "ch-001", "addresses_concern": True}],
        )
        judge_result = meta_judge_node(state)

        updated_state = _make_state(**judge_result)
        review_result = pi_review_node(updated_state)
        assert "validated_brief" in review_result
