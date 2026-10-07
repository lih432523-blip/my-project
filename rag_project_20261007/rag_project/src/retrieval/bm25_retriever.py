"""
BM25 关键词检索
使用 rank_bm25 + jieba 中文分词（英文文本用空格切分即可）。
"""
import re
from typing import List, Dict, Any
import jieba
from rank_bm25 import BM25Okapi


def simple_tokenize(text: str) -> List[str]:
    """混合分词：中文用 jieba，英文/数字按空格和标点切。"""
    # 先按空白切分，保留英文单词
    tokens = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", text)
    out = []
    for t in tokens:
        if re.match(r"[\u4e00-\u9fff]+", t):
            out.extend(jieba.lcut(t))
        else:
            out.append(t.lower())
    return out


class BM25Retriever:
    def __init__(self, chunks: List[Dict]):
        """
        chunks: [{"chunk_id": ..., "text": ..., "source": ..., "page": ...}, ...]
        """
        self.chunks = chunks
        self.corpus = [simple_tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(self.corpus)

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        tokens = simple_tokenize(query)
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        out = []
        for i in ranked:
            c = self.chunks[i]
            out.append({
                "chunk_id": c["chunk_id"],
                "text": c["text"],
                "source": c["source"],
                "page": c["page"],
                "score": float(scores[i]),
            })
        return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/root/autodl-tmp/rag_project")
    from src.data_loader.pdf_loader import load_pdfs_from_dir
    from src.chunking.chunker import chunk_pages

    pages = load_pdfs_from_dir("/root/autodl-tmp/rag_project/data")
    chunks = chunk_pages(pages, method="recursive", chunk_size=512, overlap=50)

    bm25 = BM25Retriever(chunks)
    res = bm25.search("multi-head attention", top_k=3)
    print("\n--- BM25 查询: multi-head attention ---")
    for r in res:
        print(f"[{r['score']:.2f}] {r['source']} p{r['page']}: {r['text'][:80]}...")
