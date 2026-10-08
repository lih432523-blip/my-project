"""UI integration boundary for C/D interfaces; serializes shared index mutations."""
import hashlib
import importlib.util
import math
import os
import tempfile
import time
import uuid
from pathlib import Path
from threading import RLock

from src.config import DATA_DIR, RUNTIME_DIR, MAX_UPLOAD_BYTES, OLLAMA_MODEL
from src.frontend.state import atomic_json, now


class FrontendError(RuntimeError):
    pass


def normalize_result(value):
    if not isinstance(value, dict):
        raise FrontendError("Agent 返回格式异常：预期为字典。")
    result = dict(value)
    result["answer"] = str(result.get("answer") or "未返回答案，请查看执行记录。")
    result["success"] = bool(result.get("success", False))
    for name in ("sources", "trace", "tools_used"):
        if not isinstance(result.get(name), list):
            result[name] = []
    # Keep one source/page card; the original response stays available in JSON export.
    sources, seen = [], set()
    for source in result["sources"]:
        if not isinstance(source, dict) or not source.get("source"):
            continue
        key = (str(source["source"]), str(source.get("page", "?")))
        if key not in seen:
            sources.append(source)
            seen.add(key)
    result["sources"] = sources
    result["trace"] = [step for step in result["trace"] if isinstance(step, dict)]
    if not isinstance(result.get("timing"), dict):
        result["timing"] = {}
    result["timing"].setdefault("total_time", result.get("total_time"))
    return result


def number(value):
    try:
        converted = float(value)
        return converted if math.isfinite(converted) else None
    except (TypeError, ValueError):
        return None


def typewriter(text, enabled=True):
    """Presentation streaming only: agent_chat currently returns a complete answer."""
    if not enabled:
        yield text
        return
    for start in range(0, len(text), 18):
        yield text[start:start + 18]
        time.sleep(0.008)


