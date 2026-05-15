"""Collaboration middleware — registers permission guard + role context.

This is the integration point between DeerFlow's middleware chain and the
collaboration system's permission enforcement. Registered in
agents/lead_agent/agent.py's _build_middlewares().

Architecture:
    lead_agent/agent.py
        → CollaborationMiddleware (this file)
            → PermissionGuardMiddleware (permissions/permission_guard.py)
                → collaboration.context (contextvars-based role tracking)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from deerflow.collaboration.permissions.permission_guard import PermissionGuardMiddleware

if TYPE_CHECKING:
    from langchain.agents import AgentState

logger = logging.getLogger(__name__)


class CollaborationMiddleware(AgentMiddleware):
    """Integration middleware that wraps PermissionGuardMiddleware.

    Delegates all permission enforcement to PermissionGuardMiddleware.
    This thin wrapper keeps the DeerFlow middleware registration consistent
    and provides a single point for future collaboration context injection.
    """

    def __init__(self, *, audit_log_path: str | None = None):
        super().__init__()
        self._guard = PermissionGuardMiddleware(audit_log_path=audit_log_path)

    @override
    def before_tool_call(
        self,
        state: AgentState,
        tool_call: dict,
        *,
        runtime,
    ) -> ToolMessage | None:
        """Delegate to permission guard."""
        return self._guard.before_tool_call(state, tool_call, runtime=runtime)

    def get_audit_log(self) -> list[dict]:
        """Forward audit log from guard."""
        return self._guard.get_audit_log()
