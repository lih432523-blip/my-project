"""Module 5 evaluation helper. Templates and smoke tests are never course results.

Only the run command imports the RAG/Agent backend. Other commands use stdlib.
Gold retrieval units are (PDF filename, one-based physical PDF page), not chunks.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ("factual", "comparison", "summary", "reasoning")
METHODS = ("vector", "hybrid", "hybrid_rerank")
REVIEW_FIELDS = (
    "run_id", "id", "category", "mode", "method", "chunk_size", "question",
    "answer", "reference_answer", "gold_evidence", "actual_tools",
    "accepted_tool_sets", "auto_tool_match", "route", "execution_mode", "steps",
    "wall_latency_s", "success", "correctness", "completeness", "citation_accuracy",
    "routing", "bad_case", "note",
)
SUMMARY_FIELDS = (
    "mode", "chunk_size", "method", "category", "execution_mode", "n", "failures",
    "hit_at_5", "mrr_at_5", "recall_at_5", "retrieval_gold_n",
    "avg_wall_latency_s", "p95_wall_latency_s", "avg_steps", "tool_match_rate",
    "tool_gold_n", "tool_expected_n", "tool_coverage", "avg_tokens", "token_coverage",
    "correctness", "correctness_n", "completeness", "completeness_n",
    "citation_accuracy", "citation_accuracy_n", "routing", "routing_n", "manual_n",
)


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    delays = (0.05, 0.1, 0.2, 0.4, 0.8, 1.6)
    for attempt in range(len(delays) + 1):
        try:
            os.replace(temporary, path)
            return
        except PermissionError as exc:
            if getattr(exc, "winerror", None) not in (5, 32, 33):
                raise
            if attempt == len(delays):
                # This file is already complete, closed and fsynced. Metadata
                # checkpoints can use it without touching the locked target.
                exc.pending_json_path = str(temporary)
                raise
            time.sleep(delays[attempt])


def read_metadata_record(path):
    """Read the newest durable metadata revision, including locked-target snapshots."""
    path = Path(path)
    candidates = [path, *path.parent.glob(f".{path.name}.*.tmp")]
    records = []
    primary_run_id = None
    for candidate in candidates:
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (ValueError, UnicodeError):
            if candidate == path:
                raise ValueError(f"Invalid primary metadata: {path}")
            continue  # An interrupted temporary write is not a durable revision.
        if not isinstance(value, dict) or not value.get("run_id"):
            if candidate == path:
                raise ValueError(f"Metadata has no run_id: {path}")
            continue
        revision = value.get("metadata_revision", 0)
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ValueError(f"Invalid metadata revision: {candidate}")
        if candidate == path:
            primary_run_id = value["run_id"]
        records.append((revision, value, candidate))
    if not records:
        raise FileNotFoundError(f"No valid metadata or durable checkpoint found: {path}")
    run_ids = {record[1]["run_id"] for record in records}
    if len(run_ids) != 1 or (primary_run_id and run_ids != {primary_run_id}):
        raise ValueError(f"Metadata checkpoints contain different run IDs: {path.parent}")
    latest_revision = max(record[0] for record in records)
    latest = [record for record in records if record[0] == latest_revision]
    if any(record[1] != latest[0][1] for record in latest[1:]):
        raise ValueError(f"Conflicting metadata for revision {latest_revision}: {path.parent}")
    return latest[0][1], latest[0][2]


def read_metadata(path):
    return read_metadata_record(path)[0]


def write_metadata(path, value):
    """A temporary Windows target lock must not discard completed evaluation rows."""
    value["metadata_revision"] = value.get("metadata_revision", 0) + 1
    try:
        write_json(path, value)
    except PermissionError as exc:
        snapshot = getattr(exc, "pending_json_path", None)
        if not snapshot:
            raise  # Directory permissions, disk writes and fsync still fail clearly.
        print(f"[checkpoint warning] Metadata target remains locked; durable recovery snapshot: {snapshot}. Continuing evaluation.", file=sys.stderr, flush=True)


def write_csv(path, rows, fields):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fresh_directory(path):
    path = Path(path).expanduser().resolve()
    if path.exists():
        raise ValueError(f"Output already exists; choose a new --out to preserve results: {path}")
    path.mkdir(parents=True)
    return path


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Line {number}: expected a JSON object")
            rows.append(row)
    return rows


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def pdf_files(data):
    path = Path(data).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"PDF directory does not exist: {path}")
    return sorted(path.glob("*.pdf"))


def validate_qa(qa, data, smoke=False):
    rows = read_jsonl(qa)
    files = pdf_files(data)
    sources = {p.name for p in files}
    errors, warnings, ids, counts = [], [], set(), Counter()
    if not files:
        errors.append("No PDF files directly in --data (subdirectories are not loaded).")
    if not smoke and not 10 <= len(files) <= 20:
        errors.append(f"Formal corpus requires 10-20 PDF papers; found {len(files)}.")
    if not smoke and len(rows) < 50:
        errors.append(f"Formal QA requires at least 50 rows (55 recommended); found {len(rows)}.")
    if not rows:
        errors.append("QA file is empty.")
    if not smoke and 50 <= len(rows) < 55:
        warnings.append("Only 50-54 QA rows; use 55 if following the team plan.")
    for index, row in enumerate(rows, 1):
        prefix = f"Row {index} ({row.get('id', '?')})"
        identifier = row.get("id")
        if not nonblank(identifier) or identifier in ids:
            errors.append(f"{prefix}: id must be a unique nonempty string.")
        elif identifier:
            ids.add(identifier)
        category = row.get("category")
        if category not in CATEGORIES:
            errors.append(f"{prefix}: category must be one of {CATEGORIES}.")
        else:
            counts[category] += 1
        for field in ("question", "reference_answer"):
            if not nonblank(row.get(field)):
                errors.append(f"{prefix}: {field} is blank; unfinished templates cannot be evaluated.")
        evidence = row.get("gold_evidence")
        if not isinstance(evidence, list):
            errors.append(f"{prefix}: gold_evidence must be a list.")
            evidence = []
        if not evidence and row.get("answerable", True) is not False:
            errors.append(f"{prefix}: supply gold_evidence or explicitly set answerable=false for a no-answer case.")
        if row.get("answerable", True) is False and evidence:
            errors.append(f"{prefix}: answerable=false must have an empty gold_evidence list.")
        for gold in evidence:
            if not isinstance(gold, dict):
                errors.append(f"{prefix}: each gold_evidence item must be an object.")
                continue
            if gold.get("source") not in sources:
                errors.append(f"{prefix}: unknown PDF source {gold.get('source')!r}; use the exact filename.")
            page = gold.get("page")
            if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
                errors.append(f"{prefix}: page must be a positive integer (physical PDF page).")
            if not nonblank(gold.get("evidence")):
                errors.append(f"{prefix}: evidence must contain the manually verified original passage.")
        tool_sets = row.get("accepted_tool_sets", [])
        if not isinstance(tool_sets, list) or any(
            not isinstance(group, list) or any(not nonblank(tool) for tool in group)
            for group in tool_sets
        ):
            errors.append(f"{prefix}: accepted_tool_sets must be a list of complete allowed tool lists.")
    if not smoke:
        for category in CATEGORIES:
            if counts[category] == 0:
                errors.append(f"No {category} questions; formal QA must include all four categories.")
    report = {
        "valid": not errors, "smoke": smoke, "qa_rows": len(rows),
        "pdf_count": len(files), "categories": dict(counts),
        "errors": errors, "warnings": warnings,
        "scope": "Checks schema and source existence only; humans must verify evidence and PDF page bounds.",
    }
    return rows, report


def command_init(args):
    out = fresh_directory(args.out)
    counts = (20, 15, 10, 10)
    rows = []
    for category, count in zip(CATEGORIES, counts):
        for number in range(1, count + 1):
            rows.append({
                "id": f"{category[:3]}-{number:03d}", "category": category,
                "question": "", "reference_answer": "", "answerable": True,
                "gold_evidence": [{"source": "", "page": None, "evidence": ""}],
                "accepted_tool_sets": [],
            })
    with (out / "qa.template.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out / "SCORING.md").write_text(
        "# 人工标注与评分规范\n\n"
        "这是55条空白模板（事实20、比较15、总结10、推理10），不是运行成绩。"
        "填写后另存为 qa.jsonl；不要用模型输出倒推标准答案。\n\n"
        "每题填写 question、reference_answer，并核对 gold_evidence：source必须是data根目录的PDF文件名，"
        "page是从1开始的PDF物理页码，evidence为对应页的原文。一个问题可有多个证据页。"
        "只有确实无答案的附加题才设answerable=false和gold_evidence=[]；这类题不参与检索指标。\n\n"
        "accepted_tool_sets在运行前标注。例如 [[\"paper_compare\"]]，或多个确实允许的完整集合。"
        "外层 [] 表示未标注；[[]] 表示正确行为是不调用任何工具。自动匹配比较完整工具集合（顺序不计），"
        "仅用于路由预检查；仍需人工核对工具输入、输出和推理是否合理。\n\n"
        "review.csv的correctness、completeness、citation_accuracy均填0/1/2："
        "0为错误/缺失，1为部分正确/完整/支持，2为正确、完整且有支持。"
        "correctness看事实是否准确；completeness看问题的要点是否覆盖；citation_accuracy核对引用页是否支持相应论断。"
        "routing填0或1，判断完整调用是否合理；未审阅留空，不把空值当0。"
        "bad_case统一填retrieval（漏召回/错检）、generation（事实错误/无根据回答/遗漏）、"
        "citation（引用错误）、agent（路由/工具/执行问题）或none（未发现错误）；"
        "多类用分号，例如retrieval;generation。note写具体错误、原文依据及改进。\n\n"
        "Hit@5=前5结果含任一金标准文件+页码；MRR@5=首个匹配的倒数排名；"
        "Recall@5=前5结果覆盖的唯一金标准文件+页码数/全部唯一金标准页数。"
        "同一页多个chunk只计一次Recall覆盖。失败题的检索指标计0；无gold题不参与检索指标。"
        "该指标是证据页召回，不等于答案正确率；success只是系统执行状态。\n\n"
        "avg_steps是系统返回的平均执行步骤，execution_mode=react分组才可描述ReAct步骤。"
        "Token只汇总覆盖全部LLM调用的真实计数；缺失标N/A并报告覆盖率。"
        "不得把模板、模拟测试、smoke结果作为正式实验成绩。\n",
        encoding="utf-8",
    )
    print(f"Created blank templates: {out}\nFill and verify them before running check. NOT evaluation results.")


def command_check(args):
    _, report = validate_qa(args.qa, args.data, args.smoke)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


def key(item):
    try:
        page = int(item.get("page"))
    except (TypeError, ValueError):
        return None
    source = item.get("source")
    if not source or page < 1:
        return None
    return (str(source).replace("\\", "/").split("/")[-1].casefold(), page)


def retrieval_metrics(gold, results, success=True):
    relevant = {key(item) for item in gold if key(item) is not None}
    if not relevant:
        return {"hit_at_5": None, "mrr_at_5": None, "recall_at_5": None}
    retrieved = [key(item) for item in results[:5]] if success else []
    ranks = [rank for rank, item in enumerate(retrieved, 1) if item in relevant]
    return {
        "hit_at_5": int(bool(ranks)),
        "mrr_at_5": 1.0 / min(ranks) if ranks else 0.0,
        "recall_at_5": len(relevant.intersection(retrieved)) / len(relevant),
    }


def tools_match(allowed, actual, success=True):
    if not allowed:
        return None
    # A correct tool choice can still fail during execution. Keep those measures separate.
    return int(any(set(actual) == set(group) for group in allowed))


def csv_value(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return "N/A" if value is None else value


def review_row(row):
    mapped = dict(row)
    mapped["actual_tools"] = row.get("tools_used", [])
    return {field: csv_value(mapped.get(field, "")) for field in REVIEW_FIELDS}


def make_metadata(args, files):
    packages = {}
    for package in ("torch", "chromadb", "sentence-transformers", "rank-bm25", "pdfplumber", "ollama", "streamlit"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = "not installed"
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip() or "N/A"
    except (OSError, subprocess.TimeoutExpired):
        commit = "N/A"
    corpus = [{"source": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in files]
    return {
        "run_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "started_at": now(), "smoke": args.smoke, "python": sys.version,
        "platform": platform.platform(), "processor": platform.processor(),
        "packages": packages, "git_commit": commit, "script_sha256": digest(__file__),
        "token_script_sha256": digest(Path(__file__).with_name("module5_tokens.py")) if Path(__file__).with_name("module5_tokens.py").is_file() else None,
        "backend_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "src").rglob("*.py"))},
        "qa_path": str(Path(args.qa).resolve()), "qa_sha256": digest(args.qa),
        "corpus": corpus,
        "corpus_sha256": hashlib.sha256(json.dumps(corpus, sort_keys=True).encode()).hexdigest(),
        "parameters": {"mode": args.mode, "chunk_size": args.chunk_size, "overlap": 50, "recall_k": 20, "top_k": 5, "limit": args.limit, "use_memory": False},
        "notes": ["Gold retrieval unit: exact PDF filename and physical PDF page.", "Backend explicit config construction records index provenance/storage in runtime; each evaluation output is new.", "No correctness score is inferred from backend success."],
    }


def _ollama_json(request, timeout, action, host, model):
    """Read one nonstreaming local Ollama response with actionable failures."""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(
            f"Ollama {action} failed (HTTP {exc.code}) at {host}: {body}. "
            f"Check the service and run: ollama pull {model}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Cannot reach/load Ollama during {action} at {host}: {type(exc).__name__}: {exc}. "
            f"Start the service with ollama serve; confirm the model with ollama pull {model}, then retry."
        ) from exc
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError(f"Ollama {action} returned invalid JSON at {host}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("error"):
        raise RuntimeError(
            f"Ollama {action} returned an error at {host}: {str(payload)[:1000]}. "
            f"Check the service and run: ollama pull {model}"
        )
    return payload


def preflight_ollama(mode):
    """Fail before creating output/loading embeddings if a required LLM is unusable."""
    if mode == "retrieval":
        return {"required": False, "status": "not_required"}
    # src.config imports only stdlib. Heavy RAG/Agent imports remain in prepare_backend.
    sys.path.insert(0, str(ROOT))
    from src import config
    host, model = config.OLLAMA_HOST.rstrip("/"), config.OLLAMA_MODEL
    started = time.perf_counter()
    tags = _ollama_json(host + "/api/tags", 10, "model-list check", host, model)
    tags_seconds = time.perf_counter() - started
    listed = tags.get("models")
    if not isinstance(listed, list):
        raise RuntimeError(f"Ollama /api/tags has no valid models list at {host}; check the service.")
    selected = next((entry for entry in listed if isinstance(entry, dict)
                     and model in (entry.get("name"), entry.get("model"))), None)
    if selected is None:
        available = [entry.get("name", entry.get("model")) for entry in listed if isinstance(entry, dict)]
        raise RuntimeError(
            f"Required Ollama model {model!r} is not installed at {host}. Available models: {available}. "
            f"Run: ollama pull {model}. Wait for the download to finish, then retry. "
            "No output directory/index was created; no substitute model was selected."
        )
    configured_options = config.llm_options(0) if callable(getattr(config, "llm_options", None)) else {"temperature": 0}
    probe_options = {**configured_options, "num_predict": 1}
    probe_timeout = getattr(config, "LLM_TIMEOUT", 120)
    body = json.dumps({
        "model": model, "messages": [{"role": "user", "content": "Hi"}],
        "stream": False, "options": probe_options,
        "keep_alive": getattr(config, "LLM_KEEP_ALIVE", "5m"),
    }).encode("utf-8")
    request = urllib.request.Request(host + "/api/chat", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
    probe_started = time.perf_counter()
    probe = _ollama_json(request, probe_timeout, "one-token generation probe", host, model)
    probe_seconds = time.perf_counter() - probe_started
    message = probe.get("message")
    if probe.get("done") is not True or not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise RuntimeError(f"Ollama generation probe did not return a completed chat response for {model!r}; stop before building the index.")
    info = {
        "required": True, "status": "ready", "checked_at": now(), "host": host,
        "model": model, "model_digest": selected.get("digest"),
        "keep_alive": getattr(config, "LLM_KEEP_ALIVE", "5m"),
        "tags_duration_s": round(tags_seconds, 6), "probe_duration_s": round(probe_seconds, 6),
        "duration_s": round(time.perf_counter() - started, 6),
        "probe": {"num_predict": 1, "options": probe_options, "timeout_s": probe_timeout, "done": probe["done"],
                  "prompt_eval_count": probe.get("prompt_eval_count"), "eval_count": probe.get("eval_count")},
        "scope": "Connectivity/model-load probe only; excluded from formal per-question latency and Token metrics.",
    }
    print(f"[preflight] Ollama model {model} is installed and loadable; digest={info['model_digest']}, probe={probe_seconds:.3f}s.")
    return info


def infrastructure_warmup_failure(result, model=None):
    """Identify model/connection failures without treating task quality failures as outages."""
    if not isinstance(result, dict) or result.get("success", True) is not False:
        return False
    # Avoid letting a question/title containing "model" turn a missing-paper error into an outage.
    detail = json.dumps({name: result.get(name) for name in ("answer", "error", "trace")}, ensure_ascii=False, default=str).casefold()
    network_markers = (
        "ollama connection failed", "connection refused", "connection reset",
        "failed to establish a new connection", "cannot connect to ollama",
        "winerror 10061", "winerror 10054", "connecterror",
        "ollama request timed out", "ollama request timeout", "ollama http error",
    )
    if any(marker in detail for marker in network_markers):
        return True
    model_context = any(marker in detail for marker in ("ollama", "responseerror", "llm_error", "status code"))
    if model:
        model_context = model_context or str(model).casefold() in detail
    return model_context and "model" in detail and any(marker in detail for marker in (
        "not found", "does not exist", "failed to load", "unable to load", "insufficient memory",
    ))


def validate_reuse_index(args, metadata, embedding_model):
    """Validate provenance before opening an existing persisted index; QA may differ."""
    origin = Path(args.reuse_index).expanduser().resolve()
    previous_path = origin / "metadata.json"
    vector_dir = origin / "vector_store"
    if not (vector_dir / "chroma.sqlite3").is_file():
        raise ValueError(f"--reuse-index requires an original run with metadata.json and vector_store/chroma.sqlite3: {origin}")
    previous = read_metadata(previous_path)
    if not isinstance(previous, dict):
        raise ValueError("Reused index metadata must be an object.")
    if not metadata.get("corpus_sha256") or previous.get("corpus_sha256") != metadata["corpus_sha256"]:
        raise ValueError("Reused index corpus_sha256 differs from the current PDF corpus; build a new index.")
    parameters = previous.get("parameters", {})
    for name, expected in (("chunk_size", args.chunk_size), ("overlap", 50)):
        if parameters.get(name) != expected:
            raise ValueError(f"Reused index {name}={parameters.get(name)!r} differs from requested {expected}; build a new index.")
    if parameters.get("chunk_method", "recursive") != "recursive":
        raise ValueError("Reused index was not built with recursive chunking.")
    if previous.get("runtime", {}).get("embedding_model") != embedding_model:
        raise ValueError("Reused index embedding model differs from src.config.EMBEDDING_MODEL; build a new index.")
    old_hashes = {name.replace("\\", "/"): value for name, value in previous.get("backend_sha256", {}).items()}
    new_hashes = {name.replace("\\", "/"): value for name, value in metadata.get("backend_sha256", {}).items()}
    relevant = (
        "src/data_loader/__init__.py", "src/data_loader/pdf_loader.py",
        "src/chunking/__init__.py", "src/chunking/chunker.py",
        "src/retrieval/__init__.py", "src/retrieval/vector_store.py",
    )
    for name in relevant:
        if not new_hashes.get(name) or old_hashes.get(name) != new_hashes[name]:
            raise ValueError(f"Reused index source hash differs or is missing for {name}; build a new index.")
    chunk_count = previous.get("chunk_count")
    if not isinstance(chunk_count, int) or isinstance(chunk_count, bool) or chunk_count < 20:
        raise ValueError("Reused metadata must contain a valid chunk_count >=20.")
    corpus_sources = sorted(entry["source"] for entry in metadata.get("corpus", []))
    if not corpus_sources or sorted(previous.get("indexed_sources", [])) != corpus_sources:
        raise ValueError("Reused index indexed_sources differs from the complete current PDF source list.")
    checks = {
        "corpus_sha256": "matched", "chunk_size": args.chunk_size, "overlap": 50,
        "chunk_method": "recursive", "embedding_model": embedding_model,
        "backend_hashes": {name: new_hashes[name] for name in relevant},
        "expected_chunk_count": chunk_count, "indexed_sources": corpus_sources,
        "qa_hash_required": False,
        "previous_run_status": previous.get("status"),
    }
    return {"origin": origin, "vector_dir": vector_dir, "previous": previous, "checks": checks}


def open_existing_vector_store(vector_store_class, model_path, persist_dir, device):
    """Open the existing collection, avoiding VectorStore's get_or_create path."""
    import chromadb
    from sentence_transformers import SentenceTransformer
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_collection(name="papers")  # Missing collection raises; never create one.
    vs = vector_store_class.__new__(vector_store_class)
    vs.client, vs.collection = client, collection
    vs.model = SentenceTransformer(model_path, device=device)
    return vs


