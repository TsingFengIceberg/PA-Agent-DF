"""Collaboration execution context — per-role context variable.

Enables PermissionGuardMiddleware to determine the current agent role
without requiring changes to DeerFlow's SubagentExecutor internals.

Usage in node functions::

    from deerflow.collaboration.context import current_role

    with current_role("pi_agent"):
        result = executor.execute(task)
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

# ═══════════════════════════════════════════════════════════════════════════════
# Context variable
# ═══════════════════════════════════════════════════════════════════════════════

_agent_role: ContextVar[str] = ContextVar("agent_role", default="")


def get_current_agent_role() -> str:
    """Read the current agent role from the context variable.

    Returns empty string when no role has been set (non-collaboration execution).
    """
    return _agent_role.get()


@contextmanager
def current_role(role_name: str):
    """Context manager that sets the agent role for the duration of a block.

    Example::

        with current_role("critic_agent"):
            executor.execute(task)  # All tool calls here are tagged as critic_agent
    """
    token = _agent_role.set(role_name)
    try:
        yield
    finally:
        _agent_role.reset(token)
