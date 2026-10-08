import json

import re
import time


from typing import Any, Dict, List, Tuple

from src.agent.llm_client import chat
from src.generation import retrieve
from src.agent.paper_scope import (
    resolve_paper_source,
    retrieve_from_paper,
)

# ============================================================
# Basic Utils
# ============================================================




def _extract_json_object(
    text: str,
) -> Dict[str, Any]:
    """
    从 LLM 输出中提取 JSON。
    """

    text = (
        text
        or ""
    ).strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    try:
        return json.loads(
            text
        )

    except Exception:
        pass

    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL,
    )

    if match:

        try:
            return json.loads(
                match.group(0)
            )

        except Exception:
            pass

    return {}


# ============================================================
# Compare Input Parser
# ============================================================

def parse_compare_input(
    raw_input: str,
) -> Tuple[str, str]:
    """
    支持：

    1.
    Attention Is All You Need ||| BERT

    2.
    {
        "paper_a": "...",
        "paper_b": "..."
    }

    3.
    比较《Attention Is All You Need》和《BERT》

    4.
    Compare "Paper A" and "Paper B"

    5.
    Attention Is All You Need vs BERT
    """

    text = (
        raw_input
        or ""
    ).strip()

    if not text:
        return "", ""

    # ========================================================
    # JSON
    # ========================================================

    if text.startswith("{"):

        try:

            obj = json.loads(
                text
            )

            paper_a = (
                obj.get("paper_a")
                or obj.get("paper1")
                or ""
            )

            paper_b = (
                obj.get("paper_b")
                or obj.get("paper2")
                or ""
            )

            if paper_a and paper_b:

                return (
                    str(paper_a).strip(),
                    str(paper_b).strip(),
                )

        except Exception:
            pass

    # ========================================================
    # Internal delimiter
    # ========================================================

    if "|||" in text:

        parts = [
            item.strip()
            for item
            in text.split("|||")
            if item.strip()
        ]

        if len(parts) >= 2:
            return (
                parts[0],
                parts[1],
            )

    # ========================================================
    # Chinese book-title quotes
    # ========================================================

    titles = re.findall(
        r"《([^》]+)》",
        text,
    )

    if len(titles) >= 2:

        return (
            titles[0].strip(),
            titles[1].strip(),
        )

    # ========================================================
    # English / Chinese quotation marks
    # ========================================================

    titles = re.findall(
        r'[“"]([^”"]+)[”"]',
        text,
    )

    if len(titles) >= 2:

        return (
            titles[0].strip(),
            titles[1].strip(),
        )

    # ========================================================
    # Remove common command prefix
    # ========================================================

    cleaned = re.sub(
        r"^(请|请帮我|帮我)?\s*"
        r"(比较|对比|分析比较|分析对比)\s*"
        r"(论文)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # ========================================================
    # Chinese connectors
    # ========================================================

    match = re.match(
        r"(.+?)\s*(?:和|与|以及)\s*(.+)",
        cleaned,
        flags=re.IGNORECASE,
    )

    if match:

        paper_a = (
            match.group(1)
            .strip()
        )

        paper_b = (
            match.group(2)
            .strip()
        )

        paper_b = re.sub(
            r"\s*(?:在.+?方面)?"
            r"(?:的)?"
            r"(?:区别|差异|异同|不同|比较|对比)"
            r".*$",
            "",
            paper_b,
        ).strip()

        paper_b = paper_b.strip(
            "？?。.,，"
        )

        if paper_a and paper_b:
            return paper_a, paper_b

    # ========================================================
    # English VS
    # ========================================================

    match = re.match(
        r"(.+?)\s+"
        r"(?:vs\.?|versus|with)\s+"
        r"(.+)",
        cleaned,
        flags=re.IGNORECASE,
    )

    if match:

        paper_a = (
            match.group(1)
            .strip()
        )

        paper_b = (
            match.group(2)
            .strip()
            .strip("?.")
        )

        if paper_a and paper_b:
            return paper_a, paper_b

    # ========================================================
    # Compare A and B
    # ========================================================

    match = re.search(
        r"(?:compare)\s+"
        r"(.+?)\s+"
        r"(?:and|with|vs\.?)\s+"
        r"(.+?)(?:[?.]|$)",
        text,
        flags=re.IGNORECASE,
    )

    if match:

        return (
            match.group(1).strip(),
            match.group(2).strip(),
        )

    return "", ""


# ============================================================
# Paper → Source Resolution
# ============================================================




# ============================================================
# Source-isolated Retrieval
# ============================================================

def _retrieve_paper_evidence(
    paper_name: str,
    source: str,
) -> List[Dict[str, Any]]:

    dimension_queries = {
        "method": [
            "What method, architecture, or algorithm does the paper propose?",
            "What are the main technical innovations and model components?",
        ],

        "dataset": [
            "What datasets, benchmarks, and experimental tasks are used?",
            "What training data and evaluation datasets are used?",
        ],

        "results": [
            "What are the main experimental results?",
            "What numerical results, metrics, and comparisons are reported?",
        ],
    }

    collected = {}

    for dimension, queries in (
        dimension_queries.items()
    ):

        for query in queries:

            full_query = (
                f"{paper_name}. {query}"
            )

            docs = retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=5,
                candidate_k=20,
            )

            for doc in docs[:5]:

                chunk_id = (
                    doc.get(
                        "chunk_id"
                    )
                )

                if chunk_id:

                    key = (
                        source,
                        chunk_id,
                    )

                else:

                    key = (
                        source,
                        doc.get("page"),
                        str(
                            doc.get(
                                "text",
                                "",
                            )
                        )[:100],
                    )

                if key not in collected:

                    item = dict(
                        doc
                    )

                    item[
                        "compare_dimension"
                    ] = dimension

                    collected[
                        key
                    ] = item

    docs = list(
        collected.values()
    )

    docs.sort(
        key=lambda x: float(
            x.get(
                "rerank_score",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    )

    return docs[:18]


# ============================================================
# Evidence Context
# ============================================================

def _build_context(
    paper_name: str,
    docs: List[Dict[str, Any]],
) -> str:

    parts = []

    for i, doc in enumerate(
        docs,
        1,
    ):

        parts.append(
            f"[Evidence {i}]\n"
            f"Paper: {paper_name}\n"
            f"Source: {doc.get('source', 'Unknown')}\n"
            f"Page: {doc.get('page', '?')}\n"
            f"Dimension: "
            f"{doc.get('compare_dimension', 'unknown')}\n"
            f"Content:\n"
            f"{doc.get('text', '')}"
        )

    return "\n\n".join(
        parts
    )


# ============================================================
# Fact Extraction
# ============================================================

def _extract_paper_facts(
    paper_name: str,
    docs: List[Dict[str, Any]],
) -> Dict[str, Any]:

    if not docs:

        return {
            "paper": paper_name,
            "method": (
                "检索内容中未提供足够信息"
            ),
            "datasets": [],
            "tasks": [],
            "results": [],
        }

    context = _build_context(
        paper_name,
        docs,
    )

    system_prompt = """
You are a rigorous research paper fact extractor.

You must only use the supplied evidence.

Do not use outside knowledge.

Do not invent datasets, methods, metrics, or results.

If evidence is insufficient, use an empty list or
"Insufficient evidence".

Return valid JSON only.
"""

    user_prompt = f"""
Paper:
{paper_name}

Evidence:
{context}

Extract the following information.

Return exactly this JSON structure:

{{
  "paper": "{paper_name}",
  "method": "...",
  "datasets": ["..."],
  "tasks": ["..."],
  "results": ["..."]
}}

Requirements:

1. method:
   Summarize the main technical approach.

2. datasets:
   Only datasets explicitly supported by evidence.

3. tasks:
   Main experimental tasks.

4. results:
   Important reported experimental results.
   Preserve numerical metrics when supported.

5. Do not mix facts from other papers.
"""

    raw = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
        json_mode=True,
    )

    parsed = _extract_json_object(
        raw
    )

    if not parsed:

        return {
            "paper": paper_name,
            "method": (
                "结构化事实提取失败"
            ),
            "datasets": [],
            "tasks": [],
            "results": [],
            "raw_output": raw,
        }

    parsed[
        "paper"
    ] = paper_name

    return parsed


# ============================================================
# Paper Compare
# ============================================================

def paper_compare(
    raw_input: str,
) -> Dict[str, Any]:
    """
    对两篇论文进行比较。

    输入推荐格式：

        Paper A ||| Paper B

    也支持自然语言：

        比较《Paper A》和《Paper B》
    """

    start_time = time.time()

    paper_a, paper_b = (
        parse_compare_input(
            raw_input
        )
    )

    if not paper_a or not paper_b:

        return {
            "answer": (
                "没有识别出两篇论文。"
                "请输入两篇论文名称，例如："
                "Attention Is All You Need "
                "||| BERT"
            ),
            "sources": [],
            "success": False,
        }

    if (
        paper_a.lower()
        == paper_b.lower()
    ):

        return {
            "answer": (
                "需要提供两篇不同的论文进行比较。"
            ),
            "sources": [],
            "paper_a": paper_a,
            "paper_b": paper_b,
            "success": False,
        }

    # ========================================================
    # Resolve each paper independently
    # ========================================================

    try:

        source_a = (
            resolve_paper_source(
                paper_a
            )
        )

        source_b= (
            resolve_paper_source(
                paper_b
            )
        )

    except Exception as e:

        return {
            "answer": (
                "论文来源解析失败："
                f"{type(e).__name__}: {e}"
            ),
            "sources": [],
            "paper_a": paper_a,
            "paper_b": paper_b,
            "success": False,
        }

    if source_a == source_b:

        return {
            "answer": (
                "两篇论文被解析到了同一个 PDF："
                f"{source_a}。"
                "请检查论文名称或 PDF 文件名。"
            ),
            "sources": [],
            "paper_a": paper_a,
            "paper_b": paper_b,
            "success": False,
        }

    # ========================================================
    # Retrieve isolated evidence
    # ========================================================

    docs_a = (
        _retrieve_paper_evidence(
            paper_name=paper_a,
            source=source_a,
        )
    )

    docs_b = (
        _retrieve_paper_evidence(
            paper_name=paper_b,
            source=source_b,
        )
    )

    # ========================================================
    # Extract facts independently
    # ========================================================

    facts_a = (
        _extract_paper_facts(
            paper_name=paper_a,
            docs=docs_a,
        )
    )

    facts_b = (
        _extract_paper_facts(
            paper_name=paper_b,
            docs=docs_b,
        )
    )

    # ========================================================
    # Final Comparison
    # ========================================================

    system_prompt = """
You are a rigorous academic paper comparison assistant.

Compare only the two supplied structured fact objects.

Do not add outside knowledge.

Do not invent missing results.

Clearly distinguish similarities and differences.

If one side lacks evidence, explicitly state that
the available evidence is insufficient.
"""

    user_prompt = f"""
Paper A:
{json.dumps(
    facts_a,
    ensure_ascii=False,
    indent=2,
)}

Paper B:
{json.dumps(
    facts_b,
    ensure_ascii=False,
    indent=2,
)}

Please compare the two papers.

Use the same language as the user's request.

Output structure:

## Paper Comparison

### 1. Method
Compare the core methods and architecture.

### 2. Dataset / Task
Compare datasets, benchmarks, and tasks.

### 3. Experimental Results
Compare reported results.
Do not compare numerical values unless the evidence
supports a meaningful comparison.

### 4. Main Similarities
Summarize important similarities.

### 5. Main Differences
Summarize important differences.

### 6. Conclusion
Give a concise overall comparison.
"""

    answer = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )

    # ========================================================
    # Sources
    # ========================================================

    sources = []

    seen = set()

    for paper_name, docs in [
        (paper_a, docs_a),
        (paper_b, docs_b),
    ]:

        for doc in docs:

            key = (
                doc.get(
                    "source"
                ),
                doc.get(
                    "page"
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            sources.append({
                "paper": paper_name,
                "source": doc.get(
                    "source"
                ),
                "page": doc.get(
                    "page"
                ),
                "rerank_score": doc.get(
                    "rerank_score"
                ),
                "dimension": doc.get(
                    "compare_dimension"
                ),
            })

    total_time = (
        time.time()
        - start_time
    )

    return {
        "answer": answer,

        "sources": sources,

        "paper_a": paper_a,
        "paper_b": paper_b,

        "source_a": source_a,
        "source_b": source_b,

        "facts": {
            "paper_a": facts_a,
            "paper_b": facts_b,
        },

        "retrieved_chunks": {
            "paper_a": len(
                docs_a
            ),
            "paper_b": len(
                docs_b
            ),
        },

        "total_time": total_time,

        "success": True,
    }