def assemble_reused_index(args, rag, reuse, metadata):
    """Rebuild in-memory chunks/BM25 and verify persisted IDs/text/pages without writes."""
    from src.data_loader.pdf_loader import load_pdfs_from_dir
    from src.chunking.chunker import chunk_pages
    from src.retrieval.bm25_retriever import BM25Retriever
    from src.retrieval.hybrid_retriever import HybridRetriever
    started = time.perf_counter()
    expected_count = reuse["checks"]["expected_chunk_count"]
    actual_count = rag.vs.count()
    if actual_count != expected_count:
        raise ValueError(f"Reused Chroma count {actual_count} differs from metadata count {expected_count}.")
    pages = load_pdfs_from_dir(str(Path(args.data).resolve()))
    chunks = chunk_pages(pages, method="recursive", chunk_size=args.chunk_size, overlap=50)
    expected = {chunk["chunk_id"]: chunk for chunk in chunks}
    if len(chunks) != expected_count or len(expected) != expected_count:
        raise ValueError("Re-extracted chunks/unique IDs differ from the reused index; build a new index.")
    seen = set()
    for offset in range(0, actual_count, 500):
        stored = rag.vs.collection.get(limit=500, offset=offset, include=["documents", "metadatas"])
        ids, documents, metadatas = stored.get("ids", []), stored.get("documents", []), stored.get("metadatas", [])
        if not isinstance(ids, list) or not isinstance(documents, list) or not isinstance(metadatas, list) or not len(ids) == len(documents) == len(metadatas):
            raise ValueError("Reused Chroma returned incomplete documents/metadata.")
        for identifier, text, item in zip(ids, documents, metadatas):
            chunk = expected.get(identifier)
            if identifier in seen or chunk is None or not isinstance(item, dict):
                raise ValueError("Reused Chroma has duplicate/unexpected chunk IDs or invalid metadata.")
            if text != chunk["text"] or item.get("source") != chunk["source"] or item.get("page") != chunk["page"]:
                raise ValueError(f"Reused chunk {identifier} text/source/page differs from re-extracted PDF content.")
            seen.add(identifier)
    if seen != set(expected):
        raise ValueError("Reused Chroma does not contain every expected chunk ID.")
    rag.chunks = chunks
    rag.bm25 = BM25Retriever(chunks)
    rag.hybrid = HybridRetriever(chunks, rag.vs, rag.bm25, rag.rr)
    metadata["index_reused"] = True
    metadata["reused_index_from"] = str(reuse["origin"])
    metadata["reuse_index_checks"] = {**reuse["checks"], "chroma_count": actual_count, "reextracted_count": len(chunks), "stored_ids_text_source_page": "all matched"}
    metadata["index_assembly_s"] = time.perf_counter() - started
    metadata["original_build_index_s"] = reuse["previous"].get("original_build_index_s", reuse["previous"].get("build_index_s"))
    metadata["build_index_s"] = 0.0
    metadata["index_timing_note"] = "Existing embeddings reused; build_index_s=0 is not a new-build benchmark. index_assembly_s measures PDF/chunk verification and in-memory BM25/Hybrid assembly."
    print(f"[reuse] Verified and reused {actual_count} persisted chunks; no vectorization or collection rebuild.")


