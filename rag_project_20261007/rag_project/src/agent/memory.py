"""
Conversation Memory for Research Assistant Agent.

实现功能：

1. Session Isolation
   不同 session_id 的历史完全隔离。

2. Sliding Window
   只保留最近若干条完整消息进入上下文。

3. Summary Memory
   较旧历史通过 LLM 压缩成摘要，
   避免 Prompt 无限增长。

4. Active Paper Tracking
   记录当前会话正在讨论的论文，
   用于解析：
       “它”
       “这篇论文”
       “本文”
   等指代表达。
"""

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Dict, List, Any, Optional

from src.agent.llm_client import chat


# ============================================================
# Config
# ============================================================

# 最近完整保留多少条 message
# 8 条 ≈ 4 轮 user / assistant
MAX_RECENT_MESSAGES = 8

# 超过多少条后触发摘要压缩
SUMMARY_TRIGGER_MESSAGES = 12

# 单条历史消息最多保存字符数
MAX_MESSAGE_CHARS = 2500

# Summary 最大字符数
MAX_SUMMARY_CHARS = 3000


# ============================================================
# Session State
# ============================================================

@dataclass
class SessionMemory:
    """
    单个会话的 Memory 状态。
    """

    session_id: str

    # 压缩后的长期摘要
    summary: str = ""

    # 最近完整对话
    messages: List[Dict[str, Any]] = field(
        default_factory=list
    )

    # 当前会话讨论的论文
    active_paper: Optional[str] = None

    # 累计写入消息数
    total_messages: int = 0


# ============================================================
# Memory Manager
# ============================================================

class ConversationMemoryManager:

    def __init__(
        self,
        max_recent_messages: int = MAX_RECENT_MESSAGES,
        summary_trigger_messages: int = SUMMARY_TRIGGER_MESSAGES,
    ):

        self.max_recent_messages = (
            max_recent_messages
        )

        self.summary_trigger_messages = (
            summary_trigger_messages
        )

        self._sessions: Dict[
            str,
            SessionMemory
        ] = {}

        self._lock = RLock()

    # ========================================================
    # Session
    # ========================================================

    def _normalize_session_id(
        self,
        session_id: str,
    ) -> str:

        session_id = str(
            session_id
            or "default"
        ).strip()

        return (
            session_id
            or "default"
        )

    def get_session(
        self,
        session_id: str,
    ) -> SessionMemory:
        """
        获取或创建指定 Session。
        """

        session_id = (
            self._normalize_session_id(
                session_id
            )
        )

        with self._lock:

            if session_id not in self._sessions:

                self._sessions[
                    session_id
                ] = SessionMemory(
                    session_id=session_id
                )

            return self._sessions[
                session_id
            ]

    # ========================================================
    # Add Message
    # ========================================================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        添加一条对话记录。

        role:
            user
            assistant
        """

        if role not in {
            "user",
            "assistant",
        }:

            raise ValueError(
                f"Unsupported role: {role}"
            )

        content = str(
            content
            or ""
        ).strip()

        if not content:
            return

        # 防止巨大论文总结无限占内存
        if len(content) > MAX_MESSAGE_CHARS:

            content = (
                content[
                    :MAX_MESSAGE_CHARS
                ]
                + "\n...[truncated]"
            )

        session = self.get_session(
            session_id
        )

        with self._lock:

            session.messages.append({
                "role": role,
                "content": content,
                "timestamp": (
                    datetime.now()
                    .astimezone()
                    .isoformat(
                        timespec="seconds"
                    )
                ),
            })

            session.total_messages += 1

        # assistant 消息写入后再检查压缩，
        # 尽量保持完整的一轮对话。
        if role == "assistant":

            self._compact_if_needed(
                session_id
            )

    # ========================================================
    # Active Paper
    # ========================================================

    def set_active_paper(
        self,
        session_id: str,
        paper_name: str,
    ) -> None:
        """
        设置当前会话正在讨论的论文。
        """

        paper_name = str(
            paper_name
            or ""
        ).strip()

        if not paper_name:
            return

        session = self.get_session(
            session_id
        )

        with self._lock:

            session.active_paper = (
                paper_name
            )

    def get_active_paper(
        self,
        session_id: str,
    ) -> Optional[str]:

        session = self.get_session(
            session_id
        )

        return session.active_paper

    # ========================================================
    # Summary Compression
    # ========================================================

    def _compact_if_needed(
        self,
        session_id: str,
    ) -> None:
        """
        当完整历史过长时：

            Old Messages
                 ↓
            LLM Summary
                 ↓
            Summary Memory

        最近消息继续完整保留。
        """

        session = self.get_session(
            session_id
        )

        if (
            len(session.messages)
            <= self.summary_trigger_messages
        ):
            return

        # 最近 N 条完整保留
        recent_messages = (
            session.messages[
                -self.max_recent_messages:
            ]
        )

        # 更旧的消息进行摘要
        old_messages = (
            session.messages[
                :-self.max_recent_messages
            ]
        )

        if not old_messages:
            return

        old_text_parts = []

        for message in old_messages:

            role = message.get(
                "role",
                "unknown",
            )

            content = message.get(
                "content",
                "",
            )

            old_text_parts.append(
                f"{role.upper()}: "
                f"{content}"
            )

        old_text = "\n\n".join(
            old_text_parts
        )

        existing_summary = (
            session.summary
            or "None"
        )

        system_prompt = """
