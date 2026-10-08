import os
import re

from difflib import SequenceMatcher
from typing import Dict, List, Any, Tuple

from src.generation import retrieve


# ============================================================
# Text Normalize
# ============================================================

def normalize_text(
    text: str,
) -> str:
    """
    用于论文名与 PDF 文件名 / 文本进行宽松匹配。
    """

    return re.sub(
        r"[^a-z0-9]+",
        "",
        (text or "").lower(),
    )


# ============================================================
# Resolve Paper Source
# ============================================================

def resolve_paper_source(
    paper_name: str,
) -> str:
    """
    根据论文名确定其在知识库中的 source。

    当前 C 的 retrieve() 没有 source filter 参数，
    因此 D 层先通过标题相关检索确定 PDF source。

    返回：
        source，例如：
        attention_is_all_you_need.pdf
    """

    paper_name = (
        paper_name
        or ""
    ).strip()

    if not paper_name:

        raise ValueError(
            "论文名称不能为空。"
        )

    queries = [
        f'"{paper_name}" title authors abstract',
        f'"{paper_name}" paper title',
        paper_name,
    ]

    all_docs: List[
        Dict[str, Any]
    ] = []

    for query in queries:

        docs = retrieve(
            query=query,
            top_k=20,
        )

        all_docs.extend(
            docs
        )

    if not all_docs:

        raise ValueError(
            f"知识库中没有检索到论文：{paper_name}"
        )

    grouped: Dict[
        str,
        List[Dict[str, Any]]
    ] = {}

    for doc in all_docs:

        source = str(
            doc.get(
                "source",
                "",
            )
        ).strip()

        if not source:
            continue

        grouped.setdefault(
            source,
            [],
        ).append(
            doc
        )

    if not grouped:

        raise ValueError(
            f"无法确定论文对应 PDF：{paper_name}"
        )

    title_norm = normalize_text(
        paper_name
    )

    best_source = ""
    best_score = -1.0

    for source, docs in grouped.items():

        # ----------------------------------------------------
        # 1. 文件名相似度
        # ----------------------------------------------------

        source_stem = (
            os.path.splitext(
                os.path.basename(
                    source
                )
            )[0]
        )

        source_norm = normalize_text(
            source_stem
        )

        filename_score = (
            SequenceMatcher(
                None,
                title_norm,
                source_norm,
            ).ratio()
        )

        # ----------------------------------------------------
        # 2. 检索文本里是否直接包含论文名
        # ----------------------------------------------------

        content = " ".join(
            str(
                doc.get(
                    "text",
                    "",
                )
            )
            for doc in docs[:5]
        )

        content_norm = normalize_text(
            content
        )

        title_in_content = (
            1.0
            if (
                title_norm
                and title_norm
                in content_norm
            )
            else 0.0
        )

        # ----------------------------------------------------
        # 3. 同一 source 被召回次数
        # ----------------------------------------------------

        frequency_bonus = min(
            len(docs),
            5,
        ) * 0.02

        score = (
            filename_score * 0.65
            + title_in_content * 0.30
            + frequency_bonus
        )

        if score > best_score:

            best_score = score
            best_source = source

    if not best_source:

        raise ValueError(
            f"无法解析论文来源：{paper_name}"
        )

    return best_source


# ============================================================
# Retrieve From One Paper
# ============================================================

def retrieve_from_paper(
    paper_name: str,
    query: str,
    top_k: int = 5,
    candidate_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    从指定论文中检索。

    流程：

        paper_name
            ↓
        resolve source
            ↓
        全局 retrieve(candidate_k)
            ↓
        source filter
            ↓
        top_k

    注意：
        这是 D 层隔离策略，
        不修改 C 的 retrieve() 接口。
    """

    source = resolve_paper_source(
        paper_name
    )

    full_query = (
        f"{paper_name}. {query}"
    )

    docs = retrieve(
        query=full_query,
        top_k=candidate_k,
    )

    filtered_docs = [
        doc
        for doc in docs
        if str(
            doc.get(
                "source",
                "",
            )
        ).strip()
        == source
    ]

    filtered_docs.sort(
        key=lambda x: float(
            x.get(
                "rerank_score",
                0.0,
            )
            or 0.0
        ),
        reverse=True,
    )

    return filtered_docs[
        :top_k
    ]


# ============================================================
# Retrieve Multiple Queries
# ============================================================

def retrieve_many_from_paper(
    paper_name: str,
    queries: List[str],
    top_k_per_query: int = 5,
    candidate_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    对同一篇论文执行多个 Query，
    自动进行 source 隔离和 chunk 去重。
    """

    collected = {}

    for query in queries:

        docs = retrieve_from_paper(
            paper_name=paper_name,
            query=query,
            top_k=top_k_per_query,
            candidate_k=candidate_k,
        )

        for doc in docs:

            chunk_id = doc.get(
                "chunk_id"
            )

            if chunk_id:

                key = (
                    doc.get(
                        "source"
                    ),
                    chunk_id,
                )

            else:

                key = (
                    doc.get(
                        "source"
                    ),
                    doc.get(
                        "page"
                    ),
                    str(
                        doc.get(
                            "text",
                            "",
                        )
                    )[:120],
                )

            if key not in collected:

                collected[
                    key
                ] = doc

            else:

                old_score = float(
                    collected[
                        key
                    ].get(
                        "rerank_score",
                        0.0,
                    )
                    or 0.0
                )

                new_score = float(
                    doc.get(
                        "rerank_score",
                        0.0,
                    )
                    or 0.0
                )

                if (
                    new_score
                    > old_score
                ):

                    collected[
                        key
                    ] = doc

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

    return docs


# ============================================================
# Resolve + Retrieve
# ============================================================

def resolve_and_retrieve(
    paper_name: str,
    query: str,
    top_k: int = 5,
) -> Tuple[
    str,
    List[Dict[str, Any]]
]:
    """
    同时返回：

        source
        docs
    """

    source = resolve_paper_source(
        paper_name
    )

    docs = retrieve_from_paper(
        paper_name=paper_name,
        query=query,
        top_k=top_k,
    )

    return (
        source,
        docs,
    )