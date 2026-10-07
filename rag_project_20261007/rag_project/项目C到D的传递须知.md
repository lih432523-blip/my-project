# 项目C到D的传递须知

> 本文档面向成员 D（Agent 开发），说明成员 C 已完成模块一 + 模块二的全部代码结构、文件位置、接口定义与调用方法。
> **AI 助手读取本文件即可完整理解 RAG 后端的使用方式。**

---

## 一、项目根目录

/root/autodl-tmp/rag_project/

**所有路径均为绝对路径**，请在代码中直接使用，不要使用相对路径。

---

## 二、完整文件结构

/root/autodl-tmp/rag_project/
├── README.md                            项目说明
├── requirements.txt                     Python 依赖清单
├── 项目C到D的传递须知.md                本文档
├── data/                                上传的 PDF 论文目录
│   └── attention_is_all_you_need.pdf    测试用论文
├── docs/
│   └── rag_interface.md                 接口文档（简版）
├── logs/
│   ├── chunk_experiment.csv             分块策略对比实验数据
│   └── self_check_report.md             交付自检报告
├── vector_store/                        Chroma 向量库持久化目录
└── src/
    ├── __init__.py
    ├── data_loader/                     模块一：文档加载
    │   ├── __init__.py
    │   └── pdf_loader.py
    ├── chunking/                        模块一：文本分块
    │   ├── __init__.py
    │   ├── chunker.py
    │   └── experiment.py
    ├── retrieval/                       模块一：检索层
    │   ├── __init__.py
    │   ├── vector_store.py              向量检索
    │   ├── bm25_retriever.py            BM25 关键词检索
    │   ├── reranker.py                  重排序
    │   └── hybrid_retriever.py          RRF 融合 + 三档检索
    └── generation/                      模块二：生成层
        ├── __init__.py                  ⭐ 对外接口（D 只需 import 这个）
        └── rag_pipeline.py              RAG 端到端流程

---

## 三、每个文件的功能说明

### 3.1 src/data_loader/pdf_loader.py
作用：加载 PDF，提取每页文本，保留页码、文件名等元数据。
关键函数：
- load_pdf(file_path) -> List[Dict]                加载单个 PDF
- load_pdfs_from_dir(dir_path) -> List[Dict]       批量加载目录下所有 PDF

返回格式示例：
[{"text": "本页正文", "page": 3, "source": "paper.pdf", "file_path": "/abs/path/paper.pdf"}, ...]

### 3.2 src/chunking/chunker.py
作用：实现 3 种文本分块策略。
关键函数：
- fixed_size_chunk(text, chunk_size=512, overlap=50)       固定大小切分
- recursive_char_chunk(text, chunk_size=512, overlap=50)   递归字符切分
- semantic_chunk(text, chunk_size=512, overlap=50)         语义切分（段落优先）
- chunk_pages(pages, method, chunk_size, overlap)          统一接口

chunk 格式示例：
{"chunk_id": "paper.pdf_p3_c0", "text": "...", "source": "paper.pdf", "page": 3, "chunk_index": 0}

### 3.3 src/chunking/experiment.py
作用：分块策略对比实验（3 种方法 x 3 种 chunk_size）。
输出：logs/chunk_experiment.csv

### 3.4 src/retrieval/vector_store.py
作用：向量检索（bge-large-zh + Chroma）。
类：VectorStore
关键方法：
- build(chunks)                 批量向量化并入库
- search(query, top_k=20)       向量相似度检索
- delete_all()                  清空 collection
- count()                       返回 chunk 数量

### 3.5 src/retrieval/bm25_retriever.py
作用：BM25 关键词检索（jieba 中文分词）。
类：BM25Retriever
关键方法：search(query, top_k=20)

### 3.6 src/retrieval/reranker.py
作用：使用 bge-reranker-base 对候选 chunk 精排。
类：Reranker
关键方法：rerank(query, candidates, top_k=5)

