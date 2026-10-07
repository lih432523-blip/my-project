"""
向量检索模块
封装 bge-large-zh + Chroma，提供 build / search / delete 接口。
"""
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer


class VectorStore:
    def __init__(
        self,
        model_path: str = "/root/autodl-tmp/models/bge-large-zh",
        persist_dir: str = "/root/autodl-tmp/rag_project/vector_store",
        collection_name: str = "papers",
        device: str = "cpu",
    ):
        self.model = SentenceTransformer(model_path, device=device)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def build(self, chunks: List[Dict], batch_size: int = 64):
        """批量向量化并写入 Chroma。chunks 需含 chunk_id / text / source / page。"""
        if not chunks:
            return
        texts = [c["text"] for c in chunks]
        ids = [c["chunk_id"] for c in chunks]
        metadatas = [{"source": c["source"], "page": c["page"]} for c in chunks]

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            embs = self.model.encode(batch_texts, normalize_embeddings=True).tolist()
            self.collection.add(embeddings=embs, documents=batch_texts, metadatas=batch_metas, ids=batch_ids)

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        q_emb = self.model.encode([query], normalize_embeddings=True).tolist()
        results = self.collection.query(query_embeddings=q_emb, n_results=top_k)
        out = []
        for i in range(len(results["ids"][0])):
            out.append({
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "source": results["metadatas"][0][i]["source"],
                "page": results["metadatas"][0][i]["page"],
                "score": 1 - results["distances"][0][i],  # cosine distance -> similarity
            })
        return out

    def delete_all(self):
        """清空 collection（重建索引时用）。"""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/root/autodl-tmp/rag_project")
    from src.data_loader.pdf_loader import load_pdfs_from_dir
    from src.chunking.chunker import chunk_pages

    pages = load_pdfs_from_dir("/root/autodl-tmp/rag_project/data")
    chunks = chunk_pages(pages, method="recursive", chunk_size=512, overlap=50)
    print(f"chunks: {len(chunks)}")

    vs = VectorStore()
    vs.delete_all()          # 清空重建（首次运行可保留）
    vs.build(chunks)
    print(f"Chroma 中 chunk 数: {vs.count()}")

    res = vs.search("What is the attention mechanism?", top_k=3)
    print("\n--- 查询: What is the attention mechanism? ---")
    for r in res:
        print(f"[{r['score']:.3f}] {r['source']} p{r['page']}: {r['text'][:80]}...")
