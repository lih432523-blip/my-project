import json
import re
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from src.agent.llm_client import chat

from src.agent.tools import (
    TOOLS,
    get_tool,
    initialize_tools,
)

from src.agent.prompts import (
    build_agent_system_prompt,
    build_user_prompt,
)


# ============================================================
# 基础配置
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"

# ReAct 最大推理 / 工具调用轮数
MAX_STEPS = 6

# ============================================================
# Knowledge Base Mode
# ============================================================

# False:
#   单论文模式。
#   knowledge_base_search 可以清理冗余论文标题，
#   减少 Query Drift。
#
# True:
#   多论文模式。
#   必须保留论文标题，
#   避免检索到其他论文。
MULTI_PAPER_MODE = True

# ============================================================
# Error Recovery Config
# ============================================================

# LLM 调用失败时最多尝试次数
# 2 = 初次调用 + 1 次重试
LLM_MAX_ATTEMPTS = 2

# Tool 调用失败时最多尝试次数
TOOL_MAX_ATTEMPTS = 2

# 重试等待时间
RETRY_DELAY_SECONDS = 1.0


# Tool 降级关系
#
# knowledge_base_search：
#   完整 RAG 问答失败
#
# knowledge_base_retrieve：
#   至少尝试返回检索证据，
#   让 Agent 根据 Observation 继续处理。
FALLBACK_TOOLS = {
    "knowledge_base_search":
        "knowledge_base_retrieve",
}


# ============================================================
# Terminal Tools
# ============================================================
#
# Terminal Tool：
# 工具本身已经能够产生完整最终答案，
# 因此执行完成后不再让 LLM 二次改写，
# 避免出现“RAG 回答正确，但 Agent 再次生成后产生幻觉”的问题。
#

TERMINAL_TOOLS = {
    "knowledge_base_search",
    "paper_summary",
    "paper_metadata",
    "keyword_extract",
    "paper_compare",
    "current_time",
}


# ============================================================
# 当前知识库 Query Normalization 配置
# ============================================================
#
# 当前测试知识库中只有 Attention Is All You Need。
#
# 实测：
#
# What dataset was used for training?
#
# 检索效果很好。
#
# 但是：
#
# What dataset was used for training in Attention Is All You Need?
#
# 会发生 Query Drift，导致 Retriever 检索到句法分析等其他实验内容。
#
# 因此当前阶段对这类冗余论文标题进行清理。
#
# 后续知识库扩展为多论文时，
# 应改成基于 metadata / document_id 的论文过滤机制，
# 而不是简单删除论文标题。
#

REDUNDANT_PAPER_TITLES = [
    "Attention Is All You Need",
]


# ============================================================
# Ollama 调用
# ============================================================


# ============================================================
# Agent 输出解析
# ============================================================

