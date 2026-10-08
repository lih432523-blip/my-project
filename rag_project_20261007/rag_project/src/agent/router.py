import re
from typing import Dict, Any


def route_question(
    question: str,
) -> Dict[str, Any]:
    """
    Fast Rule-based Router.

    高置信度意图：
        current_time
        paper_compare
        keyword_extract
        paper_metadata
        paper_summary

    其他复杂科研问题：
        react
    """

    text = (
        question
        or ""
    ).strip()

    lower = text.lower()

    # ========================================================
    # 1. Current Time
    # ========================================================

    time_patterns = [
        "现在几点",
        "当前时间",
        "现在时间",
        "几点了",
        "what time",
        "current time",
    ]

    if any(
        item in lower
        for item
        in time_patterns
    ):

        return {
            "route": "current_time",
            "confidence": "high",
            "reason": (
                "matched current-time intent"
            ),
        }

    # ========================================================
    # 2. Paper Compare
    # ========================================================

    # ========================================================
    # 2. Paper Compare
    # ========================================================

    compare_keywords = [
        "比较",
        "对比",
        "异同",
        "compare",
        "comparison",
        "versus",
        " vs ",
    ]

    compare_hit = any(
        item in lower
        for item in compare_keywords
    )

    # --------------------------------------------------------
    # 明确的“两篇论文”信号
    # --------------------------------------------------------

    quoted_papers = re.findall(
        r"《([^》]+)》",
        text,
    )

    has_two_quoted_papers = (
            len(quoted_papers) >= 2
    )

    has_internal_separator = (
            "|||" in text
    )

    has_vs_pair = bool(
        re.search(
            r".+\s+(?:vs\.?|versus)\s+.+",
            text,
            flags=re.IGNORECASE,
        )
    )

    has_paper_word = any([
        "论文" in text,
        "paper" in lower,
        "papers" in lower,
    ])

    has_pair_connector = any([
        "和" in text,
        "与" in text,
        "以及" in text,
        " and " in lower,
    ])

    # --------------------------------------------------------
    # 只有明确是“两篇论文比较”，才 Direct Route
    # --------------------------------------------------------

    if (
        compare_hit
        and (
        has_two_quoted_papers
        or has_internal_separator
        or has_vs_pair
        or (
                has_paper_word
                and has_pair_connector
            )
        )
    ):
        return {
            "route": "paper_compare",
            "confidence": "high",
            "reason": (
                "matched two-paper comparison intent"
            ),
        }

    # ========================================================
    # 3. Keyword Extraction
    # ========================================================

    keyword_patterns = [
        "关键词",
        "核心词",
        "核心术语",
        "技术关键词",
        "研究主题",
        "keywords",
        "keyword",
    ]

    if any(
        item in lower
        for item
        in keyword_patterns
    ):

        return {
            "route": "keyword_extract",
            "confidence": "high",
            "reason": (
                "matched keyword-extraction intent"
            ),
        }

    # ========================================================
    # 4. Paper Metadata
    # ========================================================

    metadata_patterns = [
        "作者",
        "doi",
        "发表年份",
        "年份",
        "摘要",
        "会议",
        "期刊",
        "元信息",
        "authors",
        "author",
        "abstract",
        "venue",
        "year",
    ]

    if any(
        item in lower
        for item
        in metadata_patterns
    ):

        return {
            "route": "paper_metadata",
            "confidence": "high",
            "reason": (
                "matched paper-metadata intent"
            ),
        }

    # ========================================================
    # 5. Paper Summary
    # ========================================================

    summary_patterns = [
        "总结论文",
        "总结一下论文",
        "概括论文",
        "概括一下论文",
        "介绍论文",
        "介绍一下论文",
        "论文总结",
        "summarize",
        "summary",
    ]

    if any(
        item in lower
        for item
        in summary_patterns
    ):

        return {
            "route": "paper_summary",
            "confidence": "high",
            "reason": (
                "matched paper-summary intent"
            ),
        }

    # ========================================================
    # 6. ReAct Fallback
    # ========================================================

    return {
        "route": "react",
        "confidence": "low",
        "reason": (
            "no high-confidence rule matched"
        ),
    }