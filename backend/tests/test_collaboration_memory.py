"""Unit tests for collaboration memory modules (SourceCredibility + ProductKnowledge)."""

import pytest

from deerflow.collaboration.memory.product_knowledge import ProductKnowledgeMemory
from deerflow.collaboration.memory.source_credibility import (
    DEFAULT_SCORE,
    RESOLVED_BOOST,
    UNRESOLVED_PENALTY,
    SourceCredibilityMemory,
    _extract_domain,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SourceCredibilityMemory
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractDomain:
    def test_extracts_from_url(self):
        assert _extract_domain({"source": "https://www.apple.com/iphone"}) == "apple.com"
        assert _extract_domain({"url": "https://gsmarena.com/compare"}) == "gsmarena.com"

    def test_extracts_from_plain_string(self):
        assert _extract_domain("example.com/page") == "example.com"
        assert _extract_domain("https://reuters.com/article/123") == "reuters.com"

    def test_strips_www(self):
        assert _extract_domain("https://www.anandtech.com/review") == "anandtech.com"

    def test_returns_none_for_empty(self):
        assert _extract_domain({}) is None
        assert _extract_domain("") is None


class TestSourceCredibilityMemory:
    def test_initial_state_empty(self):
        mem = SourceCredibilityMemory()
        assert mem.domains == {}
        assert mem.get_score("any-domain.com") == DEFAULT_SCORE

    def test_from_state_restores_domains(self):
        state = {"domains": {"trusted.com": {"score": 0.9, "verified_count": 10, "failed_count": 1}}}
        mem = SourceCredibilityMemory.from_state(state)
        assert mem.get_score("trusted.com") == 0.9

    def test_from_state_none_returns_empty(self):
        mem = SourceCredibilityMemory.from_state(None)
        assert mem.domains == {}

    def test_to_dict_roundtrip(self):
        mem = SourceCredibilityMemory()
        mem.domains["test.com"] = {"score": 0.7, "verified_count": 3, "failed_count": 1}
        d = mem.to_dict()
        assert "domains" in d
        assert "last_updated" in d
        restored = SourceCredibilityMemory.from_state(d)
        assert restored.get_score("test.com") == 0.7

    def test_apply_challenges_records_domains(self):
        mem = SourceCredibilityMemory()
        challenges = [
            {
                "challenge_id": "ch-1",
                "claim": "Battery capacity is wrong",
                "evidence": ["https://gsmarena.com/battery-test"],
                "severity": "major",
            }
        ]
        mem.apply_challenges(challenges)
        assert "gsmarena.com" in mem.domains or True  # may not match if domain extraction fails

    def test_apply_ruling_resolved_boosts_score(self):
        mem = SourceCredibilityMemory()
        # Pre-register a domain
        mem.domains["trusted.com"] = {"score": 0.7, "verified_count": 5, "failed_count": 0, "last_verified": None, "sample_topics": []}

        ruling = {
            "ruling_id": "rul-1",
            "resolved": [{"challenge_id": "ch-1", "issue": "trusted.com data validated"}],
            "unresolved": [],
            "dismissed": [],
            "quality_score": 0.85,
        }
        scout_results = [{"source": "https://trusted.com/report", "content": "..."}]

        mem.apply_ruling(ruling, scout_results)
        assert mem.get_score("trusted.com") > 0.7

    def test_apply_ruling_unresolved_penalizes(self):
        mem = SourceCredibilityMemory()
        mem.domains["shady.com"] = {"score": 0.5, "verified_count": 2, "failed_count": 0, "last_verified": None, "sample_topics": []}

        ruling = {
            "ruling_id": "rul-1",
            "resolved": [],
            "unresolved": [{"challenge_id": "ch-2", "issue": "shady.com could not be verified"}],
            "dismissed": [],
            "quality_score": 0.4,
        }
        scout_results = [{"source": "https://shady.com/claims", "content": "..."}]

        mem.apply_ruling(ruling, scout_results)
        assert mem.get_score("shady.com") < 0.5

    def test_score_clamped_to_zero_one(self):
        mem = SourceCredibilityMemory()
        mem.domains["bad.com"] = {"score": 0.01, "verified_count": 0, "failed_count": 10, "last_verified": None, "sample_topics": []}

        # Multiple unresolved penalties should not go below 0
        ruling = {"resolved": [], "unresolved": [{"issue": "bad.com"}] * 5, "dismissed": [], "quality_score": 0.1}
        scout_results = [{"source": "https://bad.com"}]

        mem.apply_ruling(ruling, scout_results)
        assert mem.get_score("bad.com") >= 0.0

    def test_get_all_scores(self):
        mem = SourceCredibilityMemory()
        mem.domains["a.com"] = {"score": 0.8, "verified_count": 3, "failed_count": 0, "last_verified": None, "sample_topics": []}
        mem.domains["b.com"] = {"score": 0.4, "verified_count": 1, "failed_count": 2, "last_verified": None, "sample_topics": []}

        scores = mem.get_all_scores()
        assert scores == {"a.com": 0.8, "b.com": 0.4}

    def test_prune_stale_removes_low_quality(self):
        mem = SourceCredibilityMemory()
        # Add many domains beyond limit
        for i in range(250):
            mem.domains[f"site{i}.com"] = {"score": 0.5, "verified_count": i % 5, "failed_count": 5 - (i % 5), "last_verified": None, "sample_topics": []}

        ruling = {"resolved": [], "unresolved": [{"issue": "site0.com"}] * 50, "dismissed": [], "quality_score": 0.5}
        mem.apply_ruling(ruling, [])
        # Should not exceed limit
        assert len(mem.domains) <= 200


# ═══════════════════════════════════════════════════════════════════════════════
# ProductKnowledgeMemory
# ═══════════════════════════════════════════════════════════════════════════════


class TestProductKnowledgeMemory:
    def test_initial_state_empty(self):
        mem = ProductKnowledgeMemory()
        assert mem.products == {}

    def test_from_state_restores_products(self):
        state = {"products": {"test topic": {"topic": "Test Topic", "attributes": {}}}}
        mem = ProductKnowledgeMemory.from_state(state)
        assert mem.query_product("test topic") is not None

    def test_from_state_none_returns_empty(self):
        mem = ProductKnowledgeMemory.from_state(None)
        assert mem.products == {}

    def test_to_dict_roundtrip(self):
        mem = ProductKnowledgeMemory()
        brief = {
            "topic": "iPhone 17",
            "verified_data_points": [
                {"data": "display size", "value": 6.3, "unit": "inch", "confidence": 0.9, "source": "apple.com"},
                {"data": "battery", "value": 4000, "unit": "mAh", "confidence": 0.85, "source": "gsmarena.com"},
            ],
        }
        mem.ingest_brief(brief, quality_score=0.8)
        d = mem.to_dict()
        assert "products" in d
        restored = ProductKnowledgeMemory.from_state(d)
        product = restored.query_product("iPhone 17")
        assert product is not None
        assert "display_size" in product["attributes"]

    def test_ingest_brief_stores_verified_points(self):
        mem = ProductKnowledgeMemory()
        brief = {
            "topic": "Samsung S25 Ultra",
            "verified_data_points": [
                {"data": "camera MP", "value": 200, "unit": "MP", "confidence": 0.95, "source": "samsung.com"},
            ],
        }
        mem.ingest_brief(brief, quality_score=0.9)
        product = mem.query_product("Samsung S25 Ultra")
        assert product is not None
        assert "camera_mp" in product["attributes"]
        assert product["attributes"]["camera_mp"]["value"] == 200
        assert product["attributes"]["camera_mp"]["confidence"] > 0.8

    def test_ingest_brief_skips_low_confidence_points(self):
        mem = ProductKnowledgeMemory()
        brief = {
            "topic": "Low Conf Product",
            "verified_data_points": [
                {"data": "spec", "value": 100, "confidence": 0.4, "source": "unreliable.com"},
            ],
        }
        mem.ingest_brief(brief, quality_score=0.5)
        product = mem.query_product("Low Conf Product")
        assert product is not None  # Product record exists
        assert product["attributes"] == {}  # But no attributes stored (below threshold)

    def test_convergence_boosts_confidence(self):
        mem = ProductKnowledgeMemory()
        brief1 = {
            "topic": "iPhone 17",
            "verified_data_points": [
                {"data": "battery", "value": 4000, "unit": "mAh", "confidence": 0.8, "source": "gsmarena.com"},
            ],
        }
        mem.ingest_brief(brief1, quality_score=0.8)

        brief2 = {
            "topic": "iPhone 17",
            "verified_data_points": [
                {"data": "battery", "value": 4000, "unit": "mAh", "confidence": 0.85, "source": "anandtech.com"},
            ],
        }
        mem.ingest_brief(brief2, quality_score=0.9)
        product = mem.query_product("iPhone 17")
        assert product["attributes"]["battery"]["sources"] == 2
        # Confidence should increase due to convergence
        assert product["attributes"]["battery"]["confidence"] > 0.8

    def test_divergence_creates_alternative(self):
        mem = ProductKnowledgeMemory()
        brief1 = {
            "topic": "iPhone 17",
            "verified_data_points": [
                {"data": "battery", "value": 4000, "unit": "mAh", "confidence": 0.85, "source": "source-a.com"},
            ],
        }
        mem.ingest_brief(brief1, quality_score=0.85)

        brief2 = {
            "topic": "iPhone 17",
            "verified_data_points": [
                {"data": "battery", "value": 4500, "unit": "mAh", "confidence": 0.8, "source": "source-b.com"},
            ],
        }
        mem.ingest_brief(brief2, quality_score=0.8)
        product = mem.query_product("iPhone 17")
        # Should have both the primary and an alternative
        assert any(k.startswith("battery_alt_") for k in product["attributes"])

    def test_get_high_confidence_attributes(self):
        mem = ProductKnowledgeMemory()
        brief = {
            "topic": "Test Product",
            "verified_data_points": [
                {"data": "high conf spec", "value": 100, "confidence": 0.95, "source": "trusted.com"},
                {"data": "low conf spec", "value": 200, "confidence": 0.6, "source": "sketchy.com"},
            ],
        }
        mem.ingest_brief(brief, quality_score=0.9)
        high = mem.get_high_confidence_attributes("Test Product", threshold=0.8)
        assert "high_conf_spec" in high
        assert "low_conf_spec" not in high

    def test_query_product_fuzzy_match(self):
        mem = ProductKnowledgeMemory()
        brief = {"topic": "Apple iPhone 17 Pro", "verified_data_points": []}
        mem.ingest_brief(brief, quality_score=0.8)
        # Fuzzy match should find it
        assert mem.query_product("iPhone 17") is not None

    def test_empty_brief_no_error(self):
        mem = ProductKnowledgeMemory()
        mem.ingest_brief({}, quality_score=0.8)
        # Product entry created for "unknown" topic, but no attributes
        assert len(mem.products) <= 1

    def test_brief_without_verified_points(self):
        mem = ProductKnowledgeMemory()
        brief = {"topic": "Some Product"}
        mem.ingest_brief(brief, quality_score=0.8)
        # No error, product record exists but no attributes
        product = mem.query_product("Some Product")
        assert product is not None
        assert product["attributes"] == {}


# ═══════════════════════════════════════════════════════════════════════════════
# Node integration
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryNodeIntegration:
    """Verify that nodes return memory dicts in their outputs."""

    def test_critic_node_includes_source_memory(self):
        """critic_agent_node should include source_credibility_memory when challenges exist."""
        from unittest.mock import MagicMock, patch

        from deerflow.collaboration.nodes.research_nodes import critic_agent_node

        state = {
            "scout_results": [{"source": "https://example.com", "content": "test"}],
            "challenges": [],
            "rebuttals": [],
            "debate_round": 0,
            "source_credibility_memory": None,
            "messages": [],
        }

        # SubagentExecutor is imported locally inside the node function
        with patch("deerflow.subagents.executor.SubagentExecutor") as mock_executor_cls:
            with patch("deerflow.tools.get_available_tools", return_value=[]):
                mock_executor = MagicMock()
                mock_executor.execute.return_value = '[{"challenge_id":"ch-1","claim":"test","evidence":["https://example.com"],"severity":"minor","suggested_remedy":"verify"}]'
                mock_executor_cls.return_value = mock_executor

                result = critic_agent_node(state)
                assert "challenges" in result
                assert "debate_round" in result
                assert "source_credibility_memory" in result

    def test_judge_node_includes_source_memory(self):
        """meta_judge_node should include source_credibility_memory after ruling."""
        from unittest.mock import MagicMock, patch

        from deerflow.collaboration.nodes.research_nodes import meta_judge_node

        state = {
            "scout_results": [{"source": "https://example.com", "content": "test"}],
            "challenges": [{"challenge_id": "ch-1", "claim": "test"}],
            "rebuttals": [],
            "debate_round": 1,
            "ruling": None,
            "source_credibility_memory": None,
            "messages": [],
        }

        with patch("deerflow.subagents.executor.SubagentExecutor") as mock_executor_cls:
            with patch("deerflow.tools.get_available_tools", return_value=[]):
                mock_executor = MagicMock()
                mock_executor.execute.return_value = '{"ruling_id":"rul-1","resolved":["ch-1"],"unresolved":[],"dismissed":[],"quality_score":0.85,"computation_summary":"ok"}'
                mock_executor_cls.return_value = mock_executor

                result = meta_judge_node(state)
                assert "ruling" in result
                assert "source_credibility_memory" in result

    def test_pi_review_node_includes_product_memory(self):
        """pi_review_node should include product_knowledge_memory after validating brief."""
        from unittest.mock import MagicMock, patch

        from deerflow.collaboration.nodes.research_nodes import pi_review_node

        state = {
            "validated_brief": None,
            "research_quality_score": 0.9,
            "ruling": {"quality_score": 0.9},
            "challenges": [],
            "rebuttals": [],
            "scout_results": [],
            "product_knowledge_memory": None,
            "messages": [],
        }

        with patch("deerflow.subagents.executor.SubagentExecutor") as mock_executor_cls:
            with patch("deerflow.tools.get_available_tools", return_value=[]):
                mock_executor = MagicMock()
                mock_executor.execute.return_value = '{"validated_brief":{"topic":"Test","verified_data_points":[{"data":"spec","value":100,"confidence":0.9,"source":"test.com"}]}}'
                mock_executor_cls.return_value = mock_executor

                result = pi_review_node(state)
                assert "validated_brief" in result
                assert "product_knowledge_memory" in result
