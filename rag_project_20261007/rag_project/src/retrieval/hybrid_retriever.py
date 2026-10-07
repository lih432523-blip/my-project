"""
混合检索器：向量 + BM25 → RRF 融合 → Reranker 重排
"""
import sys
sys.path.insert(0, "/root/autodl-tmp/rag_project")

from typing import List, Dict, Any
from src.retrieval.vector_store import VectorStore
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.reranker import Reranker


def rrf_fusion(
    results_a: List[Dict], results_b: List[Dict], k: int = 60, top_n: int = 20
) -> List[Dict]:
    """
    倒数排名融合（Reciprocal Rank Fusion）。
    RRF score = Σ 1/(k + rank_i)
    """
    scores: Dict[str, float] = {}
    info: Dict[str, Dict] = {}

    for rank, item in enumerate(results_a):
        cid = item["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        info[cid] = item

    for rank, item in enumerate(results_b):
        cid = item["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        info.setdefault(cid, item)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    out = []
    for cid, s in ranked:
        item = dict(info[cid])
        item["rrf_score"] = s
        out.append(item)
    return out


class HybridRetriever:
    def __init__(
        self,
        chunks: List[Dict],
        vector_store: VectorStore,
        bm25_retriever: BM25Retriever,
        reranker: Reranker,
    ):
        self.chunks = chunks
        self.vs = vector_store
        self.bm25 = bm25_retriever
        self.rr = reranker

    def search_vector(self, query: str, top_k: int = 20) -> List[Dict]:
        return self.vs.search(query, top_k=top_k)

    def search_bm25(self, query: str, top_k: int = 20) -> List[Dict]:
        return self.bm25.search(query, top_k=top_k)

    def search_hybrid(self, query: str, top_k: int = 20) -> List[Dict]:
        vec = self.search_vector(query, top_k=top_k)
        bm = self.search_bm25(query, top_k=top_k)
        return rrf_fusion(vec, bm, top_n=top_k)

    def search_hybrid_rerank(self, query: str, top_k: int = 5, recall_k: int = 20) -> List[Dict]:
        candidates = self.search_hybrid(query, top_k=recall_k)
        return self.rr.rerank(query, candidates, top_k=top_k)


if __name__ == "__main__":
    from src.data_loader.pdf_loader import load_pdfs_from_dir
    from src.chunking.chunker import chunk_pages

    pages = load_pdfs_from_dir("/root/autodl-tmp/rag_project/data")
    chunks = chunk_pages(pages, method="recursive", chunk_size=512, overlap=50)
    print(f"chunks: {len(chunks)}")

    vs = VectorStore()
    vs.delete_all()
    vs.build(chunks)

    bm = BM25Retriever(chunks)
    rr = Reranker()

    hr = HybridRetriever(chunks, vs, bm, rr)

    query = "What is multi-head attention?"
    print(f"\n=== 查询: {query} ===\n")

    print("[纯向量 Top3]")
    for r in hr.search_vector(query, top_k=3):
        print(f"  [{r['score']:.3f}] {r['source']} p{r['page']}: {r['text'][:60]}...")

    print("\n[混合检索 Top3]")
    for r in hr.search_hybrid(query, top_k=3):
        print(f"  [RRF={r['rrf_score']:.4f}] {r['source']} p{r['page']}: {r['text'][:60]}...")

    print("\n[混合 + 重排 Top3]")
    for r in hr.search_hybrid_rerank(query, top_k=3):
        print(f"  [rerank={r['rerank_score']:.3f}] {r['source']} p{r['page']}: {r['text'][:60]}...")