def parse_agent_response(
    response: str
) -> Dict[str, Optional[str]]:
    """
    解析 Qwen 输出。

    支持两种格式：

    ----------------------------------------------------------
    Tool Call
    ----------------------------------------------------------

    Thought: ...
    Action: ...
    Action Input: ...

    ----------------------------------------------------------
    Final Answer
    ----------------------------------------------------------

    Final Answer: ...
    """

    response = response.strip()

    # --------------------------------------------------------
    # Final Answer
    # --------------------------------------------------------

    final_match = re.search(
        r"Final Answer\s*:\s*(.*)",
        response,
        re.IGNORECASE | re.DOTALL,
    )

    if final_match:

        return {
            "type": "final",
            "thought": None,
            "action": None,
            "action_input": None,
            "final_answer": (
                final_match.group(1).strip()
            ),
        }

    # --------------------------------------------------------
    # Thought
    # --------------------------------------------------------

    thought_match = re.search(
        r"Thought\s*:\s*(.*?)"
        r"(?=\n\s*Action\s*:)",
        response,
        re.IGNORECASE | re.DOTALL,
    )

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------

    action_match = re.search(
        r"Action\s*:\s*([^\n]+)",
        response,
        re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Action Input
    # --------------------------------------------------------

    input_match = re.search(
        r"Action Input\s*:\s*(.*)",
        response,
        re.IGNORECASE | re.DOTALL,
    )

    if action_match and input_match:

        thought = (
            thought_match.group(1).strip()
            if thought_match
            else ""
        )

        action = (
            action_match
            .group(1)
            .strip()
            .strip("`")
        )

        action_input = (
            input_match
            .group(1)
            .strip()
        )

        # 有些模型会给 Action Input 加引号
        if (
            len(action_input) >= 2
            and (
                (
                    action_input.startswith('"')
                    and action_input.endswith('"')
                )
                or
                (
                    action_input.startswith("'")
                    and action_input.endswith("'")
                )
            )
        ):
            action_input = action_input[1:-1].strip()

        return {
            "type": "action",
            "thought": thought,
            "action": action,
            "action_input": action_input,
            "final_answer": None,
        }

    # --------------------------------------------------------
    # 无法解析
    # --------------------------------------------------------

    return {
        "type": "invalid",
        "thought": None,
        "action": None,
        "action_input": None,
        "final_answer": None,
    }


# ============================================================
# Query Normalization
# ============================================================

def normalize_rag_query(
    question: str,
    action_input: str,
) -> str:
    """
    对 RAG 检索 Query 做轻量规范化。

    当前主要解决：

        What dataset was used for training
        in Attention Is All You Need?

    ↓

        What dataset was used for training?

    原因：
        当前知识库只有这一篇论文，
        再把论文标题加入 Query 属于冗余信息，
        实测会干扰 Retriever 和 Reranker，
        导致 Query Drift。

    注意：
        这是当前单论文知识库阶段的策略。

        后续扩展多论文知识库时，
        应改为：

            query + document metadata filter

        而不是简单删除论文标题。
    """

    # 优先使用 Agent 给出的 Action Input
    query = (
        action_input.strip()
        if action_input
        else question.strip()
    )

    original_query = query

    for title in REDUNDANT_PAPER_TITLES:

        escaped_title = re.escape(title)

        # ----------------------------------------------------
        # English:
        #
        # "... in Attention Is All You Need?"
        # "... from Attention Is All You Need?"
        # "... in the paper Attention Is All You Need?"
        # ----------------------------------------------------

        query = re.sub(
            rf"\s+"
            rf"(?:in|from)\s+"
            rf"(?:the\s+paper\s+)?"
            rf"[\"'“”]?"
            rf"{escaped_title}"
            rf"[\"'“”]?"
            rf"\s*[?.!]?\s*$",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # ----------------------------------------------------
        # Chinese:
        #
        # 在《Attention Is All You Need》中
        # 《Attention Is All You Need》这篇论文中
        # ----------------------------------------------------

        query = re.sub(
            rf"在\s*"
            rf"[《\"“]?"
            rf"{escaped_title}"
            rf"[》\"”]?"
            rf"\s*(?:这篇论文)?(?:中|里)?",
            "",
            query,
            flags=re.IGNORECASE,
        )

        query = re.sub(
            rf"[《\"“]?"
            rf"{escaped_title}"
            rf"[》\"”]?"
            rf"\s*(?:这篇论文)?(?:中|里)",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # ----------------------------------------------------
        # Remaining title normalization
        #
        # Memory 场景下 Agent 可能生成：
        #
        # Why does Attention Is All You Need
        # use multi-head attention?
        #
        # 论文标题本身对当前单论文知识库属于冗余信息，
        # 但直接删除会得到：
        #
        # Why does use multi-head attention?
        #
        # 因此替换为自然的泛化指代：
        #
        # Why does the paper use multi-head attention?
        # ----------------------------------------------------

        has_chinese = bool(
            re.search(
                r"[\u4e00-\u9fff]",
                query,
            )
        )

        replacement = (
            "本文"
            if has_chinese
            else "the paper"
        )

        query = re.sub(
            rf"[《\"'“”]?"
            rf"{escaped_title}"
            rf"[》\"'“”]?",
            replacement,
            query,
            flags=re.IGNORECASE,
        )

    # 多余空格清理
    query = re.sub(
        r"\s+",
        " ",
        query,
    ).strip()

    query = query.strip(
        " ,，"
    )

    # --------------------------------------------------------
    # 如果清理导致 Query 为空或太短，则回退
    # --------------------------------------------------------

    if len(query) < 3:
        return original_query

    # --------------------------------------------------------
    # 英文 Query 恢复问号
    # --------------------------------------------------------

    if (
        original_query.endswith("?")
        and not query.endswith("?")
    ):
        query += "?"

    return query


def get_effective_tool_input(
    action: str,
    question: str,
    action_input: str,
) -> str:
    """
    根据知识库模式决定 Tool Input。

    单论文：
        可以执行历史 Query Normalization。

    多论文：
        必须保留论文标题，
        避免跨论文检索污染。
    """

    tool_input = (
        action_input.strip()
        if action_input
        else question.strip()
    )

    if (
        action
        == "knowledge_base_search"
    ):

        if MULTI_PAPER_MODE:

            return tool_input

        return normalize_rag_query(
            question=question,
            action_input=action_input,
        )

    return tool_input


# ============================================================
# Tool Observation 格式化
# ============================================================

def format_observation(
    result: Any
) -> str:
    """
    把 Tool 输出转换为：

        Observation

    方便后续继续交给 Agent。
    """

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(result, str):
        return result

    # --------------------------------------------------------
    # List
    #
    # 主要用于 knowledge_base_retrieve
    # --------------------------------------------------------

    if isinstance(result, list):

        lines = []

        for i, item in enumerate(
            result,
            1,
        ):

            if isinstance(item, dict):

                source = item.get(
                    "source",
                    "Unknown",
                )

                page = item.get(
                    "page",
                    "?",
                )

                text = item.get(
                    "text",
                    "",
                )

                score = item.get(
                    "rerank_score",
                    "",
                )

                lines.append(
                    f"[Document {i}]\n"
                    f"Source: {source}\n"
                    f"Page: {page}\n"
                    f"Score: {score}\n"
                    f"Content: {text}"
                )

            else:

                lines.append(
                    str(item)
                )

        return "\n\n".join(lines)

    # --------------------------------------------------------
    # Dict
    #
    # 主要用于 knowledge_base_search
    # --------------------------------------------------------

    if isinstance(result, dict):

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    return str(result)


# ============================================================
# Tool 执行
# ============================================================

def run_tool(
    tool_name: str,
    tool_input: str,
) -> Any:
    """
    真正执行 Agent 选择的 Tool。
    """

    if tool_name not in TOOLS:

        raise ValueError(
            f"不存在的工具: {tool_name}"
        )

    tool_func = get_tool(
        tool_name
    )

    return tool_func(
        tool_input
    )


def _is_transient_error(
    error: Exception,
) -> bool:
    """
    判断是否属于适合重试的临时错误。

    典型情况：
        timeout
        connection reset
        connection refused
        temporary unavailable
    """

    if isinstance(
        error,
        TimeoutError,
    ):
        return True

    message = str(
        error
    ).lower()

    transient_keywords = [
        "timeout",
        "timed out",
        "connection",
        "temporarily",
        "temporary",
        "unavailable",
        "reset by peer",
        "connection refused",
        "remote end closed",
    ]

    return any(
        keyword in message
        for keyword
        in transient_keywords
    )


def call_llm_with_retry(
    system_prompt: str,
    user_prompt: str,
    trace: List[Dict[str, Any]],
    step: int,
    verbose: bool = False,
) -> str:
    """
    带 Retry 的 LLM 调用。

    临时错误：
        retry

    非临时错误：
        立即失败
    """

    last_error = None

    for attempt in range(
        1,
        LLM_MAX_ATTEMPTS + 1,
    ):

        try:

            return chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        except Exception as e:

            last_error = e

            transient = (
                _is_transient_error(
                    e
                )
            )

            trace.append({
                "step": step,
                "type": "llm_retry",
                "attempt": attempt,
                "max_attempts": (
                    LLM_MAX_ATTEMPTS
                ),
                "transient": transient,
                "error": (
                    f"{type(e).__name__}: {e}"
                ),
            })

            if verbose:

                print(
                    "\n[LLM Error]"
                )

                print(
                    f"Attempt "
                    f"{attempt}/"
                    f"{LLM_MAX_ATTEMPTS}: "
                    f"{type(e).__name__}: {e}"
                )

            # 非临时错误没有必要反复请求
            if not transient:
                break

            # 已经没有下一次机会
            if (
                attempt
                >= LLM_MAX_ATTEMPTS
            ):
                break

            if verbose:

                print(
                    "[Recovery] "
                    "等待后重试 LLM..."
                )

            time.sleep(
                RETRY_DELAY_SECONDS
            )

    raise RuntimeError(
        "LLM 调用在恢复尝试后仍失败："
        f"{type(last_error).__name__}: "
        f"{last_error}"
    )


def run_tool_with_retry(
    tool_name: str,
    tool_input: str,
    trace: List[Dict[str, Any]],
    step: int,
    verbose: bool = False,
) -> Any:
    """
    Tool Retry。

    临时错误：
        retry

    非临时错误：
        不重复执行。
    """

    last_error = None

    for attempt in range(
        1,
        TOOL_MAX_ATTEMPTS + 1,
    ):

        try:

            return run_tool(
                tool_name=tool_name,
                tool_input=tool_input,
            )

        except Exception as e:

            last_error = e

            transient = (
                _is_transient_error(
                    e
                )
            )

            trace.append({
                "step": step,
                "type": "tool_retry",
                "tool": tool_name,
                "tool_input": tool_input,
                "attempt": attempt,
                "max_attempts": (
                    TOOL_MAX_ATTEMPTS
                ),
                "transient": transient,
                "error": (
                    f"{type(e).__name__}: {e}"
                ),
            })

            if verbose:

                print(
                    "\n[Tool Error]"
                )

                print(
                    f"{tool_name} "
                    f"Attempt "
                    f"{attempt}/"
                    f"{TOOL_MAX_ATTEMPTS}: "
                    f"{type(e).__name__}: {e}"
                )

            if not transient:
                break

            if (
                attempt
                >= TOOL_MAX_ATTEMPTS
            ):
                break

            if verbose:

                print(
                    "[Recovery] "
                    f"Retry Tool: "
                    f"{tool_name}"
                )

            time.sleep(
                RETRY_DELAY_SECONDS
            )

    raise RuntimeError(
        f"工具 {tool_name} "
        "在恢复尝试后仍失败："
        f"{type(last_error).__name__}: "
        f"{last_error}"
    )

# ============================================================
# ReAct Agent
# ============================================================

def react_agent(
    question: str,
    max_steps: int = MAX_STEPS,
    verbose: bool = True,
    conversation_context: str = "",
) -> Dict[str, Any]:
    """
    手写 ReAct Agent 主循环。

    流程：

        User Question
              ↓
          LLM Decision
              ↓
        Thought / Action
              ↓
       Query Normalization
              ↓
           Run Tool
              ↓
         Observation
              ↓
        下一轮 Reasoning
              ↓
         Final Answer

    返回：

        {
            "answer": ...,
            "sources": ...,
            "trace": ...,
            "tools_used": ...,
            "steps": ...,
            "total_time": ...,
            "success": ...
        }
    """

    start_time = time.time()

    # --------------------------------------------------------
    # System Prompt
    # --------------------------------------------------------

    system_prompt = (
        build_agent_system_prompt()
    )

    # --------------------------------------------------------
    # ReAct Scratchpad
    # --------------------------------------------------------

    scratchpad = ""

    # --------------------------------------------------------
    # 可观测性
    # --------------------------------------------------------

    trace: List[Dict[str, Any]] = []

    tools_used: List[str] = []

    # 防止完全相同的 Tool 调用无限重复
    executed_calls = set()

    # ========================================================
    # ReAct Loop
    # ========================================================

    for step in range(
        1,
        max_steps + 1,
    ):

        # ----------------------------------------------------
        # 构建当前 Prompt
        # ----------------------------------------------------

        # ========================================================
        # Conversation Memory
        # ========================================================

        prompt_question = question

        if conversation_context:
            prompt_question = f"""
        下面是当前 Session 的历史对话记忆。

        这些历史信息只用于：
        - 理解代词
        - 理解上下文
        - 理解用户正在讨论哪篇论文

        历史记忆不是论文事实证据。
        具体科研事实仍必须通过 Tool / RAG 验证。

        <ConversationMemory>
        {conversation_context}
        </ConversationMemory>

        <CurrentQuestion>
        {question}
        </CurrentQuestion>
        """

        user_prompt = build_user_prompt(
            question=prompt_question,
            scratchpad=scratchpad,
        )

        # ----------------------------------------------------
        # LLM Decision
        # ----------------------------------------------------

        try:

            llm_response = call_llm_with_retry(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                trace=trace,
                step=step,
                verbose=verbose,
            )

        except Exception as e:

            total_time = (
                time.time()
                - start_time
            )

            error_message = (
                f"Agent 调用语言模型失败："
                f"{type(e).__name__}: {e}"
            )

            trace.append({
                "step": step,
                "type": "llm_error",
                "error": error_message,
            })

            return {
                "answer": error_message,
                "sources": [],
                "trace": trace,
                "tools_used": tools_used,
                "steps": step,
                "total_time": round(
                    total_time,
                    3,
                ),
                "success": False,
            }

        # ----------------------------------------------------
        # Parse
        # ----------------------------------------------------

        parsed = parse_agent_response(
            llm_response
        )

        if verbose:

            print(
                f"\n========== Step {step} =========="
            )

            print(
                llm_response
            )

        # ====================================================
        # CASE 1
        #
        # Agent 直接给出最终答案
        # ====================================================

        if parsed["type"] == "final":

            total_time = (
                time.time()
                - start_time
            )

            final_answer = (
                parsed["final_answer"]
                or ""
            )

            trace.append({
                "step": step,
                "type": "final",
                "answer": final_answer,
                "source": "llm",
            })

            return {
                "answer": final_answer,
                "sources": [],
                "trace": trace,
                "tools_used": tools_used,
                "steps": step,
                "total_time": round(
                    total_time,
                    3,
                ),
                "success": True,
            }

        # ====================================================
        # CASE 2
        #
        # Agent 请求调用 Tool
        # ====================================================

        if parsed["type"] == "action":

            action = (
                parsed["action"]
                or ""
            ).strip()

            action_input = (
                parsed["action_input"]
                or ""
            ).strip()

            # ------------------------------------------------
            # Query Normalization
            # ------------------------------------------------

            effective_input = (
                get_effective_tool_input(
                    action=action,
                    question=question,
                    action_input=action_input,
                )
            )

            # ------------------------------------------------
            # 显示真正执行的 Tool Input
            # ------------------------------------------------

            if verbose:

                print(
                    "\n[Tool Input]"
                )

                print(
                    effective_input
                )

                if (
                    effective_input
                    != action_input
                ):

                    print(
                        "\n[Query Normalized]"
                    )

                    print(
                        f"Agent Input : {action_input}"
                    )

                    print(
                        f"Tool Input  : {effective_input}"
                    )

            # ------------------------------------------------
            # 防止完全相同调用重复执行
            # ------------------------------------------------

            call_key = (
                action,
                effective_input,
            )

            if call_key in executed_calls:

                observation = (
                    "检测到完全相同的 Tool 调用已经执行过，"
                    "请根据已有 Observation 直接回答，"
                    "不要重复调用相同工具。"
                )

                trace.append({
                    "step": step,
                    "type": "duplicate_tool_call",
                    "thought": parsed["thought"],
                    "action": action,
                    "action_input": action_input,
                    "effective_input": effective_input,
                    "observation": observation,
                    "success": False,
                })

                scratchpad += (
                    f"\nThought: "
                    f"{parsed['thought']}\n"
                    f"Action: {action}\n"
                    f"Action Input: {action_input}\n"
                    f"Effective Tool Input: "
                    f"{effective_input}\n"
                    f"Observation: "
                    f"{observation}\n"
                )

                continue




            # =================================================
            # 真正执行 Tool
            # =================================================

            try:

                tool_result = run_tool_with_retry(
                    tool_name=action,
                    tool_input=effective_input,
                    trace=trace,
                    step=step,
                    verbose=verbose,
                )
                executed_calls.add(
                    call_key
                )
                observation = (
                    format_observation(
                        tool_result
                    )
                )

                if verbose:

                    print(
                        "\n[Observation]"
                    )

                    print(
                        observation
                    )

                tools_used.append(
                    action
                )

                trace.append({
                    "step": step,
                    "type": "tool",
                    "thought": parsed["thought"],

                    # Agent 原始生成的输入
                    "action": action,
                    "action_input": action_input,

                    # 真正传给 Tool 的输入
                    "effective_input": effective_input,

                    "observation": observation,
                    "success": True,
                })

                # =============================================
                # Terminal Tool Early Stop
                # =============================================
                #
                # knowledge_base_search 本身已经：
                #
                # Retriever
                # → Reranker
                # → RAG Generation
                # → Citation
                #
                # 因此没有必要重新交给 Agent 生成一次。
                #

                if action in TERMINAL_TOOLS:

                    total_time = (
                        time.time()
                        - start_time
                    )

                    if isinstance(
                        tool_result,
                        dict,
                    ):

                        final_answer = (
                            tool_result.get(
                                "answer",
                                observation,
                            )
                        )

                        sources = (
                            tool_result.get(
                                "sources",
                                [],
                            )
                        )

                    else:

                        final_answer = (
                            observation
                        )

                        sources = []

                    trace.append({
                        "step": step,
                        "type": "final",
                        "answer": final_answer,
                        "source": "terminal_tool",
                    })

                    return {
                        "answer": final_answer,
                        "sources": sources,
                        "trace": trace,
                        "tools_used": tools_used,
                        "steps": step,
                        "total_time": round(
                            total_time,
                            3,
                        ),
                        "success": True,
                    }

            # =================================================
            # Tool Error Recovery
            # =================================================

            except Exception as e:

                primary_error = (

                    f"{type(e).__name__}: {e}"

                )

                # ========================================================

                # Alternative Tool Recovery

                # ========================================================

                fallback_tool = (

                    FALLBACK_TOOLS.get(

                        action

                    )

                )

                fallback_success = False

                if fallback_tool:

                    if verbose:
                        print(

                            "\n[Recovery]"

                        )

                        print(

                            f"{action} 失败，"

                            f"尝试备用工具："

                            f"{fallback_tool}"

                        )

                    try:

                        fallback_result = (

                            run_tool_with_retry(

                                tool_name=(

                                    fallback_tool

                                ),

                                tool_input=(

                                    effective_input

                                ),

                                trace=trace,

                                step=step,

                                verbose=verbose,

                            )

                        )

                        fallback_observation = (

                            format_observation(

                                fallback_result

                            )

                        )

                        observation = (

                            f"原工具 {action} 执行失败。\n"

                            f"Error: {primary_error}\n\n"

                            f"已切换备用工具："

                            f"{fallback_tool}\n\n"

                            f"Fallback Observation:\n"

                            f"{fallback_observation}\n\n"

                            "请根据备用检索结果继续回答，"

                            "不得假装原工具执行成功。"

                        )

                        tools_used.append(

                            fallback_tool

                        )

                        trace.append({

                            "step": step,

                            "type": (

                                "fallback_tool"

                            ),

                            "original_tool": action,

                            "fallback_tool": (

                                fallback_tool

                            ),

                            "effective_input": (

                                effective_input

                            ),

                            "success": True,

                        })

                        fallback_success = True


                    except Exception as fallback_e:

                        observation = (

                            f"原工具 {action} 执行失败："

                            f"{primary_error}\n"

                            f"备用工具 "

                            f"{fallback_tool} "

                            f"也执行失败："

                            f"{type(fallback_e).__name__}: "

                            f"{fallback_e}"

                        )

                        trace.append({

                            "step": step,

                            "type": (

                                "fallback_tool"

                            ),

                            "original_tool": action,

                            "fallback_tool": (

                                fallback_tool

                            ),

                            "effective_input": (

                                effective_input

                            ),

                            "success": False,

                            "error": str(

                                fallback_e

                            ),

                        })


                else:

                    observation = (

                        f"工具 {action} 执行失败："

                        f"{primary_error}。"

                        "当前没有可用的备用工具，"

                        "请尝试使用其他工具，"

                        "或在信息不足时直接说明无法完成。"

                    )

                if verbose:
                    print(

                        "\n[Recovery Observation]"

                    )

                    print(

                        observation

                    )

                trace.append({

                    "step": step,

                    "type": "tool_error",

                    "thought": parsed["thought"],

                    "action": action,

                    "action_input": action_input,

                    "effective_input": (

                        effective_input

                    ),

                    "observation": observation,

                    "fallback_success": (

                        fallback_success

                    ),

                    "success": False,

                })

                # 失败的原始调用也标记为已处理，

                # 防止 Agent 下一轮无限重复同一失败调用。

                executed_calls.add(

                    (

                        action,

                        effective_input,

                    )

                )



            # ------------------------------------------------
            # 写入 ReAct Scratchpad
            # ------------------------------------------------

            scratchpad += (
                f"\nThought: "
                f"{parsed['thought']}\n"
                f"Action: {action}\n"
                f"Action Input: "
                f"{action_input}\n"
                f"Effective Tool Input: "
                f"{effective_input}\n"
                f"Observation: "
                f"{observation}\n"
            )

            continue

        # ====================================================
        # CASE 3
        #
        # 模型输出格式无法解析
        # ====================================================

        trace.append({
            "step": step,
            "type": "invalid",
            "raw_response": llm_response,
        })

        scratchpad += (
            "\nObservation: "
            "你的上一轮输出格式不正确。"
            "如果需要调用工具，请严格使用：\n"
            "Thought: ...\n"
            "Action: ...\n"
            "Action Input: ...\n"
            "如果已经可以回答，请严格使用：\n"
            "Final Answer: ...\n"
        )

    # ========================================================
    # 超过 MAX_STEPS
    # ========================================================

    total_time = (
        time.time()
        - start_time
    )

    return {
        "answer": (
            "Agent 在限定推理步骤内未能完成任务。"
            "请尝试简化问题或重新提问。"
        ),
        "sources": [],
        "trace": trace,
        "tools_used": tools_used,
        "steps": max_steps,
        "total_time": round(
            total_time,
            3,
        ),
        "success": False,
    }


# ============================================================
# Local Test
# ============================================================

if __name__ == "__main__":

    print(
        "[Agent] 初始化知识库..."
    )

    initialize_tools()

    # --------------------------------------------------------
    # 用这个问题专门测试 Query Drift 修复
    # --------------------------------------------------------

    question = (
        "What dataset was used for training "
        "in Attention Is All You Need?"
    )

    result = react_agent(
        question=question,
        verbose=True,
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "FINAL RESULT"
    )

    print(
        "=" * 60
    )

    print(
        result["answer"]
    )

    print(
        "\nSources:"
    )

    print(
        result.get(
            "sources",
            [],
        )
    )

    print(
        "\nTools Used:"
    )

    print(
        result["tools_used"]
    )

    print(
        "\nSteps:"
    )

    print(
        result["steps"]
    )

    print(
        "\nTime:"
    )

    print(
        result["total_time"]
    )

    print(
        "\nSuccess:"
    )

    print(
        result["success"]
    )