"""Sprint 2 — Protocol messages + DebateState + Prompt validation tests.

测试对抗式批判协议数据结构和状态机的正确性。
"""

from __future__ import annotations

import pytest

from deerflow.collaboration.protocols.debate import (
    MAX_DEBATE_ROUNDS,
    DebatePhase,
    DebateState,
    create_debate_state,
)
from deerflow.collaboration.protocols.messages import Challenge, Rebuttal, Ruling, Severity, Verdict


# ═══════════════════════════════════════════════════════════════════════════════
# Protocol Messages — 数据结构验证
# ═══════════════════════════════════════════════════════════════════════════════


class TestChallengeMessage:
    """验证 Challenge 数据结构的创建和约束。"""

    def test_create_challenge(self):
        """Challenge 创建成功，所有字段可访问。"""
        c = Challenge(
            challenge_id="ch-001",
            claim="数据源冲突：Scout A 价格与 IDC 不一致",
            evidence=[{"type": "source_conflict", "source": "IDC 2026Q1", "data": "$7199", "vs": "apple.com $6999"}],
            severity=Severity.MAJOR,
            suggested_remedy="重新抓取 apple.com/pricing，检查地区差异",
        )
        assert c.challenge_id == "ch-001"
        assert c.severity == Severity.MAJOR
        assert len(c.evidence) == 1
        assert c.target_scout_index is None

    def test_challenge_critical_severity(self):
        """Critical 级别 challenge 创建。"""
        c = Challenge(
            challenge_id="ch-crit",
            claim="核心数据源不可访问",
            evidence=[],
            severity=Severity.CRITICAL,
            suggested_remedy="寻找替代数据源",
        )
        assert c.severity == Severity.CRITICAL

    def test_challenge_minor_severity(self):
        """Minor 级别不阻塞流程。"""
        c = Challenge(
            challenge_id="ch-minor",
            claim="数据时间戳格式不一致",
            evidence=[{"type": "timeliness", "data": "timestamp in UTC vs CST"}],
            severity=Severity.MINOR,
            suggested_remedy="统一时区格式",
        )
        assert c.severity == Severity.MINOR


class TestRebuttalMessage:
    """验证 Rebuttal 数据结构。"""

    def test_create_rebuttal(self):
        """Rebuttal 创建成功。"""
        r = Rebuttal(
            rebuttal_id="rb-001",
            challenge_id="ch-001",
            new_data=[{"source": "apple.com", "price": "$6999", "region": "US"}],
            addresses_concern=True,
            methods=["web_fetch", "python"],
        )
        assert r.rebuttal_id == "rb-001"
        assert r.challenge_id == "ch-001"
        assert r.addresses_concern is True
        assert len(r.methods) == 2

    def test_rebuttal_not_addressing_concern(self):
        """Scout 尝试了但无法解决质疑。"""
        r = Rebuttal(
            rebuttal_id="rb-002",
            challenge_id="ch-001",
            new_data=[],
            addresses_concern=False,
            note="数据源已下线，无法获取",
        )
        assert r.addresses_concern is False
        assert r.note != ""


class TestRulingMessage:
    """验证 Ruling 数据结构。"""

    def test_create_ruling(self):
        """Ruling 创建成功。"""
        r = Ruling(
            ruling_id="rul-001",
            resolved=["ch-001", "ch-003"],
            unresolved=[{"challenge_id": "ch-002", "issue": "数据源不可访问", "reason": "无替代源"}],
            dismissed=[],
            quality_score=0.85,
            computation_summary="交叉验证: 3/4 来源一致, Cohen's κ=0.78",
        )
        assert r.ruling_id == "rul-001"
        assert len(r.resolved) == 2
        assert len(r.unresolved) == 1
        assert r.quality_score == 0.85

    def test_all_resolved_true(self):
        """所有 challenge 已解决。"""
        r = Ruling(ruling_id="rul-ok", resolved=["ch-001"], unresolved=[])
        assert r.all_challenges_resolved() is True

    def test_all_resolved_false(self):
        """仍有未解决问题。"""
        r = Ruling(
            ruling_id="rul-bad",
            resolved=["ch-001"],
            unresolved=[{"challenge_id": "ch-002", "issue": "...", "reason": "..."}],
        )
        assert r.all_challenges_resolved() is False


# ═══════════════════════════════════════════════════════════════════════════════
# DebateState — 状态机验证
# ═══════════════════════════════════════════════════════════════════════════════