def prepare_backend(args, out, metadata):
    # These are process-local runtime adapters; no core source or existing KB is edited.
    sys.path.insert(0, str(ROOT))
    from src import config
    reuse = validate_reuse_index(args, metadata, config.EMBEDDING_MODEL) if getattr(args, "reuse_index", None) else None
    from src.retrieval.vector_store import VectorStore
    from src.retrieval.reranker import Reranker
    from src.generation.rag_pipeline import RAGPipeline
    import src.generation as generation

    legacy = []
    for name in ("generation/__init__.py", "generation/rag_pipeline.py", "retrieval/vector_store.py", "retrieval/reranker.py"):
        if "/root/autodl-tmp" in (ROOT / "src" / name).read_text(encoding="utf-8"):
            legacy.append(name)
    if legacy:
        print("[runtime] Legacy Linux defaults detected. Explicit src.config models/data and isolated output index are used in this evaluation process.")
        print("[runtime] Normal app entry still needs its own local path adapter; this helper does not rewrite source.")
    vector_dir = reuse["vector_dir"] if reuse else out / "vector_store"
    metadata["runtime"] = {
        "embedding_model": config.EMBEDDING_MODEL, "reranker_model": config.RERANKER_MODEL,
        "device": config.MODEL_DEVICE, "ollama_host": config.OLLAMA_HOST,
        "ollama_model": config.OLLAMA_MODEL, "legacy_defaults_detected": legacy,
        "llm_options": config.llm_options() if callable(getattr(config, "llm_options", None)) else {"temperature": 0.1},
        "llm_timeout_s": getattr(config, "LLM_TIMEOUT", 120),
        "data_dir": str(Path(args.data).resolve()), "vector_dir": str(vector_dir),
    }
    write_metadata(out / "metadata.json", metadata)
    # rag_pipeline uses ollama.chat (SDK reads OLLAMA_HOST), Agent uses urllib constants.
    os.environ["OLLAMA_HOST"] = config.OLLAMA_HOST
    t0 = time.perf_counter()
    if reuse:
        vs = open_existing_vector_store(VectorStore, config.EMBEDDING_MODEL, vector_dir, config.MODEL_DEVICE)
    else:
        vs = VectorStore(model_path=config.EMBEDDING_MODEL, persist_dir=str(vector_dir), device=config.MODEL_DEVICE)
    reranker = Reranker(model_path=config.RERANKER_MODEL, device=config.MODEL_DEVICE)
    rag = RAGPipeline(model_name=config.OLLAMA_MODEL, vector_store=vs, reranker=reranker)
    generation._rag_instance = rag
    generation._DEFAULT_DATA_DIR = str(Path(args.data).resolve())
    metadata["model_load_s"] = time.perf_counter() - t0
    if reuse:
        assemble_reused_index(args, rag, reuse, metadata)
        metadata["notes"].append("Persisted embeddings are reused from the validated original run; original metadata/results are preserved.")
    else:
        t0 = time.perf_counter()
        rag.build_index(str(Path(args.data).resolve()), chunk_size=args.chunk_size, overlap=50)
        metadata["build_index_s"] = time.perf_counter() - t0
        metadata["index_reused"] = False
    metadata["chunk_count"] = len(rag.chunks or [])
    metadata["indexed_sources"] = sorted({chunk["source"] for chunk in rag.chunks or []})
    missing_sources = sorted({p.name for p in pdf_files(args.data)} - set(metadata["indexed_sources"]))
    if missing_sources:
        raise ValueError(f"PDFs without extracted text/chunks: {missing_sources}. Use text PDFs or perform OCR before evaluation.")
    if metadata["chunk_count"] < 20:
        raise ValueError("Need at least 20 extractable chunks for fixed recall_k=20. Check PDF text extraction.")
    agent_chat = None
    if args.mode == "agent":
        import src.agent.tools as agent_tools
        import src.agent.llm_client as llm_client
        import src.agent.react_loop as react_loop
        from src.agent.agent import agent_chat
        agent_tools._initialized = True  # already built once with the requested chunk size
        llm_client.OLLAMA_URL = config.OLLAMA_HOST + "/api/chat"
        llm_client.OLLAMA_MODEL = config.OLLAMA_MODEL
        react_loop.OLLAMA_URL = config.OLLAMA_HOST + "/api/chat"
        react_loop.OLLAMA_MODEL = config.OLLAMA_MODEL
    return rag, agent_chat


