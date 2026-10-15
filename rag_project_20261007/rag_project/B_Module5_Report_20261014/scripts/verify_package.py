"""Validate the delivered artifacts. Optional: --check-original also checks source hashes."""
import argparse
from pathlib import Path
import hashlib
import json
import re
from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]
args = argparse.ArgumentParser()
args.add_argument("--check-original", action="store_true")
opts = args.parse_args()
data = json.loads((root / "data/report_data.json").read_text(encoding="utf-8"))
source = (root / "main.tex").read_text(encoding="utf-8")
figures = re.findall(r"\\fig\{([^}]+)\}", source)
tables = re.findall(r"\\input\{(tables/[^}]+)\}", source)
assert len(figures) == 8 and len(tables) == 7
for figure in figures:
    for ext in ("pdf", "png"):
        assert (root / "figures" / f"{figure}.{ext}").is_file()
    assert len(PdfReader(root / "figures" / f"{figure}.pdf").pages) == 1
for table in tables:
    assert (root / table).is_file()
pdf = PdfReader(root / "main.pdf")
text = "\n".join(page.extract_text() or "" for page in pdf.pages)
assert "??" not in text, "Unresolved PDF reference"
assert "南京农业大学" in text and "AI" in text
assert "scripts\\module5_eval.py validate" not in source
assert all(q["id"] in text for q in data["qa"])
assert len(data["qa"]) == len(data["agent"]) == len(data["scores"]) == 55
assert len(data["retrieval"]) == 495 and len(data["corpus"]) == 15
assert sum(p["pages"] for p in data["corpus"]) == 296
assert sum(not r["success"] for r in data["agent"]) == 2
assert data["provenance"]["independent_human_review"] is False
original_check = None
if opts.check_original:
    for item in data["provenance"]["source_records"]:
        p = root.parent / item["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"], str(p)
    original_check = True
log = root / "main.log"
overfull = None
if log.exists():
    overfull = len(re.findall(r"Overfull \\[hv]box", log.read_text(encoding="utf-8", errors="replace")))
    assert overfull == 0
result = {"status": "passed", "report_pages": len(pdf.pages), "figures": 8,
          "figure_formats": ["vector PDF", "240dpi PNG"], "table_fragments": 7,
          "qa": 55, "retrieval_rows": 495, "corpus_papers": 15, "physical_pages": 296,
          "agent_failures_retained": 2, "unresolved_references": False,
          "overfull_boxes": overfull, "original_source_hashes_unchanged": original_check,
          "independent_human_review": False, "compile_engine": "Tectonic 0.17.0 (XeTeX)"}
(root / "data/delivery_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
