"""
Reranker 重排序模块
使用 bge-reranker-base 对候选 chunk 精排。
"""
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(
        self,
        model_path: str = "/root/autodl-tmp/models/bge-reranker-base",
        device: str = "cpu",
    ):
        self.model = CrossEncoder(model_path, device=device)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        pairs = [[query, c["text"]] for c in candidates]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)[:top_k]
        out = []
        for c, s in ranked:
            item = dict(c)
            item["rerank_score"] = float(s)
            out.append(item)
        return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/root/autodl-tmp/rag_project")
    from src.data_loader.pdf_loader import load_pdfs_from_dir
    from src.chunking.chunker import chunk_pages

    pages = load_pdfs_from_dir("/root/autodl-tmp/rag_project/data")
    chunks = chunk_pages(pages, method="recursive", chunk_size=512, overlap=50)

    rr = Reranker()
    res = rr.rerank("attention mechanism", chunks[:20], top_k=3)
    print("\n--- Rerank 前 3 ---")
    for r in res:
        print(f"[{r['rerank_score']:.3f}] {r['source']} p{r['page']}: {r['text'][:80]}...")