class MissingTokenCapture(contextlib.AbstractContextManager):
    """Absent instrumentation is missing data, never a synthetic zero."""
    def __exit__(self, exc_type, exc_value, tb):
        return False

    def summary(self):
        return {"total_tokens": None, "prompt_tokens": None, "completion_tokens": None, "calls": None, "measured_calls": 0, "complete": False}


def run_one(args, rag, agent_chat, item, method, run_id, capture_class):
    row = {
        "run_id": run_id, "id": item["id"], "category": item["category"],
        "mode": args.mode, "method": method, "chunk_size": args.chunk_size,
        "question": item["question"], "reference_answer": item["reference_answer"],
        "gold_evidence": item.get("gold_evidence", []), "accepted_tool_sets": item.get("accepted_tool_sets", []),
        "smoke": args.smoke, "tools_used": [], "steps": None,
    }
    start = time.perf_counter()
    capture = capture_class()
    try:
        with capture:
            if args.mode == "retrieval":
                if method == "vector":
                    contexts = rag.hybrid.search_vector(item["question"], top_k=20)[:5]
                elif method == "hybrid":
                    contexts = rag.hybrid.search_hybrid(item["question"], top_k=20)[:5]
                else:
                    contexts = rag.hybrid.search_hybrid_rerank(item["question"], top_k=5, recall_k=20)
                result = {"answer": "", "sources": contexts, "success": True}
            elif args.mode == "rag":
                result = rag.rag_answer(item["question"], top_k=5, temperature=0.1)
            else:
                result = agent_chat(item["question"], verbose=args.verbose, session_id=f"eval_{run_id}_{item['id']}_{uuid.uuid4().hex[:6]}", use_memory=False)
        success = result.get("success", True) is not False
        row.update({
            "success": success, "answer": result.get("answer", ""),
            "sources": result.get("sources", []), "tools_used": result.get("tools_used", []),
            "steps": result.get("steps"), "route": result.get("route"),
            "execution_mode": result.get("execution_mode", args.mode),
            "tools_observed": isinstance(result.get("tools_used"), list),
            "raw_result": result,
        })
    except Exception as exc:
        row.update({"success": False, "answer": "", "sources": [], "execution_mode": "error", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()})
    row["wall_latency_s"] = round(time.perf_counter() - start, 6)
    row["token_usage"] = capture.summary() if args.mode != "retrieval" else {
        "total_tokens": None, "prompt_tokens": None, "completion_tokens": None,
        "calls": 0, "measured_calls": 0, "complete": False, "not_applicable": True,
    }
    usage = row["token_usage"]
    measured_failed_task = usage.get("complete") and isinstance(usage.get("calls"), int) and usage["calls"] > 0
    if not row["success"] and args.mode != "retrieval" and not measured_failed_task:
        row["token_usage"].update(complete=False, total_tokens=None, prompt_tokens=None, completion_tokens=None)
        row["token_usage"]["application_failure"] = True
    if args.mode == "agent":
        # Agent sources may merge citations from several tools; this is not a ranked top-5 retrieval list.
        row.update(hit_at_5=None, mrr_at_5=None, recall_at_5=None)
    else:
        row.update(retrieval_metrics(row["gold_evidence"], row["sources"], row["success"]))
    row["auto_tool_match"] = tools_match(row["accepted_tool_sets"], row["tools_used"]) if args.mode == "agent" and row.get("tools_observed") else None
    return row


