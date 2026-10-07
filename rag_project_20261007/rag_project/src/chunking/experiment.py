"""
分块策略对比实验
对比 3 种分块方法 × 3 种 chunk_size 的粒度指标，输出到控制台和 CSV。
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, "/root/autodl-tmp/rag_project")

from src.data_loader.pdf_loader import load_pdfs_from_dir
from src.chunking.chunker import chunk_pages


def run_experiment(pages, output_csv: str = None):
    methods = ["fixed", "recursive", "semantic"]
    chunk_sizes = [256, 512, 1024]

    rows = []
    for method in methods:
        for cs in chunk_sizes:
            chunks = chunk_pages(pages, method=method, chunk_size=cs, overlap=int(cs * 0.1))
            lengths = [len(c["text"]) for c in chunks]
            n = len(chunks)
            avg_len = sum(lengths) / n if n else 0
            min_len = min(lengths) if lengths else 0
            max_len = max(lengths) if lengths else 0
            rows.append({
                "method": method,
                "chunk_size": cs,
                "num_chunks": n,
                "avg_len": round(avg_len, 1),
                "min_len": min_len,
                "max_len": max_len,
            })

    # 控制台表格
    print("\n" + "=" * 70)
    print(f"{'方法':<12}{'chunk_size':<12}{'块数':<10}{'平均长度':<12}{'最短':<8}{'最长':<8}")
    print("-" * 70)
    for r in rows:
        print(f"{r['method']:<12}{r['chunk_size']:<12}{r['num_chunks']:<10}{r['avg_len']:<12}{r['min_len']:<8}{r['max_len']:<8}")
    print("=" * 70)

    if output_csv:
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n结果已保存: {output_csv}")

    return rows


if __name__ == "__main__":
    pages = load_pdfs_from_dir("/root/autodl-tmp/rag_project/data")
    run_experiment(pages, output_csv="/root/autodl-tmp/rag_project/logs/chunk_experiment.csv")