### 3.7 src/retrieval/hybrid_retriever.py
作用：向量 + BM25 检索，RRF 融合，Reranker 重排。
类：HybridRetriever
关键方法：
- search_vector(query, top_k)                      纯向量检索
- search_bm25(query, top_k)                        纯 BM25 检索
- search_hybrid(query, top_k)                      RRF 融合
- search_hybrid_rerank(query, top_k, recall_k=20)  完整三档链路（推荐）

### 3.8 src/generation/rag_pipeline.py
作用：RAG 端到端流程（检索 -> Prompt -> LLM 生成）。
类：RAGPipeline
关键方法：
- build_index(target, chunk_size, overlap)         加载 + 分块 + 索引
- retrieve(query, top_k=5)                         检索
- rag_answer(query, top_k=5, temperature=0.1)      完整问答

### 3.9 src/generation/__init__.py  ⭐ 重点
作用：D 唯一需要 import 的文件。
暴露 5 个模块级函数：build_index、retrieve、rag_answer、delete_document、get_sources。

---

## 四、对外接口（D 直接调用）

### 4.1 导入方式

import sys
sys.path.insert(0, "/root/autodl-tmp/rag_project")

from src.generation import (
    build_index,
    retrieve,
    rag_answer,
    delete_document,
    get_sources,
)

### 4.2 build_index(files=None, chunk_size=512, overlap=50) -> int

构建/重建索引。首次使用必须调用一次。

用法 1：默认扫描 data/ 目录
    n = build_index()

用法 2：指定文件列表
    n = build_index(["/path/to/a.pdf", "/path/to/b.pdf"])

用法 3：指定目录
    n = build_index("/root/autodl-tmp/rag_project/data")

参数：
- files：文件列表、目录路径，或 None（默认扫描 data/）
返回：构建的 chunk 数量（int）
耗时：约 15-20 秒（含模型加载）

### 4.3 retrieve(query, top_k=5) -> List[Dict]

混合检索接口（向量 + BM25 + RRF + Rerank）。

示例：
docs = retrieve("What is multi-head attention?", top_k=5)
for d in docs:
    print(d["source"], d["page"], d["rerank_score"])
    print(d["text"][:100])

返回格式：
[
    {
        "chunk_id": "paper.pdf_p4_c2",
        "text": "...",
        "source": "paper.pdf",
        "page": 4,
        "rerank_score": 0.856,
    },
    ...
]

### 4.4 rag_answer(query, top_k=5, temperature=0.1) -> Dict   ⚠️ 重点

RAG 完整问答。注意：返回的是 dict，不是元组！

正确用法：
result = rag_answer("What dataset was used for training?")
print(result["answer"])         答案字符串
print(result["sources"])        引用来源列表
print(result["total_time"])     总耗时（秒）

错误用法（会报错）：
answer, sources = rag_answer("...")

返回格式：
{
    "query": "What dataset was used for training?",
    "answer": "The standard WMT 2014 English-German dataset...",
    "sources": [
        {"source": "paper.pdf", "page": 7, "rerank_score": 0.984},
        {"source": "paper.pdf", "page": 11, "rerank_score": 0.953},
    ],
    "retrieve_time": 0.723,
    "generate_time": 1.367,
    "total_time": 2.09,
}

### 4.5 delete_document(doc_id) -> bool

从索引中删除指定文档的所有 chunk。

示例：
success = delete_document("attention_is_all_you_need.pdf")

参数：doc_id 为文件名（例如 "paper.pdf"）
返回：True（成功）/ False（未找到）

### 4.6 get_sources(answer_or_result) -> List[Dict]

从 rag_answer 的返回结果中提取引用来源。

示例：
result = rag_answer("...")
sources = get_sources(result)              传 dict
sources = get_sources(result["answer"])    传字符串

---

## 五、模型位置

