"""Shared paths and model settings; defaults work from any working directory."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", str(PROJECT_ROOT / "data"))).expanduser().resolve()
VECTOR_STORE_DIR = Path(os.getenv("RAG_VECTOR_DIR", str(PROJECT_ROOT / "vector_store"))).expanduser().resolve()
RUNTIME_DIR = PROJECT_ROOT / ".runtime"
LOG_DIR = PROJECT_ROOT / "logs"


def _model_default(folder, identifier):
    legacy = Path("/root/autodl-tmp/models") / folder
    local = PROJECT_ROOT / "models" / folder
    if local.is_dir():
        return str(local)
    return str(legacy) if legacy.is_dir() else identifier


EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", _model_default("bge-large-zh", "BAAI/bge-large-zh-v1.5"))
RERANKER_MODEL = os.getenv("RAG_RERANKER_MODEL", _model_default("bge-reranker-base", "BAAI/bge-reranker-base"))
MODEL_DEVICE = os.getenv("RAG_MODEL_DEVICE", "cpu")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if "://" not in OLLAMA_HOST:
    OLLAMA_HOST = "http://" + OLLAMA_HOST
OLLAMA_MODEL = os.getenv("RAG_LLM_MODEL", "qwen2.5:7b")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _optional_integer(name, minimum):
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


LLM_NUM_GPU = _optional_integer("RAG_LLM_NUM_GPU", 0)
LLM_NUM_CTX = _optional_integer("RAG_LLM_NUM_CTX", 1)
LLM_TIMEOUT = int(os.getenv("RAG_LLM_TIMEOUT", "120"))
if LLM_TIMEOUT <= 0:
    raise ValueError("RAG_LLM_TIMEOUT must be positive")
LLM_KEEP_ALIVE = os.getenv("RAG_LLM_KEEP_ALIVE", "5m")


def llm_options(temperature=None):
    """Shared request options so the probe, Agent and RAG use the same settings."""
    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if LLM_NUM_GPU is not None:
        options["num_gpu"] = LLM_NUM_GPU
    if LLM_NUM_CTX is not None:
        options["num_ctx"] = LLM_NUM_CTX
    return options
