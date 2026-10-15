"""Run the prepared 55-question set from any working directory."""
import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from module5_eval import read_metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("agent", "rag", "retrieval"), default="agent")
    parser.add_argument("--chunk-size", type=int, choices=(256, 512, 1024), default=512)
    parser.add_argument("--check-only", action="store_true", help="Validate the set without loading models")
    parser.add_argument("--smoke", action="store_true", help="Run a small trial; never count it as formal results")
    parser.add_argument("--limit", type=int, help="Number of trial questions; only valid with --smoke")
    parser.add_argument("--reuse-index", help="An existing run directory, or 'latest', to reuse its verified index")
    parser.add_argument("--resume", help="Interrupted run directory, or 'latest'; keep saved rows and execute missing questions")
    parser.add_argument("--llm-model", help="Explicit Ollama model; recorded as a new model configuration")
    parser.add_argument("--llm-device", choices=("auto", "cpu"), help="cpu sends num_gpu=0 on every LLM request")
    parser.add_argument("--context-size", type=int, help="LLM context tokens; applies to probe and real requests")
    args = parser.parse_args()
    if args.limit is not None and (not args.smoke or args.limit < 1 or args.limit > 55):
        parser.error("--limit requires --smoke and must be between 1 and 55")
    if args.check_only and (args.smoke or args.limit is not None):
        parser.error("--check-only cannot be combined with --smoke or --limit")
    if args.resume and (args.check_only or args.smoke):
        parser.error("--resume cannot be combined with --check-only or --smoke")
    if args.context_size is not None and args.context_size < 1024:
        parser.error("--context-size must be at least 1024")
    root = Path(__file__).resolve().parents[1]
    qa = root / "evaluation" / "qa.jsonl"
    corpus = root / "evaluation" / "corpus"
    if not qa.is_file():
        parser.error("The prepared evaluation/qa.jsonl file is missing.")
    with qa.open(encoding="utf-8-sig") as handle:
        questions = [json.loads(line) for line in handle if line.strip()]
    if len(questions) != 55:
        parser.error(f"Expected the prepared 55-question set; found {len(questions)} rows.")
    command = [sys.executable, "-u", "-X", "faulthandler", str(root / "scripts" / "module5_eval.py")]
    child_env = dict(os.environ)
    child_env["PYTHONIOENCODING"] = "utf-8"
    if args.resume:
        if args.resume == "latest":
            candidates = []
            for run_dir in (root / "evaluation" / "runs").glob("*"):
                if not run_dir.is_dir():
                    continue
                meta_path = run_dir / "metadata.json"
                result_path = meta_path.parent / "results.jsonl"
                try:
                    meta = read_metadata(meta_path)
                    with result_path.open(encoding="utf-8-sig") as handle:
                        row_count = sum(bool(line.strip()) for line in handle)
                except (ValueError, OSError):
                    continue
                expected = 55 * (3 if args.mode == "retrieval" else 1)
                if (not meta.get("smoke") and 0 < row_count < expected
                        and meta.get("parameters", {}).get("mode") == args.mode
                        and meta.get("parameters", {}).get("chunk_size") == args.chunk_size):
                    candidates.append((meta.get("started_at", ""), meta_path.parent))
            if not candidates:
                parser.error("No incomplete formal run found for this configuration")
            resume = max(candidates, key=lambda item: item[0])[1]
        else:
            resume = Path(args.resume).expanduser().resolve()
        previous = read_metadata(resume / "metadata.json")
        runtime = previous.get("runtime", {})
        for field, variable in (("embedding_model", "RAG_EMBEDDING_MODEL"), ("reranker_model", "RAG_RERANKER_MODEL"),
                                ("device", "RAG_MODEL_DEVICE"), ("ollama_host", "OLLAMA_HOST"),
                                ("ollama_model", "RAG_LLM_MODEL"), ("llm_timeout_s", "RAG_LLM_TIMEOUT")):
            if field in runtime:
                child_env[variable] = str(runtime[field])
        for field, variable in (("num_ctx", "RAG_LLM_NUM_CTX"), ("num_gpu", "RAG_LLM_NUM_GPU")):
            if field in runtime.get("llm_options", {}):
                child_env[variable] = str(runtime["llm_options"][field])
            else:
                child_env.pop(variable, None)
        print("Resume source (original files preserved):", resume, flush=True)
    # An index build can outlast Ollama's default 5-minute model residency.
    # Keep the benchmark model loaded across initialization and serial requests.
    child_env.setdefault("RAG_LLM_KEEP_ALIVE", "30m")
    if args.llm_model:
        child_env["RAG_LLM_MODEL"] = args.llm_model
    if args.llm_device == "cpu":
        child_env["RAG_LLM_NUM_GPU"] = "0"
        child_env.setdefault("RAG_LLM_TIMEOUT", "600")
    elif args.llm_device == "auto":
        child_env.pop("RAG_LLM_NUM_GPU", None)
    if args.context_size is not None:
        child_env["RAG_LLM_NUM_CTX"] = str(args.context_size)
    if args.check_only:
        command += ["check", "--qa", str(qa), "--data", str(corpus)]
    else:
        stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
        limit = args.limit if args.limit is not None else 3
        run_label = f"{args.mode}55_smoke{limit}" if args.smoke else f"{args.mode}55"
        output = root / "evaluation" / "runs" / f"{run_label}_{stamp}_{uuid.uuid4().hex[:6]}"
        command += ["run", "--qa", str(qa), "--data", str(corpus),
                    "--mode", args.mode, "--chunk-size", str(args.chunk_size), "--out", str(output)]
        if args.smoke:
            command += ["--smoke", "--limit", str(limit)]
        if args.resume:
            command += ["--resume", str(resume)]
        if args.reuse_index:
            if args.reuse_index == "latest":
                candidates = []
                for run_dir in (root / "evaluation" / "runs").glob("*"):
                    if not run_dir.is_dir():
                        continue
                    meta_path = run_dir / "metadata.json"
                    try:
                        meta = read_metadata(meta_path)
                    except (ValueError, OSError):
                        continue
                    if (meta.get("chunk_count", 0) > 0
                            and meta.get("parameters", {}).get("chunk_size") == args.chunk_size
                            and (meta_path.parent / "vector_store" / "chroma.sqlite3").is_file()):
                        candidates.append((meta.get("started_at", ""), meta_path.parent))
                if not candidates:
                    parser.error("No existing index candidate found for this chunk size")
                reuse = max(candidates, key=lambda item: item[0])[1]
            else:
                reuse = Path(args.reuse_index).expanduser().resolve()
            print("Index candidate (will be verified):", reuse, flush=True)
            command += ["--reuse-index", str(reuse)]
        print("Output:", output, flush=True)
    if args.check_only:
        return subprocess.call(command, cwd=root, env=child_env)
    log_dir = root / "evaluation" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{output.name}.log"
    print("Terminal/crash log:", log_path, flush=True)
    with log_path.open("x", encoding="utf-8") as log:
        with subprocess.Popen(command, cwd=root, env=child_env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace") as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            code = process.wait()
        log.write(f"\n[runner] child_exit_code={code}; hex=0x{code & 0xffffffff:08X}\n")
    if code not in (0, 1, 2):
        print(f"Evaluation process exited unexpectedly: {code} (0x{code & 0xffffffff:08X}).", flush=True)
        print("Saved results remain in:", output, "\nCrash log:", log_path, flush=True)
        print("Use --resume with that output directory to execute only missing rows.", flush=True)
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())
