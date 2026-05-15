"""Collaboration system configuration — loaded from config.yaml collaboration section.

Extends DeerFlow's config hot-loading mechanism. Configured in config.yaml:

    collaboration:
      enabled: true
      default_workflow: "competitive_analysis"
      roles: {...}
      skills: {...}
      memory: {...}
      hitl: {...}
      workflows: {...}
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Role Configuration
# ═══════════════════════════════════════════════════════════════════════════════


class RoleConfig(BaseModel):
    """Per-role runtime configuration."""

    model: str = Field(
        default="inherit",
        description="Model name (or 'inherit' for parent model)",
    )
    thinking_enabled: bool = Field(
        default=False,
        description="Whether to enable extended thinking for this role",
    )
    max_turns: int = Field(
        default=15,
        ge=1,
        description="Maximum ReAct turns for this role",
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Optional per-role timeout override",
    )
    tools: list[str] | None = Field(
        default=None,
        description="Tool whitelist (None = use DEFAULT_TOOLS for this role)",
    )
    skills: list[str] | None = Field(
        default=None,
        description="Skill names whitelist",
    )
    max_instances: int = Field(
        default=1,
        ge=1,
        description="Maximum parallel instances of this role",
    )


class RolesConfig(BaseModel):
    """Configuration for all collaboration roles."""

    pi_agent: RoleConfig = Field(default_factory=lambda: RoleConfig(model="claude-opus-4-7", thinking_enabled=True, max_turns=15))
    data_scout: RoleConfig = Field(default_factory=lambda: RoleConfig(model="inherit", thinking_enabled=False, max_turns=30, max_instances=4))
    critic_agent: RoleConfig = Field(default_factory=lambda: RoleConfig(model="claude-opus-4-7", thinking_enabled=True, max_turns=30))
    meta_judge: RoleConfig = Field(default_factory=lambda: RoleConfig(model="claude-opus-4-7", thinking_enabled=True, max_turns=25))
    pi_review: RoleConfig = Field(default_factory=lambda: RoleConfig(model="inherit", thinking_enabled=False, max_turns=15))
    analyst_lead: RoleConfig = Field(default_factory=lambda: RoleConfig(model="claude-opus-4-7", thinking_enabled=True, max_turns=15))
    synthesizer: RoleConfig = Field(default_factory=lambda: RoleConfig(model="claude-opus-4-7", thinking_enabled=True, max_turns=50))
    internal_reviewer: RoleConfig = Field(default_factory=lambda: RoleConfig(model="inherit", thinking_enabled=False, max_turns=15))
    report_composer: RoleConfig = Field(default_factory=lambda: RoleConfig(model="inherit", thinking_enabled=False, max_turns=40))
    error_handler: RoleConfig = Field(default_factory=lambda: RoleConfig(max_turns=5))


# ═══════════════════════════════════════════════════════════════════════════════
# Skills Configuration
# ═══════════════════════════════════════════════════════════════════════════════


class CollabSkillsConfig(BaseModel):
    """Collaboration Skills configuration."""

    enabled: bool = Field(default=True, description="Enable DF Skills in collaboration")
    load_path: str = Field(default="skills/public", description="Skills load path")


# ═══════════════════════════════════════════════════════════════════════════════
# Memory Configuration (Collaboration Extension)
# ═══════════════════════════════════════════════════════════════════════════════


class SourceCredibilityConfig(BaseModel):
    """Source credibility memory — scores data sources based on prior verification."""

    enabled: bool = Field(default=True)
    update_trigger: str = Field(default="post_validation", description="When to update: post_validation")


class ProductKnowledgeConfig(BaseModel):
    """Product knowledge graph memory."""

    enabled: bool = Field(default=True)
    update_trigger: str = Field(default="post_synthesis", description="When to update: post_synthesis")


class CollabMemoryConfig(BaseModel):
    """Collaboration Memory configuration (extends DF Memory)."""

    source_credibility: SourceCredibilityConfig = Field(default_factory=SourceCredibilityConfig)
    product_knowledge: ProductKnowledgeConfig = Field(default_factory=ProductKnowledgeConfig)


# ═══════════════════════════════════════════════════════════════════════════════
# HITL Configuration
# ═══════════════════════════════════════════════════════════════════════════════


class HITLConfig(BaseModel):
    """Human-in-the-Loop gate configuration."""

    enabled: bool = Field(default=True, description="Enable HITL approval gates")
    gates: list[str] = Field(
        default_factory=lambda: ["post_synthesis"],
        description="Which gates are active: post_synthesis",
    )
    stale_timeout_minutes: int = Field(
        default=30,
        ge=1,
        description="Approval timeout in minutes; stale approvals are rejected",
    )
    require_audit_log: bool = Field(
        default=True,
        description="Record audit log entries for approval decisions",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Presets
# ═══════════════════════════════════════════════════════════════════════════════


class WorkflowPreset(BaseModel):
    """Pre-configured workflow preset."""

    description: str = Field(default="", description="Human-readable description")
    scouts: int = Field(default=2, ge=1, le=4)
    phases: list[str] = Field(default_factory=lambda: ["planning", "collecting", "validating", "synthesizing", "reviewing", "composing"])
    skip_validation: bool = Field(default=False)


class WorkflowsConfig(BaseModel):
    """Named workflow presets from config.yaml."""

    competitive_analysis: WorkflowPreset = Field(
        default_factory=lambda: WorkflowPreset(
            description="Full competitive analysis with adversarial critique",
            scouts=3,
        ),
    )
    market_trend: WorkflowPreset = Field(
        default_factory=lambda: WorkflowPreset(
            description="Market trend analysis (lightweight, skip validation)",
            scouts=2,
            skip_validation=True,
        ),
    )
    pricing_optimization: WorkflowPreset = Field(
        default_factory=lambda: WorkflowPreset(
            description="Pricing optimization analysis",
            scouts=2,
        ),
    )
    supply_chain_risk: WorkflowPreset = Field(
        default_factory=lambda: WorkflowPreset(
            description="Supply chain risk assessment",
            scouts=3,
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Top-level Collaboration Config
# ═══════════════════════════════════════════════════════════════════════════════


class CollaborationAppConfig(BaseModel):
    """Top-level configuration for the collaboration system."""

    enabled: bool = Field(default=False, description="Master switch for collaboration system")
    default_workflow: str = Field(default="competitive_analysis", description="Default workflow preset")
    roles: RolesConfig = Field(default_factory=RolesConfig)
    skills: CollabSkillsConfig = Field(default_factory=CollabSkillsConfig)
    memory: CollabMemoryConfig = Field(default_factory=CollabMemoryConfig)
    hitl: HITLConfig = Field(default_factory=HITLConfig)
    workflows: WorkflowsConfig = Field(default_factory=WorkflowsConfig)

    def get_role_config(self, role_name: str) -> RoleConfig:
        """Get config for a specific role."""
        return getattr(self.roles, role_name, None) or RoleConfig()

    def get_workflow(self, name: str | None = None) -> WorkflowPreset:
        """Get a workflow preset by name."""
        workflow_name = name or self.default_workflow
        preset = getattr(self.workflows, workflow_name, None)
        if preset is not None:
            return preset
        logger.warning("Unknown workflow '%s', falling back to competitive_analysis", workflow_name)
        return self.workflows.competitive_analysis


# ── Module-level singleton, hot-reloaded ──

_collaboration_config: CollaborationAppConfig = CollaborationAppConfig()


def get_collaboration_config() -> CollaborationAppConfig:
    """Get the current collaboration configuration."""
    return _collaboration_config


def load_collaboration_config_from_dict(config_dict: dict[str, Any] | None) -> None:
    """Hot-reload collaboration configuration from a config dict (e.g., config.yaml).

    Called by AppConfig loader when config.yaml changes.
    """
    global _collaboration_config
    if config_dict is None:
        _collaboration_config = CollaborationAppConfig()
    else:
        _collaboration_config = CollaborationAppConfig(**config_dict)

    if _collaboration_config.enabled:
        logger.info(
            "Collaboration system loaded: workflow=%s, hitl=%s, roles=%d",
            _collaboration_config.default_workflow,
            "enabled" if _collaboration_config.hitl.enabled else "disabled",
            len(_collaboration_config.roles.model_dump()),
        )
    else:
        logger.info("Collaboration system is disabled")
