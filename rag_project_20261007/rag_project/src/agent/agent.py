"""
Unified Agent Entry.

统一入口：

    User Question
         ↓
    Conversation Memory
         ↓
    Fast Router
         ↓
    ┌───────────────┬────────────────┐
    │ Direct Tool   │ ReAct Fallback │
    └───────────────┴────────────────┘
         ↓
    Unified Result

设计目标：

1. 明确意图直接调用 Tool；
2. 模糊问题交给完整 ReAct；
3. 非 RAG Tool 不初始化 RAG；
4. 论文指代先解析，再决定是否初始化 RAG；
5. 支持 Session Memory；
6. 为前端提供统一返回格式。
"""

import re
import time
from typing import Dict, Any

from src.agent.router import route_question

from src.agent.tools import (
    initialize_tools,
    get_tool,
)

from src.agent.memory import (
    add_memory_message,
    get_memory_context,
    set_active_paper,
    get_active_paper,
    get_memory_stats,
)

from src.agent.react_loop import react_agent

from src.agent.observability import (
    observe_agent_call,
)


# ============================================================
# Route Configuration
# ============================================================

RAG_ROUTES = {
    "knowledge_base_search",
    "knowledge_base_retrieve",
    "paper_summary",
    "paper_metadata",
    "keyword_extract",
    "paper_compare",
}

NON_RAG_ROUTES = {
    "current_time",
}

PAPER_ROUTES = {
    "paper_summary",
    "paper_metadata",
    "keyword_extract",
}


# ============================================================
# Paper Reference Detection
# ============================================================

def _is_paper_reference(
    text: str,
) -> bool:
    """
    判断 Tool Input 是否只是论文指代表达，
    而不是实际论文名称。

    例如：

        它
        这篇论文
        本文
        this paper
    """

    text = (
        text
        or ""
    ).strip().lower()

    references = {
        "它",
        "它的",
        "这篇论文",
        "该论文",
        "本文",
        "这篇文章",
        "这个论文",
        "这个文章",
        "这篇",
        "it",
        "this paper",
        "the paper",
        "this article",
    }

    return text in references


# ============================================================
# Paper Name Extraction
# ============================================================