def mean_present(values):
    valid = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return round(statistics.mean(valid), 6) if valid else "N/A"


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)] if ordered else "N/A"


def review_key(row):
    return (str(row.get("run_id")), str(row.get("id")), str(row.get("mode")), str(row.get("method")), str(row.get("chunk_size")))


def load_reviews(paths):
    reviews = {}
    for path in paths:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                scores = {}
                for field in ("correctness", "completeness", "citation_accuracy", "routing"):
                    value = row.get(field, "").strip()
                    if value:
                        allowed = {0, 1} if field == "routing" else {0, 1, 2}
                        try:
                            score = int(value)
                        except ValueError as exc:
                            raise ValueError(f"{path}, id={row.get('id')}: {field} must be an integer.") from exc
                        if score not in allowed:
                            raise ValueError(f"{path}, id={row.get('id')}: {field} must be {sorted(allowed)}.")
                        scores[field] = score
                reviews[review_key(row)] = scores
    return reviews


def summarize_rows(rows, reviews=None):
    reviews = reviews or {}
    grouped = defaultdict(list)
    for row in rows:
        for category in ("all", row["category"]):
            for execution_mode in ("all", row.get("execution_mode", "unknown")):
                group = (row["mode"], row["chunk_size"], row["method"], category, execution_mode)
                grouped[group].append(row)
    summary = []
    for group, values in sorted(grouped.items(), key=lambda pair: tuple(str(v) for v in pair[0])):
        mode, chunk, method, category, execution_mode = group
        latencies = [row["wall_latency_s"] for row in values]
        metrics = {name: mean_present([row.get(name) for row in values]) for name in ("hit_at_5", "mrr_at_5", "recall_at_5")}
        tokens = [row.get("token_usage", {}) for row in values]
        complete = [entry["total_tokens"] for entry in tokens if entry.get("complete") and isinstance(entry.get("total_tokens"), (int, float))]
        manually_scored = [reviews.get(review_key(row), {}) for row in values]
        tool_scored = sum(row.get("auto_tool_match") is not None for row in values)
        tool_expected = sum(bool(row.get("accepted_tool_sets")) for row in values) if mode == "agent" else 0
        record = {
            "mode": mode, "chunk_size": chunk, "method": method,
            "category": category, "execution_mode": execution_mode, "n": len(values),
            "failures": sum(row.get("success") is False for row in values), **metrics,
            "retrieval_gold_n": sum(row.get("hit_at_5") is not None for row in values),
            "avg_wall_latency_s": mean_present(latencies), "p95_wall_latency_s": percentile(latencies, .95),
            "avg_steps": mean_present([row.get("steps") for row in values]),
            "tool_match_rate": mean_present([row.get("auto_tool_match") for row in values]),
            "tool_gold_n": tool_scored, "tool_expected_n": tool_expected,
            "tool_coverage": round(tool_scored / tool_expected, 6) if tool_expected else "N/A",
            "avg_tokens": mean_present(complete), "token_coverage": round(len(complete) / len(values), 6),
            "manual_n": sum(bool(scores) for scores in manually_scored),
        }
        for field in ("correctness", "completeness", "citation_accuracy", "routing"):
            record[field] = mean_present([scores.get(field) for scores in manually_scored])
            record[field + "_n"] = sum(field in scores for scores in manually_scored)
        summary.append(record)
    return summary


