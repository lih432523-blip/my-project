import json
import os
import urllib.request

from pathlib import Path
from typing import Any, Dict

import src.agent.tools as agent_tools

from src.agent.observability import (
    LOG_PATH,
)


# ============================================================
# Config
# ============================================================

PROJECT_ROOT = Path(
    "/root/autodl-tmp/rag_project"
)

DATA_DIR = (
    PROJECT_ROOT
    / "data"
)

VECTOR_STORE_DIR = (
    PROJECT_ROOT
    / "vector_store"
)

OLLAMA_URL = (
    "http://127.0.0.1:11434/api/tags"
)


# ============================================================
# Ollama
# ============================================================

def _check_ollama() -> Dict[str, Any]:

    try:

        request = (
            urllib.request.Request(
                OLLAMA_URL,
                method="GET",
            )
        )


        with urllib.request.urlopen(
            request,
            timeout=3,
        ) as response:

            data = json.loads(
                response
                .read()
                .decode(
                    "utf-8"
                )
            )


        models = []


        for item in data.get(
            "models",
            [],
        ):

            name = item.get(
                "name"
            )

            if name:

                models.append(
                    name
                )


        return {

            "status": "ok",

            "models": models,
        }


    except Exception as e:

        return {

            "status": "unavailable",

            "models": [],

            "error": (
                f"{type(e).__name__}: {e}"
            ),
        }


# ============================================================
# Observability
# ============================================================

def _check_log() -> Dict[str, Any]:

    log_path = Path(
        LOG_PATH
    )

    log_dir = (
        log_path.parent
    )


    try:

        log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


        writable = os.access(
            log_dir,
            os.W_OK,
        )


        return {

            "status": (
                "ok"
                if writable
                else "not_writable"
            ),

            "path": str(
                log_path
            ),
        }


    except Exception as e:

        return {

            "status": "error",

            "path": str(
                log_path
            ),

            "error": (
                f"{type(e).__name__}: {e}"
            ),
        }


# ============================================================
# System Health
# ============================================================

def get_system_health() -> Dict[str, Any]:
    """
    系统集成 Health Check。

    注意：

    不主动执行 initialize_tools()
    或 build_index()。

    Health Check 不应触发昂贵初始化。
    """

    # ========================================================
    # Ollama
    # ========================================================

    ollama = (
        _check_ollama()
    )


    # ========================================================
    # PDF Corpus
    # ========================================================

    pdf_files = []


    if DATA_DIR.exists():

        pdf_files = sorted(
            path.name
            for path
            in DATA_DIR.glob(
                "*.pdf"
            )
        )


    # ========================================================
    # RAG
    # ========================================================

    rag_initialized = bool(
        getattr(
            agent_tools,
            "_initialized",
            False,
        )
    )


    vector_store_exists = (
        VECTOR_STORE_DIR.exists()
    )


    # ========================================================
    # Agent Tools
    # ========================================================

    tools = list(
        agent_tools.TOOLS.keys()
    )


    # ========================================================
    # Observability
    # ========================================================

    log_status = (
        _check_log()
    )


    # ========================================================
    # Checks
    # ========================================================

    checks = {

        "agent_tools": (
            len(
                tools
            )
            > 0
        ),

        "ollama": (
            ollama.get(
                "status"
            )
            == "ok"
        ),

        "pdf_corpus": (
            len(
                pdf_files
            )
            > 0
        ),

        "vector_store": (
            vector_store_exists
        ),

        "observability_log": (
            log_status.get(
                "status"
            )
            == "ok"
        ),
    }


    overall_ok = all(
        checks.values()
    )


    # ========================================================
    # Result
    # ========================================================

    return {

        "status": (
            "ok"
            if overall_ok
            else "degraded"
        ),


        "checks":
            checks,


        "agent": {

            "status": "ok",

            "tool_count": len(
                tools
            ),

            "tools": tools,
        },


        "rag": {

            "initialized":
                rag_initialized,

            "vector_store_exists":
                vector_store_exists,
        },


        "knowledge_base": {

            "pdf_count": len(
                pdf_files
            ),

            "pdf_files":
                pdf_files,
        },


        "ollama":
            ollama,


        "observability":
            log_status,
    }