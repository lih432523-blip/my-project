import json
import os

from datetime import datetime
from functools import wraps
from inspect import signature
from threading import RLock
from typing import Any, Dict, List


# ============================================================
# Config
# ============================================================

LOG_DIR = "logs"

LOG_PATH = os.path.join(
    LOG_DIR,
    "agent_requests.jsonl",
)

_lock = RLock()

os.makedirs(
    LOG_DIR,
    exist_ok=True,
)


# ============================================================
# Utils
# ============================================================

def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(
        value,
        list,
    ):
        return value

    return []


# ============================================================
# Trace Statistics
# ============================================================

def _get_trace_stats(
    trace: List[Dict[str, Any]],
) -> Dict[str, Any]:

    retry_count = 0

    llm_retry_count = 0

    tool_retry_count = 0

    fallback_count = 0

    fallback_success_count = 0

    duplicate_block_count = 0

    tool_error_count = 0

    invalid_output_count = 0


    for item in trace:

        if not isinstance(
            item,
            dict,
        ):
            continue


        trace_type = item.get(
            "type"
        )


        if trace_type == "llm_retry":

            retry_count += 1

            llm_retry_count += 1


        elif trace_type == "tool_retry":

            retry_count += 1

            tool_retry_count += 1


        elif trace_type == "fallback_tool":

            fallback_count += 1

            if item.get(
                "success",
                False,
            ):

                fallback_success_count += 1


        elif trace_type == "duplicate_tool_call":

            duplicate_block_count += 1


        elif trace_type == "tool_error":

            tool_error_count += 1


        elif trace_type in {
            "invalid",
            "invalid_output",
        }:

            invalid_output_count += 1


    return {

        "retry_count":
            retry_count,

        "llm_retry_count":
            llm_retry_count,

        "tool_retry_count":
            tool_retry_count,

        "fallback_count":
            fallback_count,

        "fallback_success_count":
            fallback_success_count,

        "duplicate_block_count":
            duplicate_block_count,

        "tool_error_count":
            tool_error_count,

        "invalid_output_count":
            invalid_output_count,
    }


# ============================================================
# Build Log Record
# ============================================================

