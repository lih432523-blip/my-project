"""
PDF 文档加载器
使用 pdfplumber 提取每页文本，保留页码、源文件名等元数据，供后续引用溯源使用。
"""
import os
from pathlib import Path
from typing import List, Dict
import pdfplumber


def load_pdf(file_path: str) -> List[Dict]:
    """
    加载单个 PDF 文件，返回每页的文本和元数据。

    Args:
        file_path: PDF 文件路径

    Returns:
        列表，每个元素形如：
        {
            "text": "本页正文",
            "page": 3,
            "source": "paper.pdf",
            "file_path": "/abs/path/paper.pdf",
        }
    """
    file_path = str(Path(file_path).resolve())
    source_name = os.path.basename(file_path)
    pages = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if not text:
                    continue
                pages.append({
                    "text": text,
                    "page": i + 1,
                    "source": source_name,
                    "file_path": file_path,
                })
    except Exception as e:
        print(f"[ERROR] 解析 PDF 失败: {file_path}, 原因: {e}")

    return pages


def load_pdfs_from_dir(dir_path: str) -> List[Dict]:
    """
    批量加载目录下所有 PDF 文件。
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在: {dir_path}")

    all_pages = []
    pdf_files = sorted(dir_path.glob("*.pdf"))

    if not pdf_files:
        print(f"[WARN] 目录下没有 PDF 文件: {dir_path}")
        return []

    print(f"[INFO] 发现 {len(pdf_files)} 个 PDF 文件")
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"[{idx}/{len(pdf_files)}] 解析 {pdf_file.name} ...")
        pages = load_pdf(str(pdf_file))
        all_pages.extend(pages)
        print(f"    提取 {len(pages)} 页")

    print(f"[INFO] 共提取 {len(all_pages)} 页文本")
    return all_pages


if __name__ == "__main__":
    import sys
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "/root/autodl-tmp/rag_project/data"
    pages = load_pdfs_from_dir(test_dir)

    if pages:
        print("\n--- 前 2 页预览 ---")
        for p in pages[:2]:
            print(f"\n[来源: {p['source']} | 第 {p['page']} 页]")
            print(p["text"][:300])
            print("...")
