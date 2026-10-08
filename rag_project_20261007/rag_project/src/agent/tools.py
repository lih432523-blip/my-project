from typing import Dict, List, Any
from datetime import datetime
from src.agent.llm_client import chat
import json
import re
from src.generation import (
    build_index,
    rag_answer,
    retrieve,
)
from src.agent.paper_compare import (
    paper_compare,
)
from src.agent.paper_scope import (
    retrieve_from_paper,
)


# ============================================================
# 初始化状态
# ============================================================

_initialized = False


# ============================================================
# RAG 后端初始化
# ============================================================

def initialize_tools() -> int:
    """
    初始化 Agent 所依赖的 RAG 后端。

    一个 Python 进程中只初始化一次。
    """

    global _initialized

    if _initialized:
        return 0

    print("[Agent] 正在初始化 RAG 后端...")

    chunk_count = build_index()

    _initialized = True

    print(
        f"[Agent] RAG 后端初始化完成，共 {chunk_count} 个 chunk"
    )

    return chunk_count


# ============================================================
# Tool 1：完整知识库问答
# ============================================================

def knowledge_base_search(
    query: str
) -> Dict[str, Any]:
    """
    知识库问答工具。

    Pipeline:

        RAG Draft Answer
              ↓
        Retrieve Evidence
              ↓
        Evidence Validation
              ↓
        Grounded Final Answer

    目的：
        减少“检索到了相关内容，
        但生成阶段把相邻概念混淆”的问题。
    """

    import time

    start_time = time.time()

    # ========================================================
    # 1. 原始 RAG 回答
    # ========================================================

    draft_result = rag_answer(
        query=query,
        top_k=5,
        temperature=0.1,
    )

    draft_answer = draft_result.get(
        "answer",
        "",
    )

    # ========================================================
    # 2. 获取更宽的证据窗口
    # ========================================================

    evidence_docs = retrieve(
        query=query,
        top_k=8,
    )

    # ========================================================
    # 3. 构造 Evidence Context
    # ========================================================

    context_parts = []

    sources = []

    seen_sources = set()

    for i, doc in enumerate(
        evidence_docs,
        1,
    ):

        source = doc.get(
            "source",
            "Unknown",
        )

        page = doc.get(
            "page",
            "?",
        )

        score = doc.get(
            "rerank_score",
            0,
        )

        text = doc.get(
            "text",
            "",
        )

        context_parts.append(
            f"[Evidence {i}]\n"
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Content:\n{text}"
        )

        source_key = (
            source,
            page,
        )

        if source_key not in seen_sources:

            seen_sources.add(
                source_key
            )

            sources.append({
                "source": source,
                "page": page,
                "rerank_score": score,
            })

    context = "\n\n".join(
        context_parts
    )

    # ========================================================
    # 4. Evidence Guard
    # ========================================================

    system_prompt = """
你是一名严格的科研论文事实校验助手。

你将获得：

1. 用户问题
2. 一个 RAG 系统生成的 Draft Answer
3. 从论文中检索得到的原文证据

你的任务不是简单润色，而是验证 Draft Answer
是否真正受到论文原文支持。

必须遵守：

1. 最终答案只能依据 Evidence。
2. Draft Answer 可能是错误的，不得默认相信。
3. 如果 Draft Answer 把两个不同概念、机制、
   原因或实验混淆，必须纠正。
4. 特别注意区分：
   - 一个机制“是什么”
   - 为什么使用该机制
   - 相邻机制解决的其他问题
5. 不得因为两个概念出现在相邻段落，
   就把一个概念的作用归给另一个概念。
6. 不得使用模型自身记忆补充论文事实。
7. 如果证据不足，应明确说明证据不足，
   不得猜测。
8. 输出应直接回答用户问题。
9. 不要讨论 Draft Answer 的错误过程，
   只输出修正后的最终答案。
"""

    user_prompt = f"""
用户问题：

{query}


Draft Answer：

{draft_answer}


论文原文 Evidence：

{context}


请根据论文原文重新核验并回答用户问题。

如果 Draft Answer 与 Evidence 不一致，
必须以 Evidence 为准。
"""

    final_answer = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )

    total_time = (
        time.time()
        - start_time
    )

    return {
        "answer": final_answer,
        "sources": sources,
        "query": query,
        "draft_answer": draft_answer,
        "evidence_chunks": len(
            evidence_docs
        ),
        "total_time": total_time,
        "success": True,
    }


# ============================================================
# Tool 2：原始知识库检索
# ============================================================