def build_observation_record(
    question: str,
    result: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:

    trace = _safe_list(
        result.get(
            "trace"
        )
    )

    sources = _safe_list(
        result.get(
            "sources"
        )
    )

    tools_used = _safe_list(
        result.get(
            "tools_used"
        )
    )


    timing = result.get(
        "timing",
        {},
    )

    if not isinstance(
        timing,
        dict,
    ):

        timing = {}


    total_time = timing.get(
        "total_time"
    )

    if total_time is None:

        total_time = result.get(
            "total_time",
            0.0,
        )


    trace_stats = (
        _get_trace_stats(
            trace
        )
    )


    record = {

        "timestamp": (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        ),

        "session_id":
            session_id,

        "question":
            question,

        "answer":
            result.get(
                "answer",
                "",
            ),

        "success": bool(
            result.get(
                "success",
                False,
            )
        ),


        # ====================================================
        # Router
        # ====================================================

        "route":
            result.get(
                "route"
            ),

        "route_confidence":
            result.get(
                "route_confidence"
            ),

        "route_reason":
            result.get(
                "route_reason"
            ),


        # ====================================================
        # Agent
        # ====================================================

        "execution_mode":
            result.get(
                "execution_mode"
            ),

        "steps": int(
            result.get(
                "steps",
                0,
            )
            or 0
        ),


        # ====================================================
        # Tool
        # ====================================================

        "tools_used":
            tools_used,

        "tool_count":
            len(
                tools_used
            ),


        # ====================================================
        # Citation
        # ====================================================

        "source_count":
            len(
                sources
            ),

        "sources":
            sources,


        # ====================================================
        # Timing
        # ====================================================

        "total_time": round(
            _safe_float(
                total_time
            ),
            4,
        ),


        # ====================================================
        # Memory
        # ====================================================

        "memory_stats":
            result.get(
                "memory_stats"
            ),


        # ====================================================
        # Trace
        # ====================================================

        "trace":
            trace,
    }


    record.update(
        trace_stats
    )


    # ========================================================
    # Optional RAG Timing
    # ========================================================

    tool_result = result.get(
        "tool_result"
    )

    if isinstance(
        tool_result,
        dict,
    ):

        record[
            "rag_retrieve_time"
        ] = _safe_float(
            tool_result.get(
                "retrieve_time"
            )
        )

        record[
            "rag_generate_time"
        ] = _safe_float(
            tool_result.get(
                "generate_time"
            )
        )


    return record


# ============================================================
# Write Log
# ============================================================

def log_agent_result(
    question: str,
    result: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:

    record = (
        build_observation_record(
            question=question,
            result=result,
            session_id=session_id,
        )
    )


    with _lock:

        with open(
            LOG_PATH,
            "a",
            encoding="utf-8",
        ) as f:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


    return record


# ============================================================
# Decorator
# ============================================================

def observe_agent_call(
    func,
):
    """
    自动记录 agent_chat() 返回结果。

    日志失败不会影响正常问答。
    """

    func_signature = signature(
        func
    )


    @wraps(func)
    def wrapper(
        *args,
        **kwargs,
    ):

        result = func(
            *args,
            **kwargs,
        )


        try:

            bound = (
                func_signature
                .bind_partial(
                    *args,
                    **kwargs,
                )
            )


            question = (
                bound.arguments.get(
                    "question",
                    "",
                )
            )


            session_id = (
                bound.arguments.get(
                    "session_id",
                    "default",
                )
            )


            log_agent_result(
                question=question,
                result=result,
                session_id=session_id,
            )


        except Exception as e:

            # 日志异常不能影响 Agent
            if isinstance(
                result,
                dict,
            ):

                result[
                    "logging_error"
                ] = (
                    f"{type(e).__name__}: {e}"
                )


        return result


    return wrapper


# ============================================================
# Read Logs
# ============================================================

def load_agent_records(
    limit: int = 0,
) -> List[Dict[str, Any]]:

    if not os.path.exists(
        LOG_PATH
    ):

        return []


    records = []


    with _lock:

        with open(
            LOG_PATH,
            "r",
            encoding="utf-8",
        ) as f:

            for line in f:

                line = (
                    line.strip()
                )

                if not line:
                    continue


                try:

                    records.append(
                        json.loads(
                            line
                        )
                    )

                except json.JSONDecodeError:

                    continue


    if (
        limit
        and limit > 0
    ):

        return records[
            -limit:
        ]


    return records


# ============================================================
# Metrics
# ============================================================

def get_agent_metrics() -> Dict[str, Any]:

    records = (
        load_agent_records()
    )


    if not records:

        return {

            "total_requests": 0,

            "success_count": 0,

            "failure_count": 0,

            "success_rate": 0.0,

            "avg_steps": 0.0,

            "avg_latency": 0.0,

            "router_direct_rate": 0.0,

            "react_rate": 0.0,

            "retry_count": 0,

            "fallback_count": 0,

            "fallback_success_count": 0,

            "duplicate_block_count": 0,

            "tool_error_count": 0,

            "tool_usage": {},

            "route_usage": {},

            "execution_mode_usage": {},
        }


    total = len(
        records
    )


    success_count = sum(
        1
        for item in records
        if item.get(
            "success"
        )
    )


    failure_count = (
        total
        - success_count
    )


    avg_steps = (

        sum(
            _safe_float(
                item.get(
                    "steps"
                )
            )
            for item in records
        )

        / total

    )


    avg_latency = (

        sum(
            _safe_float(
                item.get(
                    "total_time"
                )
            )
            for item in records
        )

        / total

    )


    tool_usage = {}

    route_usage = {}

    execution_mode_usage = {}


    retry_count = 0

    fallback_count = 0

    fallback_success_count = 0

    duplicate_block_count = 0

    tool_error_count = 0


    for item in records:


        # ----------------------------------------------------
        # Tool Usage
        # ----------------------------------------------------

        for tool in _safe_list(
            item.get(
                "tools_used"
            )
        ):

            tool_usage[
                tool
            ] = (
                tool_usage.get(
                    tool,
                    0,
                )
                + 1
            )


        # ----------------------------------------------------
        # Route Usage
        # ----------------------------------------------------

        route = item.get(
            "route"
        )

        if route:

            route_usage[
                route
            ] = (
                route_usage.get(
                    route,
                    0,
                )
                + 1
            )


        # ----------------------------------------------------
        # Execution Mode
        # ----------------------------------------------------

        mode = item.get(
            "execution_mode"
        )

        if mode:

            execution_mode_usage[
                mode
            ] = (
                execution_mode_usage.get(
                    mode,
                    0,
                )
                + 1
            )


        # ----------------------------------------------------
        # Recovery
        # ----------------------------------------------------

        retry_count += int(
            item.get(
                "retry_count",
                0,
            )
            or 0
        )


        fallback_count += int(
            item.get(
                "fallback_count",
                0,
            )
            or 0
        )


        fallback_success_count += int(
            item.get(
                "fallback_success_count",
                0,
            )
            or 0
        )


        duplicate_block_count += int(
            item.get(
                "duplicate_block_count",
                0,
            )
            or 0
        )


        tool_error_count += int(
            item.get(
                "tool_error_count",
                0,
            )
            or 0
        )


    direct_count = (
        execution_mode_usage.get(
            "direct_tool",
            0,
        )
    )


    react_count = (
        execution_mode_usage.get(
            "react",
            0,
        )
    )


    return {

        "total_requests":
            total,

        "success_count":
            success_count,

        "failure_count":
            failure_count,

        "success_rate": round(
            success_count
            / total,
            4,
        ),

        "avg_steps": round(
            avg_steps,
            3,
        ),

        "avg_latency": round(
            avg_latency,
            3,
        ),

        "router_direct_rate": round(
            direct_count
            / total,
            4,
        ),

        "react_rate": round(
            react_count
            / total,
            4,
        ),

        "retry_count":
            retry_count,

        "fallback_count":
            fallback_count,

        "fallback_success_count":
            fallback_success_count,

        "duplicate_block_count":
            duplicate_block_count,

        "tool_error_count":
            tool_error_count,

        "tool_usage":
            tool_usage,

        "route_usage":
            route_usage,

        "execution_mode_usage":
            execution_mode_usage,
    }


# ============================================================
# Public Helpers
# ============================================================

def get_recent_requests(
    limit: int = 20,
) -> List[Dict[str, Any]]:

    return load_agent_records(
        limit=limit
    )


def get_log_path() -> str:

    return LOG_PATH