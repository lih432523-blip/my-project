"""
RAG 生成层对外接口
供成员 D（Agent 开发）直接调用：
    from src.generation import build_index, retrieve, rag_answer, delete_document, get_sources
"""
import sys
sys.path.insert(0, "/root/autodl-tmp/rag_project")

from pathlib import Path
from typing import List, Dict, Any, Union

from src.generation.rag_pipeline import RAGPipeline
from src.data_loader.pdf_loader import load_pdf


_rag_instance: RAGPipeline = None
_DEFAULT_DATA_DIR = "/root/autodl-tmp/rag_project/data"


def _get_rag() -> RAGPipeline:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGPipeline()
    return _rag_instance


def build_index(files: Union[List[str], str] = None, chunk_size: int = 512, overlap: int = 50) -> int:
    """构建/更新索引。files 可以是文件列表或目录路径。返回 chunk 数量。"""
    rag = _get_rag()
    target = files if files is not None else _DEFAULT_DATA_DIR
    rag.build_index(target, chunk_size=chunk_size, overlap=overlap)
    return len(rag.chunks)


def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """混合检索接口。返回 [{"chunk_id", "text", "source", "page", "rerank_score"}, ...]"""
    return _get_rag().retrieve(query, top_k=top_k)


def rag_answer(query: str, top_k: int = 5, temperature: float = 0.1) -> Dict[str, Any]:
    """
    RAG 问答接口。返回 Dict：
        {"query", "answer", "sources": [{"source", "page", "rerank_score"}, ...],
         "retrieve_time", "generate_time", "total_time"}
    """
    return _get_rag().rag_answer(query, top_k=top_k, temperature=temperature)


def delete_document(doc_id: str) -> bool:
    """
    从索引中删除指定文档的所有 chunk。
    doc_id 可以是文件名（如 "attention_is_all_you_need.pdf"）或 chunk_id 前缀。

    返回 True 表示删除成功，False 表示未找到。
    """
    rag = _get_rag()
    if rag.vs is None or rag.chunks is None:
        return False

    # 找出属于该文档的所有 chunk_id
    target_ids = [c["chunk_id"] for c in rag.chunks if c["source"] == doc_id]
    if not target_ids:
        return False

    # 从 Chroma 删
    try:
        rag.vs.collection.delete(ids=target_ids)
    except Exception as e:
        print(f"[delete_document] Chroma 删除失败: {e}")
        return False

    # 从内存中的 chunks 删
    rag.chunks = [c for c in rag.chunks if c["source"] != doc_id]

    # 重建 BM25 和 HybridRetriever
    from src.retrieval.bm25_retriever import BM25Retriever
    from src.retrieval.hybrid_retriever import HybridRetriever
    rag.bm25 = BM25Retriever(rag.chunks)
    rag.hybrid = HybridRetriever(rag.chunks, rag.vs, rag.bm25, rag.rr)

    return True


def get_sources(answer_or_result: Union[str, Dict]) -> List[Dict[str, Any]]:
    """
    从 rag_answer 的返回结果中提取引用来源。
    传 Dict 时直接取 sources 字段；传字符串时做简单解析。
    """
    if isinstance(answer_or_result, dict):
        return answer_or_result.get("sources", [])

    # 传字符串时，尝试正则解析 [来源: xxx pN]
    import re
    pattern = r"\[来源[:：]\s*([^\s]+)\s*p(\d+)\]"
    matches = re.findall(pattern, str(answer_or_result))
    return [{"source": m[0], "page": int(m[1]), "rerank_score": None} for m in matches]


__all__ = [
    "build_index", "retrieve", "rag_answer", "delete_document", "get_sources",
    "RAGPipeline",
]