| 模型 | 路径 | 用途 |
|---|---|---|
| Qwen2.5:7b | Ollama 内部（ollama list 可见） | LLM 生成 |
| bge-large-zh | /root/autodl-tmp/models/bge-large-zh/ | 文本向量化 |
| bge-reranker-base | /root/autodl-tmp/models/bge-reranker-base/ | 检索重排序 |
| Qwen GGUF | /root/autodl-tmp/models/qwen2.5/*.gguf | Ollama 底层文件 |

不要移动或删除这些模型文件。

---

## 六、环境配置（一次即可）

conda activate rag_env
export OLLAMA_MODELS=/root/autodl-tmp/models

确保 Ollama 服务在跑（每次重启实例后需要重新执行）：
nohup ollama serve > /root/autodl-tmp/ollama.log 2>&1 &
sleep 3

验证：
curl http://localhost:11434/api/tags

---

## 七、D 集成示例（直接可用）

### 7.1 Agent 的"知识库检索"工具

import sys
sys.path.insert(0, "/root/autodl-tmp/rag_project")

from src.generation import rag_answer, build_index

首次构建索引（只需一次）：
build_index()

def knowledge_base_search(query: str) -> str:
    """Agent 工具：知识库检索。输入用户问题，返回带引用的答案文本。"""
    result = rag_answer(query, top_k=5)
    lines = [result["answer"], "", "引用来源:"]
    for s in result["sources"]:
        lines.append(f"- {s['source']} 第 {s['page']} 页")
    return "\n".join(lines)

def knowledge_base_retrieve(query: str, top_k: int = 5) -> list:
    """Agent 工具：检索原始 chunk（不做 LLM 生成）。"""
    from src.generation import retrieve
    return retrieve(query, top_k=top_k)

### 7.2 在 ReAct 循环中调用

tools = {
    "knowledge_base_search": {
        "func": knowledge_base_search,
        "description": "在论文知识库中检索信息并生成带引用的答案。输入：用户问题字符串。",
    },
}

---

## 八、注意事项（重要）

1. 返回类型陷阱：rag_answer 返回 dict，不是元组。用 result["answer"] 取值，不要用元组解包。

2. 首次调用耗时：第一次调用 build_index 会加载 Embedding 和 Reranker 模型（约 5-10 秒），后续调用走缓存很快。

3. Ollama 服务依赖：rag_answer 依赖 Ollama 服务。如果报 Connection refused，执行：
   export OLLAMA_MODELS=/root/autodl-tmp/models
   nohup ollama serve > /root/autodl-tmp/ollama.log 2>&1 &

4. 索引持久化：索引存储在 /root/autodl-tmp/rag_project/vector_store/。重新调用 build_index() 会清空重建，D 不需要频繁调用。

5. data/ 目录：用户上传的 PDF 放在 /root/autodl-tmp/rag_project/data/。新增文件后需要重新调用 build_index()。

6. 系统路径：所有 from src.xxx import xxx 前，必须先 sys.path.insert(0, "/root/autodl-tmp/rag_project")，因为项目根目录不一定在 Python 搜索路径中。

7. 已知 Bad Case：pdfplumber 提取的文本存在英文单词黏连问题（如 Multi-HeadAttention 连在一起）。这是已知问题，后续可能换 pymupdf 优化，不影响接口调用。

8. 不要修改的文件：src/generation/__init__.py 是对外接口层，D 不要修改。如需扩展功能，新增独立文件或联系成员 C。

---

## 九、快速验证（复制即用）

import sys
sys.path.insert(0, "/root/autodl-tmp/rag_project")

from src.generation import build_index, retrieve, rag_answer

1. 构建索引
n = build_index()
print(f"构建了 {n} 个 chunk")

2. 检索
docs = retrieve("What is multi-head attention?", top_k=3)
print(f"检索到 {len(docs)} 条")

3. 问答
result = rag_answer("What dataset was used for training?")
print(f"答案: {result['answer'][:100]}...")
print(f"引用: {result['sources']}")
print(f"耗时: {result['total_time']}s")

期望输出：
构建了 82 个 chunk
检索到 3 条
答案: The standard WMT 2014 English-German dataset...
引用: [{'source': 'attention_is_all_you_need.pdf', 'page': 7, ...}, ...]
耗时: 2.09s

---

## 十、联系方式

接口问题：联系成员 C（RAG 后端负责人）
接口文档简版：/root/autodl-tmp/rag_project/docs/rag_interface.md
自检报告：/root/autodl-tmp/rag_project/logs/self_check_report.md

---

文档结束。祝 D 开发顺利！
