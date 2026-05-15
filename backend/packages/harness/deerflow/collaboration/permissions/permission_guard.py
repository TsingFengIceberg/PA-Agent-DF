"""PermissionGuardMiddleware — AgentMiddleware that enforces role permissions.

DeerFlow 中间件机制：在 before_tool_call 钩子中拦截越权操作。
配合 SubagentConfig.tools 白名单形成双层防护。
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from deerflow.collaboration.permissions.role_definition import (
    Action,
    RoleDefinition,
    find_action_for_tool,
    get_role,
)

if TYPE_CHECKING:
    from langchain.agents import AgentState
    from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class PermissionViolationError(Exception):
    """角色权限违规——由中间件捕获并转换为 ToolMessage。"""

    def __init__(self, role: str, tool: str, action: str | None, reason: str):
        self.role = role
        self.tool = tool
        self.action = action
        self.reason = reason
        super().__init__(f"[{role}] 无权调用 {tool}: {reason}")


class PermissionGuardMiddleware(AgentMiddleware):
    """在每个 tool_call 执行前检查角色权限。

    检查流程：
    1. 从 runtime 上下文获取当前角色名（agent_role）
    2. 查找角色定义
    3. 将工具名映射到抽象操作
    4. 检查角色是否有该操作的权限
    5. 检查是否需要附带证据
    6. 检查是否需要审计日志
    7. 违规 → 返回 error ToolMessage，拒绝执行
    """

    def __init__(self, *, audit_log_path: str | None = None):
        super().__init__()
        self._audit_log: list[dict[str, Any]] = []
        self._audit_log_path = audit_log_path

    def _get_current_role(self, runtime: Runtime) -> str | None:
        """从 contextvars 读取当前角色名。

        Node 函数通过 context.current_role("pi_agent") 设置，
        PermissionGuardMiddleware 在 before_tool_call 中读取。
        """
        from deerflow.collaboration.context import get_current_agent_role

        role = get_current_agent_role()
        if role:
            return role

        # Fallback: 从 runtime config 中查找
        context = getattr(runtime, "context", {}) or {}
        return context.get("agent_role")

    @override
    def before_tool_call(
        self,
        state: AgentState,
        tool_call: dict[str, Any],
        *,
        runtime: Runtime,
    ) -> ToolMessage | None:
        """在工具调用前检查权限。

        Returns:
            None: 权限检查通过，继续执行
            ToolMessage: 权限被拒绝，返回错误消息给 Agent
        """
        role_name = self._get_current_role(runtime)
        if role_name is None:
            # 无角色标记 → 不是协作图执行 → 跳过检查
            return None

        role = get_role(role_name)
        if role is None:
            logger.warning("Unknown role '%s', allowing tool call by default", role_name)
            return None

        tool_name = str(tool_call.get("name", ""))
        action = find_action_for_tool(tool_name)

        # ── 权限检查 ──
        if action is not None and not role.can(action):
            violation = PermissionViolationError(
                role=role_name,
                tool=tool_name,
                action=action.value,
                reason=f"角色 [{role_name}] 无权执行操作 [{action.value}]，该操作不在 allowed_actions 中",
            )
            logger.warning(str(violation))
            return ToolMessage(
                content=json.dumps({
                    "error": "permission_denied",
                    "role": role_name,
                    "tool": tool_name,
                    "action": action.value,
                    "message": str(violation),
                }, ensure_ascii=False),
                tool_call_id=str(tool_call.get("id", "")),
            )

        # ── 证据检查 ──
        if action is not None and role.requires_evidence(action):
            tool_args = tool_call.get("args", {})
            if not self._has_evidence(tool_args):
                return ToolMessage(
                    content=json.dumps({
                        "error": "evidence_required",
                        "role": role_name,
                        "tool": tool_name,
                        "action": action.value,
                        "message": f"操作 [{action.value}] 必须附带证据（引用具体数据点/来源）",
                    }, ensure_ascii=False),
                    tool_call_id=str(tool_call.get("id", "")),
                )

        # ── 审计日志 ──
        if action is not None and role.requires_audit(action):
            entry = {
                "timestamp": time.time(),
                "role": role_name,
                "tool": tool_name,
                "action": action.value,
                "tool_args": tool_call.get("args", {}),
            }
            self._audit_log.append(entry)
            logger.info("AUDIT: [%s] %s → %s", role_name, action.value, tool_name)

        return None  # 通过检查

    def _has_evidence(self, tool_args: dict[str, Any]) -> bool:
        """检查工具调用参数是否包含证据。

        证据可以是：source 字段、evidence 字段、data 字段中的具体引用。
        """
        # 检查直接证据字段
        if tool_args.get("evidence"):
            return True
        # 检查 source 引用
        if tool_args.get("source") or tool_args.get("url"):
            return True
        # 检查数据引用（key 中包含 data/content/source）
        for key in tool_args:
            if any(kw in key.lower() for kw in ("source", "data", "evidence", "content")):
                return True
        return False

    def get_audit_log(self) -> list[dict[str, Any]]:
        """获取当前会话的审计日志。"""
        return list(self._audit_log)
