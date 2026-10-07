# RAG 后端接口文档（成员 C → 成员 D）

## 快速开始

from src.generation import build_index, retrieve, rag_answer, delete_document, get_sources

# 1. 首次构建索引（只需执行一次）
build_index()                                       # 默认扫描 data/
build_index(["/path/to/a.pdf", "/path/to/b.pdf"])   # 或指定文件列表

# 2. 检索（供 Agent 工具调用）
docs = retrieve("What is attention?", top_k=5)

# 3. RAG 问答（Agent 的核心 Tool）
result = rag_answer("What dataset was used?")
print(result["answer"])        # 答案字符串
print(result["sources"])       # [{"source", "page", "rerank_score"}, ...]

# 4. 删除文档（可选）
delete_document("paper01.pdf")

# 5. 提取引用来源（可选）
sources = get_sources(result)  # 从 rag_answer 结果中提取

## 接口详细说明

### build_index(files=None, chunk_size=512, overlap=50) -> int
构建/重建向量索引和 BM25 索引。
- files: 文件路径列表 或 目录路径；不传则默认扫描 data/
- 返回: 构建的 chunk 数量

### retrieve(query, top_k=5) -> List[Dict]
混合检索（向量 + BM25 + RRF + Rerank）。
返回: [{"chunk_id", "text", "source", "page", "rerank_score"}, ...]

### rag_answer(query, top_k=5, temperature=0.1) -> Dict
完整 RAG 流程。**注意返回的是 dict，不是元组**。
返回:
{
    "query": str,
    "answer": str,
    "sources": [{"source", "page", "rerank_score"}, ...],
    "retrieve_time": float,
    "generate_time": float,
    "total_time": float,
}

### delete_document(doc_id: str) -> bool
从索引中删除指定文档的所有 chunk。返回 True/False。

### get_sources(answer_or_result) -> List[Dict]
从 rag_answer 的返回结果（dict）或纯字符串答案中提取引用来源。

## Agent 集成示例

from src.generation import rag_answer

def knowledge_base_search(query: str) -> str:
    """Agent 工具：知识库检索"""
    result = rag_answer(query, top_k=5)
    lines = [result["answer"], "", "引用来源:"]
    for s in result["sources"]:
        lines.append("- " + s["source"] + " p" + str(s["page"]))
    return "\n".join(lines)

## 注意事项
- 首次调用会加载 Embedding 和 Reranker 模型，约 5-10 秒
- Ollama 服务必须先启动（ollama serve）
- 索引持久化在 vector_store/
- 索引数据存在后，再次调用 build_index() 会清空重建