def save_summaries(out, rows, reviews, metadata=None):
    summary = summarize_rows(rows, reviews)
    payload = {
        "generated_at": now(), "result_rows": len(rows), "smoke_rows": sum(bool(row.get("smoke")) for row in rows),
        "definitions": {
            "retrieval": "Retrieval/RAG only: Hit@5/MRR@5/Recall@5 match gold PDF filename + physical page; failed cases score zero; no-gold cases excluded. Agent merged citations are not a ranked retrieval list and do not get these metrics.",
            "tool_match_rate": "Pre-annotated complete allowed tool-set match; execution success is separate. Unannotated or unobserved tool lists are excluded; tool_coverage reports observed/scorable cases over pre-annotated cases. Not answer correctness.",
            "manual_scores": "0/1/2 averages; routing 0/1; blanks excluded; per-field denominators are in this JSON.",
            "avg_steps": "Backend execution steps. Use execution_mode=react to discuss ReAct steps.",
            "tokens": "Only complete real per-question LLM token counters; N/A is missing, never zero. token_coverage is complete cases / all cases.",
        },
        "groups": summary,
    }
    if metadata:
        payload["run_id"] = metadata["run_id"]
    write_json(out / "summary.json", payload)
    write_csv(out / "summary.csv", summary, SUMMARY_FIELDS)
    return summary


def prepare_resume(args, qa, metadata):
    """Keep original files intact and reject mixed experiments before model loading."""
    if not getattr(args, "resume", None):
        return [], {}
    if args.smoke or args.limit is not None:
        raise ValueError("Resume is for interrupted formal runs; do not combine it with --smoke/--limit.")
    origin = Path(args.resume).expanduser().resolve()
    meta_path, result_path = origin / "metadata.json", origin / "results.jsonl"
    previous, selected_metadata_path = read_metadata_record(meta_path)
    for field in ("qa_sha256", "corpus_sha256", "parameters", "packages", "python", "platform", "processor"):
        if previous.get(field) != metadata.get(field):
            raise ValueError(f"Resume configuration differs: {field}. Start a new experiment instead.")
    normalize = lambda hashes: {name.replace("\\", "/"): value for name, value in hashes.items()}
    if normalize(previous.get("backend_sha256", {})) != normalize(metadata["backend_sha256"]):
        raise ValueError("Resume requires unchanged backend source files.")
    if previous.get("smoke") is not False:
        raise ValueError("Smoke results cannot be resumed as a formal experiment.")
    if digest(origin / "qa_snapshot.jsonl") != metadata["qa_sha256"]:
        raise ValueError("Resume QA snapshot does not match the current question set.")
    sys.path.insert(0, str(ROOT))
    from src import config
    expected_runtime = {
        "embedding_model": config.EMBEDDING_MODEL, "reranker_model": config.RERANKER_MODEL,
        "device": config.MODEL_DEVICE, "ollama_host": config.OLLAMA_HOST,
        "ollama_model": config.OLLAMA_MODEL, "llm_options": config.llm_options(),
        "llm_timeout_s": config.LLM_TIMEOUT,
    }
    for field, value in expected_runtime.items():
        if previous.get("runtime", {}).get(field) != value:
            raise ValueError(f"Resume runtime differs: {field}. Keep the original model/settings.")
    methods = METHODS if args.mode == "retrieval" else ("hybrid_rerank",)
    order = {(item["id"], method): number for number, (item, method) in
             enumerate((item, method) for item in qa for method in methods)}
    by_id = {item["id"]: item for item in qa}
    saved = read_jsonl(result_path)
    if not saved or len(saved) >= len(order):
        raise ValueError("Resume requires a nonempty, incomplete results file.")
    if [(row.get("id"), row.get("method")) for row in saved] != list(order)[:len(saved)]:
        raise ValueError("Resume saved rows must be a continuous question/method prefix, with no gaps or duplicates.")
    if previous.get("token_script_sha256") and previous["token_script_sha256"] != metadata["token_script_sha256"]:
        raise ValueError("Resume Token instrumentation differs; start a new experiment.")
    reviews = {}
    review_path = origin / "review.csv"
    if review_path.exists():
        load_reviews([review_path])  # Validate scores before carrying manual work.
        with review_path.open(encoding="utf-8-sig", newline="") as handle:
            reviews = {review_key(row): row for row in csv.DictReader(handle)}
    carried, carried_reviews, seen = [], {}, set()
    for row in saved:
        pair = (row.get("id"), row.get("method"))
        if pair not in order or pair in seen:
            raise ValueError(f"Resume has an unknown or duplicate question/method: {pair}")
        seen.add(pair)
        if (row.get("run_id") != previous.get("run_id") or row.get("mode") != args.mode
                or row.get("chunk_size") != args.chunk_size or row.get("smoke") is not False):
            raise ValueError(f"Resume result configuration does not match metadata: {pair}")
        item = by_id[row["id"]]
        for field in ("question", "reference_answer", "category"):
            if row.get(field) != item.get(field):
                raise ValueError(f"Resume question content differs: {pair}, {field}")
        for field in ("gold_evidence", "accepted_tool_sets"):
            if row.get(field, []) != item.get(field, []):
                raise ValueError(f"Resume annotation differs: {pair}, {field}")
        if (not isinstance(row.get("success"), bool) or not isinstance(row.get("wall_latency_s"), (int, float))
                or not isinstance(row.get("token_usage"), dict)):
            raise ValueError(f"Resume result is missing required measurements: {pair}")
        old_key = review_key(row)
        copied = dict(row)
        copied["origin_run_id"] = row.get("origin_run_id", row["run_id"])
        copied["run_id"] = metadata["run_id"]
        carried.append(copied)
        if old_key in reviews:
            carried_reviews[review_key(copied)] = {field: reviews[old_key].get(field, "") for field in
                ("correctness", "completeness", "citation_accuracy", "routing", "bad_case", "note")}
    carried.sort(key=lambda row: order[(row["id"], row["method"])])
    if not getattr(args, "reuse_index", None):
        vector_dir = previous.get("runtime", {}).get("vector_dir")
        if not vector_dir:
            raise ValueError("Resume needs the original vector index; specify --reuse-index.")
        args.reuse_index = str(Path(vector_dir).parent)
    metadata["resume"] = {
        "from": str(origin), "previous_run_id": previous["run_id"],
        "source_metadata_path": str(selected_metadata_path),
        "source_metadata_sha256": digest(selected_metadata_path), "source_results_sha256": digest(result_path),
        "carried_rows": len(carried), "remaining_rows": len(order) - len(carried),
        "carried_ids": [row["id"] for row in carried],
        "previous_preflight": previous.get("preflight", {}),
        "previous_script_sha256": previous.get("script_sha256"),
        "token_instrumentation_hash_verified": bool(previous.get("token_script_sha256")),
        "scope": "Saved rows (including recorded failures) retain original answers/timings/Tokens; origin_run_id records provenance. Only missing rows execute. This is an interrupted/resumed experiment.",
        "limitations": "Older runs may lack Token-instrumentation hashes and model snapshot revisions; those historical values cannot be retrospectively verified. New segment loading/warmup/started_at/finished_at do not measure the complete multi-segment experiment duration.",
    }
    metadata["notes"].append("Interrupted experiment resumed in a new directory; earlier measured rows are carried with provenance, not rerun or counted twice.")
    print(f"[resume] Preserving {len(carried)} saved rows; running {len(order) - len(carried)} missing rows.", flush=True)
    return carried, carried_reviews


