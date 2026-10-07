"""
RAG 生成层
串联 检索层（向量+BM25+RRF+Rerank） 与 Ollama LLM，产出带引用溯源的答案。
"""
import sys
sys.path.insert(0, "/root/autodl-tmp/rag_project")

import time
from typing import List, Dict, Any
import ollama

from src.data_loader.pdf_loader import load_pdfs_from_dir
from src.chunking.chunker import chunk_pages
from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.reranker import Reranker
from src.retrieval.hybrid_retriever import HybridRetriever


# ---------- Prompt 模板 ----------
RAG_SYSTEM_PROMPT = """你是一个严谨的科研助理。请严格基于用户提供的文献片段回答问题。

规则：
1. 只使用【文献片段】中的信息作答，不要编造。
2. 在答案末尾用 [来源: 文件名 p页码] 的格式标注引用。
3. 如果文献片段中没有相关信息，明确回复"当前知识库中未找到相关文档"。
4. 回答要简洁、准确、有逻辑。
"""


def build_prompt(query: str, contexts: List[Dict[str, Any]]) -> str:
    """把检索到的 chunks 拼成上下文，与问题一起构造 prompt。"""
    context_parts = []
    for i, c in enumerate(contexts, 1):
        context_parts.append(
            f"[片段 {i}] 来源: {c['source']} 第 {c['page']} 页\n{c['text']}"
        )
    context_text = "\n\n".join(context_parts)

    prompt = f"""【文献片段】
{context_text}

【问题】
{query}

请基于以上文献片段回答问题，并在末尾标注引用来源。
"""
    return prompt


class RAGPipeline:
    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        vector_store: VectorStore = None,
        bm25_retriever: BM25Retriever = None,
        reranker: Reranker = None,
    ):
        self.model_name = model_name
        self.vs = vector_store or VectorStore()
        self.bm25 = bm25_retriever
        self.rr = reranker or Reranker()
        self.hybrid = None
        self.chunks = None

    def build_index(self, target, chunk_size: int = 512, overlap: int = 50):
        """
        加载 PDF → 分块 → 向量化入库 → 构建 BM25 索引。

        Args:
            target: 目录路径（str）或 PDF 文件路径列表（list）
        """
        from pathlib import Path

        # 兼容两种情况：目录 或 文件列表
        if isinstance(target, (list, tuple)):
            pages = []
            for f in target:
                if str(f).lower().endswith(".pdf"):
                    pages.extend(load_pdf(str(f)))
        else:
            target_path = Path(target)
            if target_path.is_dir():
                pages = load_pdfs_from_dir(str(target_path))
            elif target_path.is_file():
                pages = load_pdf(str(target_path))
            else:
                raise FileNotFoundError(f"路径不存在: {target}")

        print(f"[RAG] 分块 (method=recursive, size={chunk_size})")
        self.chunks = chunk_pages(pages, method="recursive", chunk_size=chunk_size, overlap=overlap)
        print(f"[RAG] 生成 {len(self.chunks)} 个 chunk")

        print("[RAG] 向量化 + 写入 Chroma")
        self.vs.delete_all()
        self.vs.build(self.chunks)
        print(f"[RAG] Chroma 中 chunk 数: {self.vs.count()}")

        print("[RAG] 构建 BM25 索引")
        self.bm25 = BM25Retriever(self.chunks)
        self.hybrid = HybridRetriever(self.chunks, self.vs, self.bm25, self.rr)
        print("[RAG] 索引构建完成")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索接口，供 Agent 调用。"""
        if self.hybrid is None:
            raise RuntimeError("请先调用 build_index()")
        return self.hybrid.search_hybrid_rerank(query, top_k=top_k, recall_k=20)

    def rag_answer(self, query: str, top_k: int = 5, temperature: float = 0.1) -> Dict:
        """
        完整 RAG 流程：检索 → 构造 prompt → 调用 LLM → 返回答案 + 来源。
        """
        t0 = time.time()
        contexts = self.retrieve(query, top_k=top_k)
        retrieve_time = time.time() - t0

        if not contexts:
            return {
                "query": query,
                "answer": "当前知识库中未找到相关文档。",
                "sources": [],
                "retrieve_time": retrieve_time,
                "generate_time": 0,
            }

        prompt = build_prompt(query, contexts)

        t1 = time.time()
        response = ollama.chat(
            model=self.model_name,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": temperature},
        )
        answer = response["message"]["content"]
        generate_time = time.time() - t1

        sources = [
            {"source": c["source"], "page": c["page"], "rerank_score": c.get("rerank_score", 0)}
            for c in contexts
        ]

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "retrieve_time": round(retrieve_time, 3),
            "generate_time": round(generate_time, 3),
            "total_time": round(retrieve_time + generate_time, 3),
        }


if __name__ == "__main__":
    rag = RAGPipeline()

    # 首次运行需要建索引；之后可注释掉
    rag.build_index("/root/autodl-tmp/rag_project/data")

    # 测试三个不同问题
    queries = [
        "What is multi-head attention?",
        "What dataset was used for training?",
        "这篇论文的作者是谁？",  # 测试中文问题
    ]

    for q in queries:
        print("\n" + "=" * 70)
        print(f"❓ 问题: {q}")
        result = rag.rag_answer(q, top_k=5)
        print(f"\n💡 答案:\n{result['answer']}")
        print(f"\n📚 引用来源:")
        for s in result["sources"]:
            print(f"   - {s['source']} p{s['page']} (rerank={s['rerank_score']:.3f})")
        print(f"\n⏱  检索 {result['retrieve_time']}s + 生成 {result['generate_time']}s = {result['total_time']}s")
