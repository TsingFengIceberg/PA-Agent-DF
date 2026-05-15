"""Role-gated permission system — 四权分立 + 8 角色权限矩阵。

PermissionGuardMiddleware 在 before_tool_call 中拦截越权操作，
配合 SubagentConfig.tools 白名单形成双层防护。
"""

from deerflow.collaboration.permissions.permission_guard import PermissionGuardMiddleware
from deerflow.collaboration.permissions.role_definition import (
    ROLES,
    Action,
    RoleDefinition,
    find_action_for_tool,
    get_role,
)

__all__ = [
    "Action",
    "RoleDefinition",
    "ROLES",
    "get_role",
    "find_action_for_tool",
    "PermissionGuardMiddleware",
]
