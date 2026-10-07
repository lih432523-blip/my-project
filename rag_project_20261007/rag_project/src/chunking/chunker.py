"""
文本分块模块
实现 3 种分块策略：
  1. fixed      - 固定字符数切分
  2. recursive  - 递归字符切分（优先段落，其次句子，最后字符）
  3. semantic   - 语义切分（基于段落/句子边界）
统一接口 chunk_pages()，输入 load_pdf 的输出，输出带元数据的 chunk 列表。
"""
import re
from typing import List, Dict


def fixed_size_chunk(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """固定字符数切分。"""
    if not text:
        return []
    chunks = []
    start = 0
    step = max(1, chunk_size - overlap)
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks


def recursive_char_chunk(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """递归字符切分：按分隔符优先级依次尝试。"""
    if not text:
        return []

    separators = ["\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ", "; ", "，", ", ", " ", ""]

    def _split(s: str, seps: List[str]) -> List[str]:
        if len(s) <= chunk_size or not seps:
            return [s.strip()] if s.strip() else []

        sep = seps[0]
        if sep == "":
            # 最后按字符硬切
            result = []
            start = 0
            step = max(1, chunk_size - overlap)
            while start < len(s):
                result.append(s[start:start + chunk_size].strip())
                if start + chunk_size >= len(s):
                    break
                start += step
            return [r for r in result if r]

        parts = s.split(sep)
        merged = []
        buf = ""
        for part in parts:
            candidate = buf + sep + part if buf else part
            if len(candidate) <= chunk_size:
                buf = candidate
            else:
                if buf:
                    merged.append(buf)
                if len(part) > chunk_size:
                    merged.extend(_split(part, seps[1:]))
                    buf = ""
                else:
                    buf = part
        if buf:
            merged.append(buf)
        return [m.strip() for m in merged if m.strip()]

    return _split(text, separators)


def semantic_chunk(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """语义切分：优先按段落边界，超长段落再按句子边界切。"""
    if not text:
        return []

    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(buf) + len(para) + 2 <= chunk_size:
            buf = buf + "\n\n" + para if buf else para
        else:
            flush()
            if len(para) > chunk_size:
                # 段落过长，按句子切
                sentences = re.split(r'(?<=[。！？.!?])\s+', para)
                sub = ""
                for s in sentences:
                    if len(sub) + len(s) + 1 <= chunk_size:
                        sub = sub + " " + s if sub else s
                    else:
                        if sub.strip():
                            chunks.append(sub.strip())
                        sub = s
                if sub.strip():
                    chunks.append(sub.strip())
            else:
                buf = para

    flush()
    return chunks


CHUNK_METHODS = {
    "fixed": fixed_size_chunk,
    "recursive": recursive_char_chunk,
    "semantic": semantic_chunk,
}


def chunk_pages(
    pages: List[Dict],
    method: str = "fixed",
    chunk_size: int = 512,
    overlap: int = 50,
) -> List[Dict]:
    """
    对 load_pdf 返回的页列表进行分块，保留元数据。

    Args:
        pages:      [{"text": ..., "page": ..., "source": ..., "file_path": ...}]
        method:     "fixed" | "recursive" | "semantic"
        chunk_size: 目标块大小（字符数）
        overlap:    相邻块重叠字符数

    Returns:
        [{"chunk_id": "xxx_p3_c0", "text": ..., "source": ..., "page": 3, "chunk_index": 0}, ...]
    """
    if method not in CHUNK_METHODS:
        raise ValueError(f"未知分块方法: {method}，可选: {list(CHUNK_METHODS.keys())}")

    chunker = CHUNK_METHODS[method]
    all_chunks = []

    for page in pages:
        sub_chunks = chunker(page["text"], chunk_size=chunk_size, overlap=overlap)
        for idx, chunk_text in enumerate(sub_chunks):
            if not chunk_text.strip():
                continue
            all_chunks.append({
                "chunk_id": f"{page['source']}_p{page['page']}_c{idx}",
                "text": chunk_text,
                "source": page["source"],
                "page": page["page"],
                "chunk_index": idx,
            })

    return all_chunks


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/root/autodl-tmp/rag_project")
    from src.data_loader.pdf_loader import load_pdfs_from_dir

    pages = load_pdfs_from_dir("/root/autodl-tmp/rag_project/data")
    print(f"\n原始页数: {len(pages)}")

    for method in ["fixed", "recursive", "semantic"]:
        chunks = chunk_pages(pages, method=method, chunk_size=512, overlap=50)
        avg_len = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
        print(f"\n[{method}] 切出 {len(chunks)} 块, 平均 {avg_len:.0f} 字符")
        if chunks:
            print(f"  首块预览: {chunks[0]['text'][:80]}...")