def extract_paper_name(
    question: str,
    route: str,
) -> str:
    """
    从 Router 已确定意图的问题中提取论文名称。

    示例：

        请总结一下论文 Attention Is All You Need
            ->
        Attention Is All You Need


        请提取论文 Attention Is All You Need 的核心关键词
            ->
        Attention Is All You Need


        Attention Is All You Need 的作者和 DOI 是什么？
            ->
        Attention Is All You Need


        请提取它的核心关键词
            ->
        它

    后续进入多论文阶段后，
    建议升级成 paper_id / document registry。
    """

    text = (
        question
        or ""
    ).strip()

    # ========================================================
    # 1. 优先解析带引号 / 书名号论文名
    # ========================================================

    quoted_patterns = [
        r"《([^》]+)》",
        r"“([^”]+)”",
        r'"([^"]+)"',
        r"'([^']+)'",
    ]

    for pattern in quoted_patterns:

        match = re.search(
            pattern,
            text,
        )

        if match:

            candidate = (
                match.group(1)
                .strip()
            )

            if candidate:
                return candidate

    # ========================================================
    # 2. Summary
    # ========================================================

    if route == "paper_summary":

        # ----------------------------------------------------
        # 先处理纯指代式表达
        # ----------------------------------------------------

        reference_patterns = [
            r"请总结一下(它|这篇论文|该论文|本文|这篇文章)",
            r"请总结(它|这篇论文|该论文|本文|这篇文章)",
            r"总结一下(它|这篇论文|该论文|本文|这篇文章)",
            r"总结(它|这篇论文|该论文|本文|这篇文章)",
            r"请概括一下(它|这篇论文|该论文|本文|这篇文章)",
            r"概括一下(它|这篇论文|该论文|本文|这篇文章)",
            r"介绍一下(它|这篇论文|该论文|本文|这篇文章)",
        ]

        for pattern in reference_patterns:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:
                return (
                    match.group(1)
                    .strip()
                )

        # ----------------------------------------------------
        # 正常论文名称
        # ----------------------------------------------------

        patterns = [
            r"请总结一下论文\s*(.+)$",
            r"请总结论文\s*(.+)$",
            r"总结一下论文\s*(.+)$",
            r"总结论文\s*(.+)$",
            r"请概括一下论文\s*(.+)$",
            r"请概括论文\s*(.+)$",
            r"介绍一下论文\s*(.+)$",
            r"概括一下论文\s*(.+)$",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:

                candidate = (
                    match.group(1)
                    .strip()
                    .strip("？?。.")
                )

                if candidate:
                    return candidate

    # ========================================================
    # 3. Keyword Extraction
    # ========================================================

    if route == "keyword_extract":

        cleaned = re.sub(
            r"^(请)?(帮我)?"
            r"(提取|抽取|给出|生成)"
            r"(一下)?"
            r"(论文)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*的?"
            r"(核心关键词|关键词|核心词|"
            r"核心术语|技术关键词|研究主题)"
            r".*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = (
            cleaned
            .strip()
            .strip("？?。.")
        )

        if cleaned:
            return cleaned

    # ========================================================
    # 4. Metadata
    # ========================================================

    if route == "paper_metadata":

        metadata_markers = [
            r"\s*的作者.*$",
            r"\s*作者和.*$",
            r"\s*作者、.*$",
            r"\s*的年份.*$",
            r"\s*的发表年份.*$",
            r"\s*的发表时间.*$",
            r"\s*的摘要.*$",
            r"\s*的\s*DOI.*$",
            r"\s*DOI.*$",
            r"\s*的会议.*$",
            r"\s*的期刊.*$",
            r"\s*的元信息.*$",
            r"\s*的基本信息.*$",
        ]

        cleaned = text

        cleaned = re.sub(
            r"^(请)?"
            r"(告诉我|给我|查询|查看)?"
            r"(一下)?"
            r"(论文)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        for pattern in metadata_markers:

            new_text = re.sub(
                pattern,
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

            if new_text != cleaned:
                cleaned = new_text
                break

        cleaned = (
            cleaned
            .strip()
            .strip("？?。.")
        )

        if cleaned:
            return cleaned

    # ========================================================
    # 5. Fallback
    # ========================================================

    return text


# ============================================================
# Memory Helper
# ============================================================

def _get_memory_stats_or_none(
    session_id: str,
    use_memory: bool,
):
    """
    use_memory=False 时完全不访问 Memory。
    """

    if not use_memory:
        return None

    return get_memory_stats(
        session_id
    )


def _save_conversation(
    session_id: str,
    question: str,
    answer: str,
    use_memory: bool,
) -> None:
    """
    统一保存一轮 User / Assistant 对话。
    """

    if not use_memory:
        return

    add_memory_message(
        session_id=session_id,
        role="user",
        content=question,
    )

    add_memory_message(
        session_id=session_id,
        role="assistant",
        content=answer,
    )


# ============================================================
# Normalize Direct Tool Result
# ============================================================

def normalize_tool_result(
    tool_name: str,
    tool_result: Any,
    route_info: Dict[str, Any],
    elapsed: float,
) -> Dict[str, Any]:
    """
    把不同 Tool 的结果统一成前端可使用格式。
    """

    if isinstance(
        tool_result,
        dict,
    ):

        answer = tool_result.get(
            "answer",
            str(tool_result),
        )

        sources = tool_result.get(
            "sources",
            [],
        )

        success = tool_result.get(
            "success",
            True,
        )

    else:

        answer = str(
            tool_result
        )

        sources = []

        success = True

    return {
        "answer": answer,

        "sources": sources,

        "tools_used": [
            tool_name
        ],

        "steps": 1,

        "success": bool(
            success
        ),

        "route": route_info.get(
            "route"
        ),

        "route_confidence": route_info.get(
            "confidence"
        ),

        "route_reason": route_info.get(
            "reason"
        ),

        "execution_mode": "direct_tool",

        "trace": [
            {
                "step": 1,
                "action": tool_name,
                "mode": "router_direct",
            }
        ],

        "timing": {
            "total_time": elapsed,
        },

        # 调试 / 前端高级展示时可以使用
        "tool_result": tool_result,
    }


# ============================================================
# Unified Agent Chat
# ============================================================
@observe_agent_call
def agent_chat(
    question: str,
    verbose: bool = False,
    session_id: str = "default",
    use_memory: bool = True,
) -> Dict[str, Any]:
    """
    科研助理统一入口。

    Pipeline:

        Question
            ↓
        Memory Context
            ↓
        Fast Router
            ↓
      high confidence?
        /          \\
      yes           no
       ↓             ↓
    Direct Tool    ReAct
       ↓             ↓
       └──── Unified Result ────┘


    参数：

        question:
            用户问题。

        verbose:
            是否显示 Router / Tool / Memory 调试信息。

        session_id:
            当前会话 ID。
            不同 session_id 的 Memory 相互隔离。

        use_memory:
            True:
                开启多轮会话 Memory。

            False:
                完全不访问 / 创建 Memory。
    """

    start_time = time.time()

    question = (
        question
        or ""
    ).strip()

    # ========================================================
    # 0. Empty Question
    # ========================================================

    if not question:

        return {
            "answer": "问题不能为空。",
            "sources": [],
            "tools_used": [],
            "steps": 0,
            "success": False,

            "route": "none",
            "route_confidence": "none",
            "route_reason": "empty question",

            "execution_mode": "none",

            "trace": [],

            "timing": {
                "total_time": 0.0,
            },

            "session_id": session_id,

            "memory_stats": (
                _get_memory_stats_or_none(
                    session_id,
                    use_memory,
                )
            ),
        }

    # ========================================================
    # 1. Conversation Memory
    # ========================================================

    memory_context = ""

    if use_memory:

        memory_context = (
            get_memory_context(
                session_id
            )
        )

        if (
            verbose
            and memory_context
        ):

            print(
                "\n[Memory]"
            )

            print(
                memory_context
            )

    # ========================================================
    # 2. Fast Router
    # ========================================================

    route_info = route_question(
        question
    )

    route = route_info.get(
        "route",
        "react",
    )

    if verbose:

        print(
            "\n[Router]"
        )

        print(
            f"Route: {route}"
        )

        print(
            "Confidence: "
            f"{route_info.get('confidence')}"
        )

        print(
            "Reason: "
            f"{route_info.get('reason')}"
        )

    # ========================================================
    # 3. ReAct Fallback
    # ========================================================

    if route == "react":

        if verbose:

            print(
                "\n[Agent] "
                "Router 无高置信度结果，"
                "进入 ReAct fallback。"
            )

        # 当前 ReAct 主要用于论文知识库问题，
        # 因此进入 ReAct 时才初始化 RAG。
        initialize_tools()

        try:

            result = react_agent(
                question=question,
                verbose=verbose,
                conversation_context=(
                    memory_context
                ),
            )

        except Exception as e:

            elapsed = (
                time.time()
                - start_time
            )

            error_answer = (
                "ReAct Agent 执行失败："
                f"{type(e).__name__}: {e}"
            )

            _save_conversation(
                session_id=session_id,
                question=question,
                answer=error_answer,
                use_memory=use_memory,
            )

            return {
                "answer": error_answer,
                "sources": [],
                "tools_used": [],
                "steps": 0,
                "success": False,

                "route": "react",
                "route_confidence": (
                    route_info.get(
                        "confidence"
                    )
                ),
                "route_reason": (
                    route_info.get(
                        "reason"
                    )
                ),

                "execution_mode": "react",

                "trace": [
                    {
                        "step": 0,
                        "type": "react_error",
                        "error": str(e),
                    }
                ],

                "timing": {
                    "total_time": elapsed,
                },

                "session_id": session_id,

                "memory_stats": (
                    _get_memory_stats_or_none(
                        session_id,
                        use_memory,
                    )
                ),
            }

        elapsed = (
            time.time()
            - start_time
        )

        # ----------------------------------------------------
        # 补充统一 Router 信息
        # ----------------------------------------------------

        result[
            "route"
        ] = "react"

        result[
            "route_confidence"
        ] = route_info.get(
            "confidence"
        )

        result[
            "route_reason"
        ] = route_info.get(
            "reason"
        )

        result[
            "execution_mode"
        ] = "react"

        if "timing" not in result:

            result[
                "timing"
            ] = {}

        result[
            "timing"
        ][
            "total_time"
        ] = elapsed

        # ----------------------------------------------------
        # 保存对话
        # ----------------------------------------------------

        _save_conversation(
            session_id=session_id,
            question=question,
            answer=result.get(
                "answer",
                "",
            ),
            use_memory=use_memory,
        )

        result[
            "session_id"
        ] = session_id

        result[
            "memory_stats"
        ] = (
            _get_memory_stats_or_none(
                session_id,
                use_memory,
            )
        )

        return result

    # ========================================================
    # 4. Direct Tool - Build Tool Input
    # ========================================================
    #
    # 注意：
    #
    # 这里必须先处理论文指代，
    # 然后才能决定是否初始化 RAG。
    #
    # Session B 如果问：
    #
    #     “它的作者是谁？”
    #
    # 又没有 Active Paper，
    # 应直接 clarification，
    # 不允许先初始化整个 RAG。
    # ========================================================

    if route == "current_time":

        tool_input = ""

    elif route == "paper_compare":

        # paper_compare 自己负责解析两篇论文
        tool_input = question

    else:

        tool_input = extract_paper_name(
            question=question,
            route=route,
        )

    # ========================================================
    # 5. Resolve Paper Reference
    # ========================================================

    if (
        route in PAPER_ROUTES
        and _is_paper_reference(
            tool_input
        )
    ):

        active_paper = None

        if use_memory:

            active_paper = (
                get_active_paper(
                    session_id
                )
            )

        # ----------------------------------------------------
        # 找到了当前论文
        # ----------------------------------------------------

        if active_paper:

            if verbose:

                print(
                    "\n[Memory Resolution]"
                )

                print(
                    f"{tool_input} "
                    f"→ {active_paper}"
                )

            tool_input = (
                active_paper
            )

        # ----------------------------------------------------
        # 没有上下文
        # ----------------------------------------------------

        else:

            answer = (
                "请先告诉我你想查询哪篇论文。"
            )

            result = {
                "answer": answer,

                "sources": [],

                "tools_used": [],

                "steps": 0,

                "success": True,

                "needs_clarification": True,

                "route": route,

                "route_confidence": (
                    route_info.get(
                        "confidence"
                    )
                ),

                "route_reason": (
                    route_info.get(
                        "reason"
                    )
                ),

                "execution_mode": (
                    "clarification"
                ),

                "trace": [],

                "timing": {
                    "total_time": (
                        time.time()
                        - start_time
                    ),
                },

                "session_id": session_id,
            }

            _save_conversation(
                session_id=session_id,
                question=question,
                answer=answer,
                use_memory=use_memory,
            )

            result[
                "memory_stats"
            ] = (
                _get_memory_stats_or_none(
                    session_id,
                    use_memory,
                )
            )

            return result

    # ========================================================
    # 6. Lazy RAG Initialization
    # ========================================================
    #
    # 到这里才说明：
    #
    # 1. Tool Input 已经确定；
    # 2. 论文指代已经解析；
    # 3. 不需要 clarification。
    #
    # 此时才允许初始化 RAG。
    # ========================================================

    if route in RAG_ROUTES:

        if verbose:

            print(
                "\n[Agent] "
                f"{route} 需要 RAG，"
                "开始初始化知识库。"
            )

        initialize_tools()

    elif route in NON_RAG_ROUTES:

        if verbose:

            print(
                "\n[Agent] "
                f"{route} 不需要 RAG，"
                "跳过知识库初始化。"
            )

    # ========================================================
    # 7. Display Direct Tool
    # ========================================================

    if verbose:

        print(
            "\n[Direct Tool]"
        )

        print(
            f"Tool: {route}"
        )

        print(
            f"Input: {tool_input}"
        )

    # ========================================================
    # 8. Execute Tool
    # ========================================================

    try:

        tool_func = get_tool(
            route
        )

        tool_result = tool_func(
            tool_input
        )

        # ====================================================
        # 8.1 Update Active Paper
        # ====================================================

        tool_success = True

        if isinstance(
            tool_result,
            dict,
        ):

            tool_success = bool(
                tool_result.get(
                    "success",
                    True,
                )
            )

        if (
            use_memory
            and tool_success
            and route in PAPER_ROUTES
        ):

            # -----------------------------------------------
            # 优先使用 Tool 实际确认的 paper 字段。
            #
            # 比直接保存 tool_input 更稳。
            # -----------------------------------------------

            resolved_paper = (
                tool_input
            )

            if isinstance(
                tool_result,
                dict,
            ):

                resolved_paper = (
                    tool_result.get(
                        "paper"
                    )
                    or tool_input
                )

            if resolved_paper:

                set_active_paper(
                    session_id=session_id,
                    paper_name=(
                        resolved_paper
                    ),
                )

        # ====================================================
        # 8.2 Normalize Result
        # ====================================================

        elapsed = (
            time.time()
            - start_time
        )

        result = normalize_tool_result(
            tool_name=route,
            tool_result=tool_result,
            route_info=route_info,
            elapsed=elapsed,
        )

        # ====================================================
        # 8.3 Save Conversation
        # ====================================================

        _save_conversation(
            session_id=session_id,
            question=question,
            answer=result.get(
                "answer",
                "",
            ),
            use_memory=use_memory,
        )

        result[
            "session_id"
        ] = session_id

        result[
            "memory_stats"
        ] = (
            _get_memory_stats_or_none(
                session_id,
                use_memory,
            )
        )

        return result

    # ========================================================
    # 9. Tool Error
    # ========================================================

    except Exception as e:

        elapsed = (
            time.time()
            - start_time
        )

        answer = (
            f"工具 {route} 执行失败："
            f"{type(e).__name__}: {e}"
        )

        # 是否把错误也记入 Memory：
        #
        # 当前保留这一轮，
        # 这样下一轮用户说“重试一下”时
        # 仍能知道上一轮发生了什么。
        _save_conversation(
            session_id=session_id,
            question=question,
            answer=answer,
            use_memory=use_memory,
        )

        return {
            "answer": answer,

            "sources": [],

            "tools_used": [
                route
            ],

            "steps": 1,

            "success": False,

            "route": route,

            "route_confidence": (
                route_info.get(
                    "confidence"
                )
            ),

            "route_reason": (
                route_info.get(
                    "reason"
                )
            ),

            "execution_mode": (
                "direct_tool"
            ),

            "trace": [
                {
                    "step": 1,
                    "action": route,
                    "error": str(e),
                }
            ],

            "timing": {
                "total_time": elapsed,
            },

            "session_id": session_id,

            "memory_stats": (
                _get_memory_stats_or_none(
                    session_id,
                    use_memory,
                )
            ),
        }