def command_run(args):
    if args.limit is not None and not args.smoke:
        raise ValueError("--limit is only allowed with --smoke; formal experiments must run the full QA set.")
    qa, report = validate_qa(args.qa, args.data, args.smoke)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["valid"]:
        return 2
    if args.limit is not None:
        qa = qa[:args.limit]
    if Path(args.out).expanduser().resolve().exists():
        raise ValueError(f"Output already exists; choose a new --out to preserve results: {args.out}")
    metadata = make_metadata(args, pdf_files(args.data))
    carried, carried_reviews = prepare_resume(args, qa, metadata)
    preflight = preflight_ollama(args.mode)
    if carried and args.mode != "retrieval":
        previous_probe = metadata["resume"]["previous_preflight"]
        if (not previous_probe.get("model_digest") or not preflight.get("model_digest")
                or (preflight.get("model"), preflight.get("model_digest")) != (previous_probe.get("model"), previous_probe.get("model_digest"))):
            raise ValueError("Resume requires the same installed Ollama model and digest; start a new experiment for a changed model.")
    out = fresh_directory(args.out)
    shutil.copyfile(args.qa, out / "qa_snapshot.jsonl")
    metadata["validation"] = report
    metadata["preflight"] = preflight
    metadata["status"] = "initializing"
    metadata["result_rows"] = len(carried)
    write_metadata(out / "metadata.json", metadata)
    # Persist carried results before any native model code runs. The source is untouched.
    with (out / "results.jsonl").open("w", encoding="utf-8") as handle:
        for row in carried:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    initial_reviews = []
    for row in carried:
        record = review_row(row)
        record.update(carried_reviews.get(review_key(row), {}))
        initial_reviews.append(record)
    write_csv(out / "review.csv", initial_reviews, REVIEW_FIELDS)
    try:
        rag, agent_chat = prepare_backend(args, out, metadata)
        try:
            from module5_tokens import TokenCapture
            capture_class = TokenCapture
            metadata["token_instrumentation"] = "module5_tokens.TokenCapture"
        except ImportError:
            capture_class = MissingTokenCapture
            metadata["token_instrumentation"] = "unavailable; Token N/A"
        t0 = time.perf_counter()
        if not args.no_warmup:
            rag.retrieve(qa[0]["question"], top_k=5)
            if args.mode == "rag":
                warmup_result = rag.rag_answer(qa[0]["question"], top_k=5, temperature=0.1)
            elif args.mode == "agent":
                warmup_result = agent_chat(qa[0]["question"], verbose=False, session_id=f"warmup_{uuid.uuid4().hex}", use_memory=False)
            if args.mode in ("rag", "agent"):
                metadata["warmup_result"] = {
                    "success": warmup_result.get("success", True),
                    "execution_mode": warmup_result.get("execution_mode", args.mode),
                    "error": str(warmup_result.get("error", warmup_result.get("answer", "")))[:1000] if warmup_result.get("success") is False else None,
                }
                if infrastructure_warmup_failure(warmup_result, preflight.get("model")):
                    metadata["warmup_s"] = time.perf_counter() - t0
                    metadata["warmup_enabled"] = True
                    raise RuntimeError(f"Ollama model/connection failure during warmup; evaluation stopped before formal questions: {metadata['warmup_result']['error']}")
        metadata["warmup_s"] = time.perf_counter() - t0
        metadata["warmup_enabled"] = not args.no_warmup
        write_metadata(out / "metadata.json", metadata)
        rows = list(carried)
        methods = METHODS if args.mode == "retrieval" else ("hybrid_rerank",)
        completed = {(row["id"], row["method"]) for row in rows}
        with (out / "results.jsonl").open("a", encoding="utf-8") as handle:
            for number, item in enumerate(qa, 1):
                for method in methods:
                    if (item["id"], method) in completed:
                        continue
                    metadata.update(status="running", active_question=item["id"], active_method=method, result_rows=len(rows))
                    write_metadata(out / "metadata.json", metadata)
                    print(f"[start {number}/{len(qa)}] {item['id']} {method}", flush=True)
                    row = run_one(args, rag, agent_chat, item, method, metadata["run_id"], capture_class)
                    rows.append(row)
                    handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                    metadata.update(result_rows=len(rows), last_completed_question=item["id"], active_question=None, active_method=None)
                    write_metadata(out / "metadata.json", metadata)
                    print(f"[{number}/{len(qa)}] {item['id']} {method}: success={row['success']} latency={row['wall_latency_s']:.3f}s hit@5={row['hit_at_5']}", flush=True)
        review_rows = []
        for row in rows:
            record = review_row(row)
            record.update(carried_reviews.get(review_key(row), {}))
            review_rows.append(record)
        write_csv(out / "review.csv", review_rows, REVIEW_FIELDS)
        per_fields = REVIEW_FIELDS[:18] + ("hit_at_5", "mrr_at_5", "recall_at_5", "total_tokens", "token_complete", "error")
        per_rows = []
        for row in rows:
            record = review_row(row)
            record.update({name: csv_value(row[name]) for name in ("hit_at_5", "mrr_at_5", "recall_at_5")})
            record.update(total_tokens=csv_value(row["token_usage"].get("total_tokens")), token_complete=row["token_usage"].get("complete"), error=row.get("error", ""))
            per_rows.append(record)
        write_csv(out / "per_question.csv", per_rows, per_fields)
        save_summaries(out, rows, load_reviews([out / "review.csv"]))
        metadata["finished_at"] = now()
        metadata["result_rows"] = len(rows)
        metadata["failed_rows"] = sum(row["success"] is False for row in rows)
        metadata["status"] = "completed_with_failures" if metadata["failed_rows"] else "completed"
        write_metadata(out / "metadata.json", metadata)
        print(f"Saved: {out}\nHuman scoring remains blank in review.csv. Edit it, then run summarize.")
        return 1 if metadata["failed_rows"] else 0
    except BaseException as exc:
        metadata["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "aborted"
        metadata["error"] = f"{type(exc).__name__}: {exc}"
        metadata["finished_at"] = now()
        try:
            write_metadata(out / "metadata.json", metadata)
        except Exception as checkpoint_error:
            print(f"[checkpoint error] Could not persist abort metadata: {checkpoint_error}. Original error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise


def command_summarize(args):
    root = Path(args.results).resolve()
    if root.is_file():
        paths = [root]
    else:
        paths = sorted(root.rglob("results.jsonl"))
    if not paths:
        raise ValueError("No results.jsonl found.")
    rows, review_paths = [], []
    seen = set()
    for path in paths:
        batch = read_jsonl(path)
        if any(row.get("smoke") for row in batch) and not args.include_smoke:
            print(f"Skipping smoke results: {path}")
            continue
        for row in batch:
            marker = review_key(row)
            if marker in seen:
                raise ValueError(f"Duplicate result key: {marker}; copied or repeated runs need separate aggregation.")
            seen.add(marker)
            rows.append(row)
        review = path.parent / "review.csv"
        if review.exists():
            review_paths.append(review)
    if not rows:
        raise ValueError("No formal results found. For debugging smoke summaries, add --include-smoke.")
    # Do not silently compare different corpora/question sets/backends as one experiment.
    fingerprints = set()
    for path in paths:
        metadata_path = path.parent / "metadata.json"
        if metadata_path.exists() or any(metadata_path.parent.glob(".metadata.json.*.tmp")):
            meta = read_metadata(metadata_path)
            if meta.get("smoke") and not args.include_smoke:
                continue
            fingerprints.add((meta.get("corpus_sha256"), meta.get("qa_sha256")))
    if len(fingerprints) > 1:
        raise ValueError("Results contain different corpus/QA hashes; summarize each controlled experiment separately.")
    configuration_runs = defaultdict(set)
    for row in rows:
        configuration_runs[(row["mode"], row["chunk_size"], row["method"])].add(row["run_id"])
    repeated = [configuration for configuration, run_ids in configuration_runs.items() if len(run_ids) > 1]
    if repeated:
        raise ValueError(f"Multiple runs for the same configuration: {repeated}. Summarize baseline and optimized directories separately.")
    out = fresh_directory(args.out)
    reviews = load_reviews(review_paths)
    save_summaries(out, rows, reviews)
    write_csv(out / "all_results.csv", [review_row(row) for row in rows], REVIEW_FIELDS)
    write_json(out / "inputs.json", {"results": [str(p) for p in paths], "reviews": [str(p) for p in review_paths], "include_smoke": args.include_smoke})
    print(f"Summary: {out / 'summary.csv'}\nUse category=all and execution_mode=all for overall comparisons.")
    return 0


def parser():
    main = argparse.ArgumentParser(description=__doc__)
    commands = main.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create 55 blank QA rows and manual scoring rules.")
    init.add_argument("--out", required=True)
    init.set_defaults(func=command_init)
    check = commands.add_parser("check", help="Validate manually annotated QA; no backend imports.")
    check.add_argument("--qa", required=True)
    check.add_argument("--data", default=str(ROOT / "data"))
    check.add_argument("--smoke", action="store_true")
    check.set_defaults(func=command_check)
    run = commands.add_parser("run", help="Run real backend evaluation in a new isolated output index.")
    run.add_argument("--qa", required=True)
    run.add_argument("--data", default=str(ROOT / "data"))
    run.add_argument("--out", required=True)
    run.add_argument("--mode", choices=("retrieval", "rag", "agent"), required=True)
    run.add_argument("--chunk-size", type=int, choices=(256, 512, 1024), default=512)
    run.add_argument("--reuse-index", help="Reuse a validated original run's vector_store; recheck chunks and assemble BM25 without embedding rebuild.")
    run.add_argument("--resume", help="Carry verified saved rows from an interrupted run into this new output; execute missing rows only.")
    run.add_argument("--smoke", action="store_true")
    run.add_argument("--limit", type=int)
    run.add_argument("--no-warmup", action="store_true")
    run.add_argument("--verbose", action="store_true")
    run.set_defaults(func=command_run)
    summary = commands.add_parser("summarize", help="Aggregate real results and any completed manual review.")
    summary.add_argument("--results", required=True)
    summary.add_argument("--out", required=True)
    summary.add_argument("--include-smoke", action="store_true")
    summary.set_defaults(func=command_summarize)
    return main


def main():
    args = parser().parse_args()
    if getattr(args, "limit", None) is not None and args.limit < 1:
        parser().error("--limit must be positive")
    try:
        return args.func(args) or 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