class BackendService:
    def __init__(self, data_dir=DATA_DIR, runtime_dir=RUNTIME_DIR):
        self.data_dir = Path(data_dir).resolve()
        self.runtime_dir = Path(runtime_dir).resolve()
        self.manifest_path = self.runtime_dir / "index_state.json"
        self.lock = RLock()
        self.ready_fingerprint = None
        self.last_error = None

    def _document_path(self, name):
        if not name or Path(name).name != name or "/" in name or "\\" in name:
            raise FrontendError("文件名不能包含目录。")
        path = self.data_dir / name
        if path.is_symlink() or path.resolve().parent != self.data_dir:
            raise FrontendError("文件路径不在文档目录内。")
        return path

    def _fingerprint(self):
        return {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(self.data_dir.glob("*.pdf")) if not path.is_symlink()}

    def _manifest(self):
        if self.manifest_path.exists():
            import json
            try:
                value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                return value if isinstance(value, dict) else {}
            except (ValueError, OSError):
                pass
        return {}

    def documents(self):
        with self.lock:
            fingerprint = self._fingerprint()
            previous = self._manifest()
            ready = self.ready_fingerprint == fingerprint and bool(fingerprint)
            items = []
            for name, digest in fingerprint.items():
                path = self._document_path(name)
                if ready:
                    status = "已向量化"
                elif self.last_error:
                    status = "建库失败，可重试"
                elif previous.get("files", {}).get(name) == digest:
                    status = "待恢复索引"
                else:
                    status = "待向量化"
                items.append({"name": name, "size": path.stat().st_size, "status": status})
            return items

    def _invalidate(self):
        self.ready_fingerprint = None
        self.last_error = None
        # Invalidate D's lazy initialization flag; the next query must rebuild.
        import sys
        tools = sys.modules.get("src.agent.tools")
        if tools is not None:
            tools._initialized = False
        generation = sys.modules.get("src.generation")
        rag = getattr(generation, "_rag_instance", None)
        if rag is not None:
            rag.hybrid = None

    def upload(self, name, data):
        with self.lock:
            if not isinstance(data, bytes):
                raise FrontendError("上传内容必须是文件字节。")
            if not data or len(data) > MAX_UPLOAD_BYTES:
                raise FrontendError("文件为空或超过 50 MB 限制。")
            if Path(name).suffix.lower() != ".pdf" or not data.lstrip().startswith(b"%PDF-"):
                raise FrontendError("当前后端仅支持 PDF，请上传有效的 PDF 文件。")
            # C scans lowercase *.pdf; normalize the suffix without losing the paper title.
            name = str(Path(name).with_suffix(".pdf"))
            path = self._document_path(name)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if path.exists():
                if path.read_bytes() == data:
                    return {"name": name, "status": "文件已存在，已跳过"}
                raise FrontendError(f"同名文件 {name} 已存在，请重命名后上传。")
            # Never overwrite a collaborator's original paper.
            fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=self.data_dir)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            self._invalidate()
            return {"name": name, "status": "上传成功，待向量化"}

    def delete_document(self, name):
        with self.lock:
            path = self._document_path(name)
            if not path.is_file():
                raise FrontendError("文档不存在。")
            trash = self.data_dir / ".trash" / uuid.uuid4().hex
            trash.mkdir(parents=True, exist_ok=True)
            target = trash / name
            path.rename(target)
            self._invalidate()
            return target

    def read_document(self, source):
        with self.lock:
            path = self._document_path(str(source))
            if not path.is_file():
                raise FrontendError("原文件已删除或不在当前知识库中。")
            return path.read_bytes()

    def build_index(self):
        with self.lock:
            fingerprint = self._fingerprint()
            if not fingerprint:
                raise FrontendError("知识库为空，请先上传 PDF。")
            self._invalidate()
            try:
                # C's loader swallows parsing errors. Validate first so a partial corpus
                # cannot be incorrectly labelled as fully indexed by the UI.
                import pdfplumber
                for name in fingerprint:
                    with pdfplumber.open(self._document_path(name)) as pdf:
                        if not any((page.extract_text() or "").strip() for page in pdf.pages):
                            raise FrontendError(f"{name} 没有可提取文本；扫描件需先做 OCR。")
                from src.agent.tools import refresh_knowledge_base
                count = refresh_knowledge_base()
                if not count:
                    raise FrontendError("后端未生成有效文本块。")
                self.ready_fingerprint = fingerprint
                atomic_json(self.manifest_path, {"files": fingerprint, "chunks": count, "built_at": now()})
                self.last_error = None
                return count
            except Exception as exc:
                self._invalidate()
                self.last_error = f"{type(exc).__name__}: {exc}"
                raise FrontendError(f"知识库构建失败：{self.last_error}") from exc

    def chat(self, question, session_id, use_memory=True, history=()):
        with self.lock:
            if not question.strip():
                raise FrontendError("问题不能为空。")
            if len(question) > 12000:
                raise FrontendError("问题过长，请控制在 12000 字符以内。")
            try:
                from src.agent import agent_chat
                from src.agent.router import route_question
                route = route_question(question)["route"]
                if route != "current_time":
                    if self.ready_fingerprint != self._fingerprint() or not self.ready_fingerprint:
                        self.build_index()
                if use_memory:
                    self._restore_memory(session_id, history)
                return normalize_result(agent_chat(question=question, session_id=session_id,
                                                   use_memory=use_memory, verbose=False))
            except FrontendError:
                raise
            except Exception as exc:
                raise FrontendError(f"问答失败：{type(exc).__name__}: {exc}") from exc

    def _restore_memory(self, session_id, history):
        # Use D's public memory APIs to resume a persisted UI conversation after restart.
        from src.agent.memory import get_memory_stats, add_memory_message, set_active_paper
        if get_memory_stats(session_id)["total_messages"] or not history:
            return
        for message in history[-12:]:
            if message.get("role") in {"user", "assistant"}:
                add_memory_message(session_id, message["role"], message.get("content", ""))
        for message in reversed(history):
            stats = message.get("result", {}).get("memory_stats") or {}
            if stats.get("active_paper"):
                set_active_paper(session_id, stats["active_paper"])
                break

    def clear_session(self, session_id):
        with self.lock:
            from src.agent.memory import clear_memory
            clear_memory(session_id)

    def health(self):
        with self.lock:
            from src.agent import get_system_health
            health = get_system_health()
            packages = {name: importlib.util.find_spec(name) is not None for name in
                        ("pdfplumber", "chromadb", "sentence_transformers", "rank_bm25", "jieba", "ollama")}
            health["dependencies"] = packages
            health["model_available"] = any(
                str(name).removesuffix(":latest") == OLLAMA_MODEL.removesuffix(":latest")
                for name in health.get("ollama", {}).get("models", []))
            health["rag"]["initialized"] = bool(self.ready_fingerprint) and self.ready_fingerprint == self._fingerprint()
            health["index_error"] = self.last_error
            return health

    def metrics(self):
        with self.lock:
            from src.agent import get_agent_metrics
            return get_agent_metrics()
