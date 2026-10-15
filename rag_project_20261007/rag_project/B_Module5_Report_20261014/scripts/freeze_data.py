"""Freeze the existing experiment records. Never runs a model or alters a source file."""
from pathlib import Path
import hashlib
import json
import shutil

OUT = Path(__file__).resolve().parents[1]
PROJECT = OUT.parent

def read(rel):
    return json.loads((PROJECT / rel).read_text(encoding="utf-8-sig"))

def rows(rel):
    return [json.loads(s) for s in (PROJECT / rel).read_text(encoding="utf-8-sig").splitlines() if s.strip()]

def main():
    data_dir = OUT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    base = "evaluation/runs/agent55_20261014_175735_da23d1"
    review = "evaluation/ai_review_20261014_191222"
    comp = "evaluation/retrieval_comparison_20261014_214329/comparison.json"
    sources = ["evaluation/qa.jsonl", "evaluation/corpus_manifest.json", comp,
               f"{base}/results.jsonl", f"{base}/metadata.json", f"{base}/qa_snapshot.jsonl",
               f"{base}/review.csv", f"{review}/scores_audit.json", f"{review}/verification.json",
               f"{review}/summary/summary.json"]
    comparison = read(comp)
    retrieval = []
    for item in comparison["inputs"]:
        run = Path(item["directory"]).name
        rel = f"evaluation/runs/{run}/results.jsonl"
        sources += [rel, f"evaluation/runs/{run}/metadata.json"]
        retrieval.extend(rows(rel))
    audit = read(f"{review}/scores_audit.json")
    provenance = {
        "frozen_on": "2026-10-14", "assessment_type": audit["assessment_type"],
        "independent_human_review": False, "agent_metadata": read(f"{base}/metadata.json"),
        "source_records": [{"path": r, "sha256": hashlib.sha256((PROJECT/r).read_bytes()).hexdigest()}
                           for r in sources],
        "scope": "Existing local experiments only; no rerun, new human study or quality optimization is implied."
    }
    result = {"qa": rows("evaluation/qa.jsonl"), "corpus": read("evaluation/corpus_manifest.json")["papers"],
              "agent": rows(f"{base}/results.jsonl"), "scores": audit["scores"],
              "retrieval": retrieval, "comparison": comparison,
              "agent_summary": read(f"{review}/summary/summary.json"), "provenance": provenance}
    # Preserve the locally verified titles, which the original manifest does not contain.
    previous = data_dir / "report_data.json"
    if previous.exists():
        titles = {r["source"]: {k: r[k] for k in ("title", "paper_id") if k in r}
                  for r in json.loads(previous.read_text(encoding="utf-8"))["corpus"]}
        for paper in result["corpus"]:
            paper.update(titles.get(paper["source"], {}))
    assert len(result["qa"]) == len(result["agent"]) == len(result["scores"]) == 55
    assert len(retrieval) == 495 and len({x['id'] for x in result['agent']}) == 55
    for x in ("qa", "agent", "scores"):
        assert {r['id'] for r in result[x]} == {r['id'] for r in result['qa']}
    assert sum(x['pages'] for x in result['corpus']) == 296
    (data_dir / "report_data.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for rel, name in [("evaluation/qa.jsonl", "qa.jsonl"), (f"{review}/scores_audit.json", "scores_audit.json"),
                      (f"{review}/verification.json", "grading_verification.json"),
                      ("evaluation/corpus_manifest.json", "corpus_manifest.json")]:
        shutil.copyfile(PROJECT / rel, data_dir / name)
    (data_dir/"source_manifest.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Frozen: 15 papers / 296 pages / 55 Agent cases / 495 retrieval rows. Sources unchanged.")

if __name__ == "__main__":
    main()
