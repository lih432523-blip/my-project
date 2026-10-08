"""
Agent Package Public API.

对外统一暴露成员 D 的稳定接口。
"""


from src.agent.agent import (
    agent_chat,
)

from src.agent.health import (
    get_system_health,
)

from src.agent.observability import (
    get_agent_metrics,
    get_recent_requests,
    get_log_path,
)


__all__ = [

    "agent_chat",

    "get_system_health",

    "get_agent_metrics",

    "get_recent_requests",

    "get_log_path",
]