"""Plot measured module-five summaries; never generate example results."""
import argparse
import csv
import math
from collections import Counter
from pathlib import Path


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def load_rows(paths):
    rows = []
    for filename in paths:
        path = Path(filename)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("category", "all") != "all":
                    continue
                if row.get("execution_mode", "all") != "all":
                    continue
                row["experiment"] = path.parent.name
                rows.append(row)
    return rows


def label(row):
    parts = [row["experiment"], row.get("mode", ""), row.get("method", "")]
    parts.append("chunk=" + str(row.get("chunk_size", "?")))
    return "\n".join(part for part in parts if part)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="append", required=True,
                        help="Repeat to compare baseline and optimized summary.csv files")
    parser.add_argument("--review", action="append", default=[],
                        help="Optional completed manual review.csv files")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = load_rows(args.summary)
    if not rows:
        raise SystemExit("No overall rows found; expected category=all and execution_mode=all.")
    output = Path(args.out)
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Output directory is not empty; choose a new directory.")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("Plotting requires matplotlib: python -m pip install matplotlib")
    output.mkdir(parents=True, exist_ok=True)
    generated = []

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(output / name, dpi=180, bbox_inches="tight")
        plt.close(fig)
        generated.append(name)

    retrieval = [row for row in rows if row.get("mode") == "retrieval"
                 and number(row.get("hit_at_5")) is not None]
    if retrieval:
        fig, axes = plt.subplots(1, 3, figsize=(max(12, len(retrieval) * 1.5), 5))
        for axis, key, title in zip(axes, ["hit_at_5", "mrr_at_5", "recall_at_5"],
                                   ["Hit@5", "MRR@5", "Recall@5 (document-page labels)"]):
            valid = [row for row in retrieval if number(row.get(key)) is not None]
            axis.bar(range(len(valid)), [number(row[key]) for row in valid], color="#18776f")
            axis.set_xticks(range(len(valid)), [label(row) for row in valid], fontsize=8)
            axis.set_ylim(0, 1.05)
            axis.set_title(title)
            axis.grid(axis="y", alpha=.2)
        save(fig, "01_retrieval_metrics.png")

    answers = [row for row in rows if row.get("mode") in {"rag", "agent"}]
    latency = [row for row in answers if number(row.get("avg_wall_latency_s")) is not None]
    if latency:
        fig, axis = plt.subplots(figsize=(max(8, len(latency) * 1.5), 5))
        axis.bar(range(len(latency)), [number(row["avg_wall_latency_s"]) for row in latency],
                 color="#18776f")
        axis.set_xticks(range(len(latency)), [label(row) for row in latency], fontsize=8)
        axis.set_ylabel("Mean measured request latency (seconds)")
        axis.set_title("Serial request benchmark; index construction excluded")
        save(fig, "02_answer_latency.png")

    manual = [row for row in answers if any(number(row.get(key)) is not None for key in
                                           ("correctness", "completeness", "citation_accuracy"))]
    if manual:
        fig, axes = plt.subplots(1, 3, figsize=(max(12, len(manual) * 1.5), 5))
        for axis, key in zip(axes, ["correctness", "completeness", "citation_accuracy"]):
            valid = [row for row in manual if number(row.get(key)) is not None]
            axis.bar(range(len(valid)), [number(row[key]) for row in valid], color="#3f6c98")
            axis.set_xticks(range(len(valid)), [label(row) for row in valid], fontsize=8)
            axis.set_ylim(0, 2.1)
            axis.set_title(key.replace("_", " ") + " (0-2 rubric)")
        save(fig, "03_human_scores.png")

    agents = [row for row in answers if row.get("mode") == "agent"]
    if agents:
        fig, axes = plt.subplots(1, 2, figsize=(max(10, len(agents) * 1.5), 5))
        for axis, key, title in zip(axes, ["tool_match_rate", "avg_steps"],
                                   ["Exact accepted tool-set match rate", "Mean reported execution steps"]):
            valid = [row for row in agents if number(row.get(key)) is not None]
            if valid:
                axis.bar(range(len(valid)), [number(row[key]) for row in valid], color="#18776f")
                axis.set_xticks(range(len(valid)), [label(row) for row in valid], fontsize=8)
            else:
                axis.text(.5, .5, "No measured labels", ha="center", va="center", transform=axis.transAxes)
            axis.set_title(title)
            if key == "tool_match_rate":
                axis.set_ylim(0, 1.05)
        save(fig, "04_agent_tools_and_steps.png")

    tokens = [row for row in answers if number(row.get("avg_tokens")) is not None
              and number(row.get("token_coverage")) == 1.0]
    if tokens:
        fig, axis = plt.subplots(figsize=(max(8, len(tokens) * 1.5), 5))
        axis.bar(range(len(tokens)), [number(row["avg_tokens"]) for row in tokens], color="#3f6c98")
        axis.set_xticks(range(len(tokens)), [label(row) for row in tokens], fontsize=8)
        axis.set_title("Mean measured prompt + completion tokens; coverage = 100%")
        save(fig, "05_token_usage.png")

    bad_cases = Counter()
    allowed = {"retrieval", "generation", "citation", "agent"}
    for filename in args.review:
        with Path(filename).open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("mode") not in {"rag", "agent"}:
                    continue
                categories = {item.strip() for item in row.get("bad_case", "").split(";")}
                for category in categories & allowed:
                    bad_cases[category] += 1
    if bad_cases:
        fig, axis = plt.subplots(figsize=(8, 5))
        categories = [key for key in ["retrieval", "generation", "citation", "agent"] if key in bad_cases]
        axis.bar(categories, [bad_cases[key] for key in categories], color="#a5563c")
        axis.set_ylabel("Annotated result rows (a row may have multiple labels)")
        axis.set_title("Observed bad cases; missing categories are not presumed zero")
        save(fig, "06_bad_case_counts.png")
    (output / "README.txt").write_text(
        "Inputs:\n" + "\n".join(str(Path(path).resolve()) for path in args.summary)
        + "\n\nGenerated:\n" + "\n".join(generated)
        + "\n\nMissing scores and incomplete Token coverage were not filled with zero.\n",
        encoding="utf-8")
    print("Generated:", ", ".join(generated) or "no charts; no eligible measurements")
    print("Output:", output.resolve())


if __name__ == "__main__":
    main()