你是科研助理系统的会话记忆压缩模块。

你的任务是把较旧的聊天历史压缩成简洁、
事实性的 Conversation Memory。

必须保留：

1. 用户正在讨论的论文名称。
2. 用户已经提出的重要问题。
3. 已经确定的重要上下文。
4. 用户使用的代词或后续问题可能依赖的信息。
5. 已经完成的任务，例如：
   - 论文总结
   - 作者查询
   - 关键词提取
   - 方法讨论

要求：

1. 不得增加聊天记录中不存在的新事实。
2. 不要保存冗长的完整回答。
3. 不需要保留工具执行日志。
4. 不要保存 Thought / Action 等内部执行过程。
5. 摘要控制在简洁范围内。
"""

        user_prompt = f"""
Existing Memory Summary:

{existing_summary}


Older Conversation:

{old_text}


请生成更新后的会话摘要。
"""

        try:

            new_summary = chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
            )

            new_summary = (
                new_summary.strip()
            )

            if len(
                new_summary
            ) > MAX_SUMMARY_CHARS:

                new_summary = (
                    new_summary[
                        :MAX_SUMMARY_CHARS
                    ]
                )

        except Exception:

            # ------------------------------------------------
            # LLM Summary 失败时的降级策略
            #
            # 不能因为 Memory 压缩失败，
            # 导致整个 Agent 对话失败。
            # ------------------------------------------------

            fallback_parts = []

            if session.summary:

                fallback_parts.append(
                    session.summary
                )

            # 只保存旧消息的简化文本
            fallback_parts.append(
                old_text[:1500]
            )

            new_summary = "\n".join(
                fallback_parts
            )[:MAX_SUMMARY_CHARS]

        with self._lock:

            session.summary = (
                new_summary
            )

            session.messages = (
                recent_messages
            )

    # ========================================================
    # Build Context
    # ========================================================

    def get_context(
        self,
        session_id: str,
    ) -> str:
        """
        返回适合放入 Agent Prompt 的 Memory Context。
        """

        session = self.get_session(
            session_id
        )

        parts = []

        if session.active_paper:

            parts.append(
                "Active Paper:\n"
                f"{session.active_paper}"
            )

        if session.summary:

            parts.append(
                "Conversation Summary:\n"
                f"{session.summary}"
            )

        if session.messages:

            recent_parts = []

            for message in session.messages:

                role = (
                    message.get(
                        "role",
                        "unknown",
                    )
                    .upper()
                )

                content = message.get(
                    "content",
                    "",
                )

                recent_parts.append(
                    f"{role}: {content}"
                )

            parts.append(
                "Recent Conversation:\n"
                + "\n\n".join(
                    recent_parts
                )
            )

        return "\n\n".join(
            parts
        )

    # ========================================================
    # Stats
    # ========================================================

    def get_stats(
        self,
        session_id: str,
    ) -> Dict[str, Any]:

        session = self.get_session(
            session_id
        )

        return {
            "session_id": (
                session.session_id
            ),
            "active_paper": (
                session.active_paper
            ),
            "recent_messages": len(
                session.messages
            ),
            "total_messages": (
                session.total_messages
            ),
            "has_summary": bool(
                session.summary
            ),
            "summary_chars": len(
                session.summary
            ),
        }

    # ========================================================
    # Clear
    # ========================================================

    def clear_session(
        self,
        session_id: str,
    ) -> bool:

        session_id = (
            self._normalize_session_id(
                session_id
            )
        )

        with self._lock:

            if session_id in self._sessions:

                del self._sessions[
                    session_id
                ]

                return True

        return False

    def clear_all(
        self,
    ) -> None:

        with self._lock:

            self._sessions.clear()


# ============================================================
# Global Memory Manager
# ============================================================

memory_manager = (
    ConversationMemoryManager()
)


# ============================================================
# Public API
# ============================================================

def add_memory_message(
    session_id: str,
    role: str,
    content: str,
) -> None:

    memory_manager.add_message(
        session_id=session_id,
        role=role,
        content=content,
    )


def get_memory_context(
    session_id: str,
) -> str:

    return memory_manager.get_context(
        session_id
    )


def set_active_paper(
    session_id: str,
    paper_name: str,
) -> None:

    memory_manager.set_active_paper(
        session_id,
        paper_name,
    )


def get_active_paper(
    session_id: str,
) -> Optional[str]:

    return memory_manager.get_active_paper(
        session_id
    )


def get_memory_stats(
    session_id: str,
) -> Dict[str, Any]:

    return memory_manager.get_stats(
        session_id
    )


def clear_memory(
    session_id: str,
) -> bool:

    return memory_manager.clear_session(
        session_id
    )