def knowledge_base_retrieve(
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    原始知识库检索工具。

    输入：
        query
            检索问题。

        top_k
            返回文档块数量。

    功能：
        只进行检索，
        不让 LLM 生成最终答案。

    主要供：
        paper_summary
        paper_compare
        keyword_extract

    等高级 Tool 使用。
    """

    return retrieve(
        query=query,
        top_k=top_k,
    )


# ============================================================
# Tool 3：论文结构化总结
# ============================================================

def paper_summary(
    paper_name: str
) -> Dict[str, Any]:
    """
    论文结构化总结工具。

    Pipeline:

        Background / Method Retrieval
                  ↓
        Experiment Task Discovery
                  ↓
        Task A ── 独立检索 ── 独立事实抽取
        Task B ── 独立检索 ── 独立事实抽取
        Task C ── 独立检索 ── 独立事实抽取
                  ↓
        Structured Final Summary

    核心目标：
        1. 防止不同实验任务之间的数据集、参数、
           指标和结果发生 Cross-task Contamination。
        2. 所有检索均限制在目标论文对应 source，
           防止多论文知识库中的 Cross-paper Contamination。
    """

    # ========================================================
    # 内部辅助函数：从 LLM 输出中提取 JSON
    # ========================================================

    def extract_json_object(
        text: str
    ) -> Dict[str, Any]:

        text = text.strip()

        # 去掉 ```json ... ```
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
            return json.loads(text)

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                text,
                re.DOTALL,
            )

            if not match:
                return {}

            try:
                return json.loads(
                    match.group(0)
                )
            except json.JSONDecodeError:
                return {}

    # ========================================================
    # 内部辅助函数：Chunk 去重
    # ========================================================

    def deduplicate_docs(
        docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        unique_docs = {}

        for doc in docs:

            chunk_id = doc.get(
                "chunk_id"
            )

            if chunk_id:

                key = chunk_id

            else:

                key = (
                    f"{doc.get('source', '')}_"
                    f"{doc.get('page', '')}_"
                    f"{doc.get('text', '')[:120]}"
                )

            if key not in unique_docs:

                unique_docs[key] = doc

            else:

                old_score = unique_docs[key].get(
                    "rerank_score",
                    0,
                )

                new_score = doc.get(
                    "rerank_score",
                    0,
                )

                if new_score > old_score:
                    unique_docs[key] = doc

        return list(
            unique_docs.values()
        )

    # ========================================================
    # 内部辅助函数：文档转 Context
    # ========================================================

    def build_context(
        docs: List[Dict[str, Any]],
        prefix: str
    ) -> str:

        parts = []

        for i, doc in enumerate(
            docs,
            1,
        ):

            parts.append(
                f"[{prefix} Document {i}]\n"
                f"Source: {doc.get('source', 'Unknown')}\n"
                f"Page: {doc.get('page', '?')}\n"
                f"Rerank Score: "
                f"{doc.get('rerank_score', 0)}\n"
                f"Content:\n"
                f"{doc.get('text', '')}"
            )

        return "\n\n".join(
            parts
        )

    # ========================================================
    # 1. Background Retrieval
    # ========================================================

    background_queries = [
        (
            "What research problem does this paper address "
            "and what motivates the proposed work?"
        ),
        (
            "What limitations of recurrent, convolutional "
            "or previous sequence models are discussed?"
        ),
    ]

    background_docs = []

    for query in background_queries:
        background_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=2,
                candidate_k=20,
            )
        )

    background_docs = deduplicate_docs(
        background_docs
    )

    # ========================================================
    # 2. Method Retrieval
    # ========================================================

    method_queries = [
        (
            "What model architecture and method "
            "does this paper propose?"
        ),
        (
            "What are the key technical mechanisms "
            "and innovations of the proposed method?"
        ),
    ]

    method_docs = []

    for query in method_queries:

        method_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=2,
                candidate_k=20,
            )
        )

    method_docs = deduplicate_docs(
        method_docs
    )

    # ========================================================
    # 3. Experiment Task Discovery
    # ========================================================
    #
    # 这里不判断 Primary / Additional。
    #
    # 只回答：
    #
    # “论文到底进行了哪些不同的实验任务？”
    #

    discovery_queries = [
        (
            "What experimental tasks, benchmarks and datasets "
            "are used to evaluate the model in this paper?"
        ),
        (
            "What additional experiments or different tasks "
            "are evaluated in this paper?"
        ),
        (
            "What datasets and evaluation metrics are reported "
            "for the experiments in this paper?"
        ),
        (
            "What dataset was used for training?"
        ),
    ]

    discovery_docs = []

    for query in discovery_queries:

        discovery_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=5,
                candidate_k=30,
            )
        )

    discovery_docs = deduplicate_docs(
        discovery_docs
    )

    # 控制发现阶段上下文大小
    discovery_docs = discovery_docs[:12]

    discovery_context = build_context(
        discovery_docs,
        "Task Discovery",
    )

    discovery_system_prompt = """
你是一名科研论文实验信息抽取助手。

你需要从论文原文片段中识别论文实际进行了哪些
“彼此不同的实验任务”。

规则：

1. 只能依据提供的原文片段。

2. Experimental Task 指真正有独立：
   - Dataset
   - Evaluation Metric
   - Experimental Result
   的实验任务。

3. 不要把以下内容当作实验任务：
   - Sequence Transduction
   - Self-Attention
   - Transformer
   - Encoder-Decoder
   等泛化研究概念或模型名称。

4. 如果机器翻译、句法分析、分类、
   语言建模等分别使用不同数据集和指标，
   应视为不同实验任务。

5. 不要判断哪个任务最重要。

6. 不允许使用模型自身记忆补充论文内容。

7. 必须输出合法 JSON。
"""

    discovery_user_prompt = f"""
论文名称：

{paper_name}

下面是检索得到的实验相关原文：

{discovery_context}

请识别所有有明确原文证据支持的实验任务。

严格输出：

{{
  "tasks": [
    {{
      "name": "任务名称",
      "keywords": [
        "检索关键词1",
        "检索关键词2"
      ]
    }}
  ]
}}

不要输出 JSON 之外的任何内容。
"""

    discovery_result_text = chat(
        system_prompt=discovery_system_prompt,
        user_prompt=discovery_user_prompt,
        temperature=0.0,
    )

    discovery_result = extract_json_object(
        discovery_result_text
    )

    tasks = discovery_result.get(
        "tasks",
        [],
    )

    # ========================================================
    # 4. Task Discovery 安全检查
    # ========================================================

    cleaned_tasks = []

    for task in tasks:

        if not isinstance(
            task,
            dict,
        ):
            continue

        name = str(
            task.get(
                "name",
                ""
            )
        ).strip()

        keywords = task.get(
            "keywords",
            [],
        )

        if not name:
            continue

        if not isinstance(
            keywords,
            list,
        ):
            keywords = [
                str(keywords)
            ]

        # 防止模型产生过多伪任务
        cleaned_tasks.append({
            "name": name,
            "keywords": [
                str(x)
                for x in keywords
                if str(x).strip()
            ][:6],
        })

    # 最多保留 4 种实验任务
    cleaned_tasks = cleaned_tasks[:4]

    # 如果发现失败，不直接胡编
    if not cleaned_tasks:

        cleaned_tasks = [{
            "name": "Experimental Evaluation",
            "keywords": [],
        }]

    # ========================================================
    # 5. 每个任务独立检索
    # ========================================================

    task_results = []

    task_source_docs = []

    for task in cleaned_tasks:

        task_name = task["name"]

        task_keywords = ", ".join(
            task["keywords"]
        )

        # ----------------------------------------------------
        # Dataset / Setup Query
        # ----------------------------------------------------

        setup_query = (
            f'For the experimental task "{task_name}", '
            f"what dataset, training configuration, "
            f"decoding or evaluation setup are used? "
            f"Relevant keywords: {task_keywords}"
        )

        setup_docs = retrieve_from_paper(
            paper_name=paper_name,
            query=setup_query,
            top_k=3,
            candidate_k=30,
        )

        # ----------------------------------------------------
        # Result Query
        # ----------------------------------------------------

        result_query = (
            f'For the experimental task "{task_name}", '
            f"what evaluation metrics, numerical results "
            f"and comparisons with previous methods "
            f"are reported? "
            f"Relevant keywords: {task_keywords}"
        )

        result_docs = retrieve_from_paper(
            paper_name=paper_name,
            query=result_query,
            top_k=3,
            candidate_k=30,
        )

        task_docs = deduplicate_docs(
            setup_docs
            + result_docs
        )

        task_source_docs.extend(
            task_docs
        )

        task_context = build_context(
            task_docs,
            task_name,
        )

        # ====================================================
        # 6. 每个 Task 独立事实抽取
        # ====================================================
        #
        # 关键：
        #
        # Translation 的 Context
        # 只生成 Translation Facts。
        #
        # Parsing 的 Context
        # 只生成 Parsing Facts。
        #

        extraction_system_prompt = """
你是一名科研论文实验事实抽取助手。

你正在分析一个明确指定的实验任务。

规则：

1. 只抽取属于当前指定实验任务的信息。

2. 如果某个片段显然属于其他任务，
   必须忽略它。

3. Dataset、Training Setup、Metric、
   Result 和 Comparison 必须来自同一个任务语境。

4. 不允许把其他实验任务的：
   - 层数
   - beam size
   - alpha
   - 数据集
   - 指标
   - 结果
   拼接到当前任务。

5. 不允许依据模型自身记忆补充事实。

6. 如果某字段证据不足，
   填写：
   "检索内容中未提供足够信息"

7. 必须输出合法 JSON。
"""

        extraction_user_prompt = f"""
当前实验任务：

{task_name}

任务关键词：

{task_keywords}

下面是针对这个任务检索得到的原文：

{task_context}

请只提取属于：

{task_name}

这个实验任务的事实。

严格输出：

{{
  "task": "{task_name}",
  "dataset": "...",
  "training_setup": "...",
  "evaluation_metric": "...",
  "main_result": "...",
  "comparison": "...",
  "evidence_pages": []
}}

不要输出 JSON 之外的内容。
"""

        extraction_text = chat(
            system_prompt=extraction_system_prompt,
            user_prompt=extraction_user_prompt,
            temperature=0.0,
        )

        extracted = extract_json_object(
            extraction_text
        )

        if not extracted:

            extracted = {
                "task": task_name,
                "dataset": (
                    "检索内容中未提供足够信息"
                ),
                "training_setup": (
                    "检索内容中未提供足够信息"
                ),
                "evaluation_metric": (
                    "检索内容中未提供足够信息"
                ),
                "main_result": (
                    "检索内容中未提供足够信息"
                ),
                "comparison": (
                    "检索内容中未提供足够信息"
                ),
                "evidence_pages": [],
            }

        task_results.append(
            extracted
        )

    # ========================================================
    # 7. Background + Method Context
    # ========================================================

    background_context = build_context(
        background_docs,
        "Background",
    )

    method_context = build_context(
        method_docs,
        "Method",
    )

    # ========================================================
    # 8. 最终总结
    # ========================================================

    final_system_prompt = """
你是一名严谨的科研论文总结助手。

你将获得：

1. Background 原文
2. Method 原文
3. 已经按实验任务隔离并抽取好的 Experimental Facts

必须遵守：

1. Background 和 Method 只能依据对应原文。

2. Experimental Settings 和 Results
   必须严格使用 Experimental Facts。

3. 不得再次跨任务组合实验事实。

4. 不得自行修改实验数据。

5. 不得使用模型自身记忆添加具体事实。

6. 如果字段为
   “检索内容中未提供足够信息”，
   保持这一结论，不得自行补充。

7. 输出专业、清晰、简洁。
"""

    task_facts_json = json.dumps(
        task_results,
        ensure_ascii=False,
        indent=2,
    )

    final_user_prompt = f"""
请总结论文：

{paper_name}


==============================
Research Background Evidence
==============================

{background_context}


==============================
Method Evidence
==============================

{method_context}


==============================
Task-isolated Experimental Facts
==============================

{task_facts_json}


请严格按照下面结构输出：


## 1. Research Background

总结研究背景、核心问题和已有方法局限。


## 2. Proposed Method

总结：
- 主要方法
- 模型结构
- 核心机制
- 技术创新


## 3. Experimental Settings

对每个实验任务分别写：

### Experiment N: <Task>

- Dataset:
- Training Setup:
- Evaluation Metric:


## 4. Experimental Results

必须和上一部分任务一一对应：

### Experiment N: <Task>

- Main Result:
- Comparison:


## 5. Main Contributions

概括论文主要贡献。


## 6. Conclusion

简洁总结整篇论文。


严禁重新组合不同实验任务的数据、
参数、指标和结果。
"""

    answer = chat(
        system_prompt=final_system_prompt,
        user_prompt=final_user_prompt,
        temperature=0.0,
    )

    # ========================================================
    # 9. Sources
    # ========================================================

    all_docs = (
        background_docs
        + method_docs
        + discovery_docs
        + task_source_docs
    )

    all_docs = deduplicate_docs(
        all_docs
    )

    sources = []

    for doc in all_docs:

        sources.append({
            "source": doc.get(
                "source",
                "Unknown",
            ),
            "page": doc.get(
                "page",
                "?",
            ),
            "rerank_score": doc.get(
                "rerank_score",
                0,
            ),
        })

    # ========================================================
    # 10. Return
    # ========================================================

    return {
        "answer": answer,
        "sources": sources,
        "paper": paper_name,
        "experiment_tasks": cleaned_tasks,
        "task_facts": task_results,
        "retrieved_chunks": len(
            all_docs
        ),
    }


def paper_metadata(
    paper_name: str
) -> Dict[str, Any]:
    """
    论文元信息提取工具。

    核心策略：
        1. 所有检索限制在目标论文对应 source
        2. 针对首页/作者/摘要/出版信息进行多 Query 检索
        3. 优先聚合第一页 chunk
        4. LLM 必须同时返回 metadata + evidence
        5. 没有证据的字段自动置为 null
    """

    import json
    import re

    # ========================================================
    # 1. 元信息定向检索
    # ========================================================

    queries = [
        (
            f'"{paper_name}" title authors affiliations'
        ),
        (
            f'"{paper_name}" abstract'
        ),
        (
            "full paper abstract beginning middle end"
        ),
        (
            "paper abstract experimental results conclusion"
        ),
        (
            "paper first page authors affiliations abstract"
        ),
        (
            "paper publication year conference venue DOI"
        ),
        (
            "Abstract authors title"
        ),
    ]

    candidates = []

    for query in queries:
        docs = retrieve_from_paper(
            paper_name=paper_name,
            query=query,
            top_k=12,
            candidate_k=40,
        )

        candidates.extend(
            docs
        )

    # ========================================================
    # 2. 去重
    # ========================================================

    unique_docs = {}

    for doc in candidates:

        chunk_id = doc.get(
            "chunk_id"
        )

        if chunk_id:

            key = chunk_id

        else:

            key = (
                f"{doc.get('source', '')}_"
                f"{doc.get('page', '')}_"
                f"{doc.get('text', '')[:100]}"
            )

        if key not in unique_docs:

            unique_docs[key] = doc

        else:

            old_score = unique_docs[key].get(
                "rerank_score",
                0,
            )

            new_score = doc.get(
                "rerank_score",
                0,
            )

            if new_score > old_score:
                unique_docs[key] = doc

    docs = list(
        unique_docs.values()
    )

    # ========================================================
    # 3. 首页优先
    # ========================================================

    first_page_docs = [
        doc
        for doc in docs
        if doc.get("page") == 1
    ]

    other_docs = [
        doc
        for doc in docs
        if doc.get("page") != 1
    ]

    # 首页 chunk 按 chunk_id 中的 cN 排序
    def chunk_order(doc):

        chunk_id = str(
            doc.get(
                "chunk_id",
                ""
            )
        )

        match = re.search(
            r"_c(\d+)",
            chunk_id,
        )

        if match:
            return int(
                match.group(1)
            )

        return 999

    first_page_docs.sort(
        key=chunk_order
    )

    # 其他页按 rerank score
    other_docs.sort(
        key=lambda x: float(
            x.get(
                "rerank_score",
                0
            )
        ),
        reverse=True,
    )

    # 首页尽量全部保留
    # 后续页只作为 year / venue / DOI 补充证据
    docs = (
        first_page_docs[:12]
        + other_docs[:6]
    )

    # ========================================================
    # 4. 构造 Context
    # ========================================================

    context_parts = []

    sources = []

    for i, doc in enumerate(
        docs,
        1,
    ):

        source = doc.get(
            "source",
            "Unknown",
        )

        page = doc.get(
            "page",
            "?",
        )

        text = doc.get(
            "text",
            "",
        )

        score = doc.get(
            "rerank_score",
            0,
        )

        context_parts.append(
            f"[Metadata Evidence {i}]\n"
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Chunk ID: {doc.get('chunk_id', '')}\n"
            f"Content:\n{text}"
        )

        sources.append({
            "source": source,
            "page": page,
            "rerank_score": score,
        })

    context = "\n\n".join(
        context_parts
    )

    if not docs:

        return {
            "answer": (
                "未能从论文知识库中"
                "检索到元信息。"
            ),
            "metadata": {
                "title": None,
                "authors": [],
                "year": None,
                "abstract": None,
                "doi": None,
                "venue": None,
            },
            "evidence": {},
            "sources": [],
            "paper": paper_name,
            "success": False,
        }

    # ========================================================
    # 5. Evidence-grounded Metadata Extraction
    # ========================================================

    system_prompt = """
你是一名严格的论文元信息抽取助手。

你只能从提供的论文原文片段中提取信息。

绝对禁止使用你自身记忆补充论文信息。

规则：

1. title 必须在原文中明确出现。
2. authors 必须逐个依据原文出现的人名提取。
3. 不得因为作者列表过长而省略最后几位作者。
4. year 只有原文明确出现年份时才能填写。
5. venue 只有原文明确出现会议或期刊信息时才能填写。
6. DOI 只有原文明确出现 DOI 时才能填写。
7. abstract 必须来自论文摘要原文。
8. 不确定的字段必须设为 null。
9. authors 找不到时返回空数组。
10. 每个非空字段必须同时给出 evidence。
11. evidence 必须直接来自给定文本，不允许自己创造证据。
12. 必须只输出合法 JSON。
"""

    user_prompt = f"""
目标论文：

{paper_name}


下面是论文元信息相关原文：

{context}


请严格输出：

{{
  "metadata": {{
    "title": null,
    "authors": [],
    "year": null,
    "abstract": null,
    "doi": null,
    "venue": null
  }},
  "evidence": {{
    "title": null,
    "authors": null,
    "year": null,
    "abstract": null,
    "doi": null,
    "venue": null
  }}
}}

要求：

如果某字段没有明确原文证据，
metadata 和 evidence 中对应字段都必须为 null。

不要输出 Markdown。
不要输出解释。
"""

    raw_result = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )

    # ========================================================
    # 6. JSON 清洗
    # ========================================================

    cleaned = raw_result.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    result = {}

    try:

        result = json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            cleaned,
            re.DOTALL,
        )

        if match:

            try:
                result = json.loads(
                    match.group(0)
                )
            except json.JSONDecodeError:
                result = {}

    # ========================================================
    # 7. 安全默认值
    # ========================================================

    metadata = result.get(
        "metadata",
        {}
    )

    evidence = result.get(
        "evidence",
        {}
    )

    if not isinstance(
        metadata,
        dict,
    ):

        metadata = {}

    if not isinstance(
        evidence,
        dict,
    ):

        evidence = {}

    fields = [
        "title",
        "authors",
        "year",
        "abstract",
        "doi",
        "venue",
    ]

    for field in fields:

        metadata.setdefault(
            field,
            [] if field == "authors" else None,
        )

        evidence.setdefault(
            field,
            None,
        )

    if not isinstance(
        metadata["authors"],
        list,
    ):

        metadata["authors"] = []

    # ========================================================
    # 8. Evidence Validation
    # ========================================================
    #
    # 如果 LLM 给出了字段，
    # 却没有提供任何 evidence，
    # 则这个字段不能被信任。
    #

    for field in [
        "title",
        "year",
        "abstract",
        "doi",
        "venue",
    ]:

        if (
            metadata.get(field) is not None
            and not evidence.get(field)
        ):

            metadata[field] = None

    # 作者同样必须有证据
    if (
        metadata.get("authors")
        and not evidence.get("authors")
    ):

        metadata["authors"] = []

    # ========================================================
    # Year deterministic recovery
    # ========================================================

    if metadata.get("year") is None:

        venue = metadata.get("venue")

        if isinstance(venue, str):

            year_match = re.search(
                r"\b((?:19|20)\d{2})\b",
                venue,
            )

            if year_match:
                metadata["year"] = int(
                    year_match.group(1)
                )

                # year 的证据继承自 venue 原文证据
                evidence["year"] = evidence.get(
                    "venue"
                )

    # ========================================================
    # 9. 输出
    # ========================================================

    authors_text = (
        ", ".join(
            metadata["authors"]
        )
        if metadata["authors"]
        else "未检索到"
    )

    answer = (
        "## Paper Metadata\n\n"
        f"**Title:** "
        f"{metadata['title'] or '未检索到'}\n\n"

        f"**Authors:** "
        f"{authors_text}\n\n"

        f"**Year:** "
        f"{metadata['year'] or '未检索到'}\n\n"

        f"**Venue:** "
        f"{metadata['venue'] or '未检索到'}\n\n"

        f"**DOI:** "
        f"{metadata['doi'] or '未检索到'}\n\n"

        f"**Abstract:**\n"
        f"{metadata['abstract'] or '未检索到'}"
    )

    return {
        "answer": answer,
        "metadata": metadata,
        "evidence": evidence,
        "sources": sources,
        "paper": paper_name,
        "retrieved_chunks": len(
            docs
        ),
        "success": True,
    }

def keyword_extract(
    paper_name: str
) -> Dict[str, Any]:
    """
    论文关键词提取工具。

    使用 Paper-scoped Retrieval
    + Category-isolated Retrieval
    + Category-isolated Extraction。

    每一类关键词：
        在目标论文 source 内独立检索
        -> 独立 LLM 抽取
        -> 最后统一合并

    同时避免：
        1. 一个 Prompt 同时承担四类抽取任务；
        2. 多论文知识库中的跨论文事实污染。
    """

    import json
    import re

    # ========================================================
    # 1. 文档去重
    # ========================================================

    def deduplicate_docs(
        docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        unique_docs = {}

        for doc in docs:

            chunk_id = doc.get("chunk_id")

            if chunk_id:
                key = chunk_id
            else:
                key = (
                    f"{doc.get('source', '')}_"
                    f"{doc.get('page', '')}_"
                    f"{doc.get('text', '')[:100]}"
                )

            if key not in unique_docs:

                unique_docs[key] = doc

            else:

                old_score = unique_docs[key].get(
                    "rerank_score",
                    0,
                )

                new_score = doc.get(
                    "rerank_score",
                    0,
                )

                if new_score > old_score:
                    unique_docs[key] = doc

        return list(
            unique_docs.values()
        )

    # ========================================================
    # 2. 构造 Context
    # ========================================================

    def build_context(
        docs: List[Dict[str, Any]]
    ) -> str:

        parts = []

        for i, doc in enumerate(
            docs,
            1,
        ):

            parts.append(
                f"[Document {i}]\n"
                f"Source: {doc.get('source', 'Unknown')}\n"
                f"Page: {doc.get('page', '?')}\n"
                f"Content:\n"
                f"{doc.get('text', '')}"
            )

        return "\n\n".join(parts)

    # ========================================================
    # 3. 独立关键词抽取器
    # ========================================================

    def extract_category(
        category_name: str,
        description: str,
        docs: List[Dict[str, Any]],
    ) -> List[str]:

        if not docs:
            return []

        context = build_context(
            docs
        )

        system_prompt = f"""
你是一名严谨的科研论文关键词抽取助手。

你现在只需要完成一个任务：

提取论文的 {category_name}。

定义：

{description}

规则：

1. 只能依据提供的论文原文。
2. 不得使用模型自身记忆补充关键词。
3. 不要返回过于宽泛的词：
   paper
   model
   method
   experiment
   result
   computation
4. 优先使用标准科研术语。
5. 最多返回 8 个关键词。
6. 如果 PDF 文本存在明显单词粘连，可以恢复正常空格。

例如：

machinetranslation
→ machine translation

languagemodeling
→ language modeling

WallStreetJournal
→ Wall Street Journal

7. 只允许修复文本格式，
   不得创造原文中不存在的事实。

8. 如果原文中明确存在相关关键词，
   应当提取，不要因为要求严格而全部返回空。

9. 必须输出合法 JSON。

严格格式：

{{
  "keywords": []
}}
"""

        user_prompt = f"""
论文：

{paper_name}

下面是与 {category_name} 相关的论文原文：

{context}

请从这些原文中提取：

{category_name}

严格输出：

{{
  "keywords": [
    "keyword 1",
    "keyword 2"
  ]
}}

如果原文明确出现相关科研术语，
请正常提取。

不要输出 JSON 之外的内容。
"""

        raw_result = chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            json_mode=True,
        )

        # 调试信息
        print(
            f"\n[{category_name} Raw LLM Output]"
        )

        print(
            raw_result
        )

        try:

            result = json.loads(
                raw_result
            )

        except json.JSONDecodeError:

            cleaned = re.sub(
                r"^```(?:json)?\s*",
                "",
                raw_result.strip(),
                flags=re.IGNORECASE,
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned,
            )

            match = re.search(
                r"\{.*\}",
                cleaned,
                re.DOTALL,
            )

            if not match:
                return []

            try:

                result = json.loads(
                    match.group(0)
                )

            except json.JSONDecodeError:

                return []

        keywords = result.get(
            "keywords",
            []
        )

        if not isinstance(
            keywords,
            list,
        ):
            return []

        # ====================================================
        # 清洗 + 去重
        # ====================================================

        final_keywords = []

        seen = set()

        for keyword in keywords:

            keyword = str(
                keyword
            ).strip()

            if not keyword:
                continue

            normalized = (
                keyword
                .lower()
                .strip()
            )

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            final_keywords.append(
                keyword
            )

        return final_keywords[:8]

    # ========================================================
    # 4. Core Keywords Retrieval
    # ========================================================

    core_queries = [
        (
            "What are the central ideas and main "
            "research concepts of this paper?"
        ),
        (
            "What is the main contribution and key idea "
            "introduced in this paper?"
        ),
    ]

    core_docs = []

    for query in core_queries:

        core_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=3,
                candidate_k=20,
            )
        )

    core_docs = deduplicate_docs(
        core_docs
    )[:6]

    # ========================================================
    # 5. Method Keywords Retrieval
    # ========================================================

    method_queries = [
        (
            "What model architecture and technical "
            "mechanisms are proposed in this paper?"
        ),
        (
            "What are the key components of the "
            "Transformer architecture?"
        ),
        (
            "What attention mechanisms, encoding methods "
            "and neural network components are used?"
        ),
    ]

    method_docs = []

    for query in method_queries:

        method_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=3,
                candidate_k=20,
            )
        )

    method_docs = deduplicate_docs(
        method_docs
    )[:7]

    # ========================================================
    # 6. Task Keywords Retrieval
    # ========================================================

    task_queries = [
        (
            "What research tasks and experimental tasks "
            "are evaluated in this paper?"
        ),
        (
            "What machine translation or other NLP tasks "
            "are performed in this paper?"
        ),
    ]

    task_docs = []

    for query in task_queries:

        task_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=3,
                candidate_k=25,
            )
        )

    task_docs = deduplicate_docs(
        task_docs
    )[:6]

    # ========================================================
    # 7. Dataset Keywords Retrieval
    # ========================================================

    dataset_queries = [
        "What dataset was used for training?",
        (
            "What datasets were used for the "
            "machine translation experiments?"
        ),
        (
            "What datasets or corpora were used "
            "in other experiments in this paper?"
        ),
    ]

    dataset_docs = []

    for query in dataset_queries:

        dataset_docs.extend(
            retrieve_from_paper(
                paper_name=paper_name,
                query=query,
                top_k=3,
                candidate_k=25,
            )
        )

    dataset_docs = deduplicate_docs(
        dataset_docs
    )[:7]

    # ========================================================
    # 8. 四类独立抽取
    # ========================================================

    core_keywords = extract_category(
        category_name="Core Keywords",
        description=(
            "能够代表整篇论文最核心思想、"
            "研究主题和主要贡献的概念。"
        ),
        docs=core_docs,
    )

    method_keywords = extract_category(
        category_name="Method Keywords",
        description=(
            "模型结构、算法机制、注意力机制、"
            "编码方法和关键技术组件。"
        ),
        docs=method_docs,
    )

    task_keywords = extract_category(
        category_name="Task Keywords",
        description=(
            "论文实际研究或评估的任务名称，"
            "例如机器翻译、句法分析等。"
        ),
        docs=task_docs,
    )

    dataset_keywords = extract_category(
        category_name="Dataset Keywords",
        description=(
            "论文明确使用的数据集、benchmark、"
            "corpus 或实验数据名称。"
        ),
        docs=dataset_docs,
    )

    # ========================================================
    # 9. 统一结果
    # ========================================================

    keywords = {
        "core_keywords": core_keywords,
        "method_keywords": method_keywords,
        "task_keywords": task_keywords,
        "dataset_keywords": dataset_keywords,
    }

    # ========================================================
    # 10. Sources
    # ========================================================

    all_docs = deduplicate_docs(
        core_docs
        + method_docs
        + task_docs
        + dataset_docs
    )

    sources = []

    seen_sources = set()

    for doc in all_docs:

        key = (
            doc.get(
                "source",
                "Unknown",
            ),
            doc.get(
                "page",
                "?",
            ),
        )

        if key in seen_sources:
            continue

        seen_sources.add(
            key
        )

        sources.append({
            "source": doc.get(
                "source",
                "Unknown",
            ),
            "page": doc.get(
                "page",
                "?",
            ),
            "rerank_score": doc.get(
                "rerank_score",
                0,
            ),
        })

    # ========================================================
    # 11. Human-readable output
    # ========================================================

    def format_keywords(
        items: List[str]
    ) -> str:

        if not items:
            return "未检索到"

        return ", ".join(
            items
        )

    answer = (
        "## Paper Keywords\n\n"

        "**Core Keywords:**\n"
        f"{format_keywords(core_keywords)}\n\n"

        "**Method Keywords:**\n"
        f"{format_keywords(method_keywords)}\n\n"

        "**Task Keywords:**\n"
        f"{format_keywords(task_keywords)}\n\n"

        "**Dataset Keywords:**\n"
        f"{format_keywords(dataset_keywords)}"
    )

    # ========================================================
    # 12. Success
    # ========================================================

    has_keywords = any([
        core_keywords,
        method_keywords,
        task_keywords,
        dataset_keywords,
    ])

    return {
        "answer": answer,

        "keywords": keywords,

        "sources": sources,

        "paper": paper_name,

        "retrieval_stats": {
            "core_chunks": len(
                core_docs
            ),
            "method_chunks": len(
                method_docs
            ),
            "task_chunks": len(
                task_docs
            ),
            "dataset_chunks": len(
                dataset_docs
            ),
        },

        "retrieved_chunks": len(
            all_docs
        ),

        "success": bool(
            has_keywords
        ),
    }


def current_time(
    _: str = ""
) -> Dict[str, Any]:
    """
    获取服务器当前系统时间。

    这是一个非 RAG 工具，
    用于测试 Agent 对通用工具的选择能力。
    """

    now = datetime.now().astimezone()

    timezone_name = (
        now.tzname()
        or "Local Time"
    )

    iso_time = now.isoformat(
        timespec="seconds"
    )

    readable_time = now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    answer = (
        f"当前系统时间：{readable_time} "
        f"({timezone_name})"
    )

    return {
        "answer": answer,
        "datetime": iso_time,
        "timezone": timezone_name,
        "success": True,
    }


# ============================================================
# Tool Registry
# ============================================================
#
# 注意：
#
# TOOLS 一定要放在所有 Tool 函数定义之后！
#
# 否则：
#
# "func": paper_summary
#
# 执行时 paper_summary 还没定义，
# 就会产生：
#
# NameError
#

TOOLS = {

    # --------------------------------------------------------
    # RAG QA
    # --------------------------------------------------------

    "knowledge_base_search": {

        "func": knowledge_base_search,

        "description": (
            "在论文知识库中检索相关信息，"
            "并生成带引用来源的完整答案。"
            "适合回答论文中的具体事实、"
            "方法、数据集、实验结果等问题。"
            "如果用户只是询问论文中的一个具体问题，"
            "优先使用这个工具。"
        ),
    },

    # --------------------------------------------------------
    # Raw Retrieval
    # --------------------------------------------------------

    "knowledge_base_retrieve": {

        "func": knowledge_base_retrieve,

        "description": (
            "从论文知识库中检索原始文本片段，"
            "但不生成最终答案。"
            "适合需要获取原始论文材料的任务，"
            "通常供其他高级科研工具使用。"
        ),
    },

    # --------------------------------------------------------
    # Paper Summary
    # --------------------------------------------------------

    "paper_summary": {

        "func": paper_summary,

        "description": (
            "对整篇论文进行结构化总结，"
            "包括研究背景、提出的方法、"
            "数据集与实验设置、主要实验结果、"
            "核心贡献和结论。"
            "当用户要求总结、概括、介绍、"
            "梳理整篇论文时，应优先使用此工具。"
            "输入应为论文名称。"
        ),
    },
    "paper_metadata": {

        "func": paper_metadata,

        "description": (
            "提取论文的元信息，包括标题、作者、年份、"
            "摘要、DOI和发表信息。"
            "当用户询问论文作者、标题、发表年份、"
            "摘要、DOI、会议或基本信息时使用。"
            "输入应为论文名称。"
        ),
    },

    "keyword_extract": {

        "func": keyword_extract,

        "description": (
            "从论文中提取核心科研关键词，"
            "并区分核心概念、方法术语、"
            "实验任务和数据集关键词。"
            "当用户要求提取论文关键词、"
            "核心术语、研究主题或技术关键词时使用。"
            "输入应为论文名称。"
        ),
    },

    "current_time": {

        "func": current_time,

        "description": (
            "返回当前系统日期和时间。"
            "当用户询问现在几点、今天日期、"
            "当前时间或当前日期时使用。"
            "此工具不需要论文名称或知识库检索。"
        ),
    },

    "paper_compare": {
        "func": paper_compare,
        "description": (
            "比较两篇论文的方法、数据集、实验任务和实验结果。"
            "必须输入两篇论文。"
            "推荐 Action Input 格式："
            "Paper A ||| Paper B。"
            "该工具会分别检索两篇论文并进行 source 隔离，"
            "避免跨论文事实污染。"
        ),
    },

}


def refresh_knowledge_base() -> int:
    """
    手动重新扫描 PDF 并重建知识库。

    适用于：
        - 新增 PDF
        - 删除 PDF
        - 更新 PDF

    不需要修改 C 模块。
    """

    global _initialized

    print(
        "[Agent] 正在重新构建知识库..."
    )

    chunk_count = build_index()

    _initialized = True

    print(
        "[Agent] 知识库重新构建完成，"
        f"共 {chunk_count} 个 chunk"
    )

    return chunk_count

# ============================================================
# Tool 获取
# ============================================================

def get_tool(
    tool_name: str
):
    """
    根据 Tool 名称获取对应函数。
    """

    tool = TOOLS.get(
        tool_name
    )

    if tool is None:

        available = ", ".join(
            TOOLS.keys()
        )

        raise ValueError(
            f"未知工具: {tool_name}。"
            f"可用工具: {available}"
        )

    return tool["func"]


# ============================================================
# Tool Description
# ============================================================

def get_tool_descriptions() -> str:
    """
    返回所有 Tool 的描述。

    后续用于：

        Agent System Prompt

    让 LLM 知道有哪些工具可以使用。
    """

    descriptions = []

    for name, info in TOOLS.items():

        descriptions.append(
            f"- {name}: "
            f"{info['description']}"
        )

    return "\n".join(
        descriptions
    )