class TestDebateStateLifecycle:
    """验证 DebateState 完整生命周期。"""

    def test_initial_state(self):
        """初始状态：IDLE, round=0。"""
        ds = create_debate_state()
        assert ds.phase == DebatePhase.IDLE
        assert ds.current_round == 0
        assert ds.can_continue is True
        assert ds.has_challenges is False
        assert ds.needs_rebuttal() is False

    def test_full_debate_flow(self):
        """完整流程：质疑 → 补采 → 裁决 → 完成。"""
        ds = create_debate_state()
        c = Challenge(
            challenge_id="ch-001",
            claim="数据冲突",
            evidence=[{"type": "source_conflict", "source": "A", "data": "X", "vs": "Y"}],
            severity=Severity.MAJOR,
            suggested_remedy="补采",
        )

        # 1. 质疑
        pending = ds.advance_to_critique([c])
        assert ds.phase == DebatePhase.CRITIQUING
        assert ds.current_round == 1
        assert len(pending) == 1  # major 级别需要补采
        assert ds.needs_rebuttal() is True

        # 2. 补采
        rb = Rebuttal(rebuttal_id="rb-001", challenge_id="ch-001", new_data=[{"ok": True}], addresses_concern=True)
        ds.advance_to_rebuttal([rb])
        assert ds.phase == DebatePhase.REBUTTAL
        assert len(ds.rebuttals) == 1

        # 3. 裁决
        remaining = ds.advance_to_adjudication()
        assert ds.phase == DebatePhase.ADJUDICATING
        assert remaining == 0  # 全部回应

        # 4. 完成
        ruling = Ruling(ruling_id="rul-ok", resolved=["ch-001"], quality_score=0.9)
        unresolved_count = ds.complete(ruling)
        assert ds.phase == DebatePhase.COMPLETE
        assert unresolved_count == 0

    def test_minor_challenges_skipped_in_pending(self):
        """Minor 级别的 challenge 不进入补采队列。"""
        ds = create_debate_state()
        c = Challenge(
            challenge_id="ch-minor",
            claim="小问题",
            evidence=[],
            severity=Severity.MINOR,
            suggested_remedy="可忽略",
        )
        pending = ds.advance_to_critique([c])
        assert len(pending) == 0  # minor 不强制补采

    def test_max_rounds_enforced(self):
        """第 2 轮后不能继续质疑。"""
        ds = create_debate_state()
        c = Challenge(challenge_id="ch-001", claim="test", evidence=[], severity=Severity.MAJOR, suggested_remedy="x")

        ds.advance_to_critique([c])  # round 1
        ds.current_round = 2  # 模拟到第 2 轮
        assert ds.can_continue is False

    def test_advance_to_critique_beyond_max_raises(self):
        """超过最大轮次调用 advance_to_critique 抛出 ValueError。"""
        ds = create_debate_state()
        c = Challenge(challenge_id="ch-001", claim="test", evidence=[], severity=Severity.MAJOR, suggested_remedy="x")

        ds.advance_to_critique([c])  # round 1
        ds.current_round = MAX_DEBATE_ROUNDS  # 已满

        with pytest.raises(ValueError, match="最大轮次"):
            ds.advance_to_critique([c])

    def test_needs_rebuttal_false_when_no_challenges(self):
        """无质疑时无需补采。"""
        ds = create_debate_state()
        assert ds.needs_rebuttal() is False

    def test_needs_rebuttal_false_when_all_rebutted(self):
        """所有质疑已回应时无需补采。"""
        ds = create_debate_state()
        c = Challenge(challenge_id="ch-001", claim="test", evidence=[], severity=Severity.MAJOR, suggested_remedy="x")
        ds.advance_to_critique([c])
        rb = Rebuttal(rebuttal_id="rb-001", challenge_id="ch-001", new_data=[], addresses_concern=True)
        ds.advance_to_rebuttal([rb])
        assert ds.needs_rebuttal() is False


# ═══════════════════════════════════════════════════════════════════════════════
# Prompts — 提示词验证
# ═══════════════════════════════════════════════════════════════════════════════


class TestPrompts:
    """验证 4 个角色提示词的正确性。"""

    def test_pi_prompt_loaded(self):
        """PI 提示词包含关键权限信息。"""
        from deerflow.collaboration.prompts import PI_AGENT_PROMPT

        assert "PI Agent" in PI_AGENT_PROMPT
        assert "Forbidden" in PI_AGENT_PROMPT  # 权限约束
        assert "validated_brief" in PI_AGENT_PROMPT  # 输出格式

    def test_scout_prompt_loaded(self):
        """Scout 提示词包含工具和约束。"""
        from deerflow.collaboration.prompts import DATA_SCOUT_PROMPT

        assert "Data Scout" in DATA_SCOUT_PROMPT
        assert "Forbidden" in DATA_SCOUT_PROMPT
        assert "source" in DATA_SCOUT_PROMPT

    def test_critic_prompt_loaded(self):
        """Critic 提示词包含证据要求。"""
        from deerflow.collaboration.prompts import CRITIC_AGENT_PROMPT

        assert "Critic Agent" in CRITIC_AGENT_PROMPT
        assert "evidence" in CRITIC_AGENT_PROMPT.lower()
        assert "challenge" in CRITIC_AGENT_PROMPT.lower()

    def test_judge_prompt_loaded(self):
        """Judge 提示词包含计算验证要求。"""
        from deerflow.collaboration.prompts import META_JUDGE_PROMPT

        assert "Meta-Judge" in META_JUDGE_PROMPT
        assert "computation" in META_JUDGE_PROMPT.lower()
        assert "quality_score" in META_JUDGE_PROMPT
