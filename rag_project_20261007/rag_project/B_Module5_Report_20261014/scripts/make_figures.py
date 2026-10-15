"""Rebuild the eight report figures from the frozen, portable JSON dataset.

Usage: python scripts/make_figures.py
Requires Python 3.10+, numpy and matplotlib. No models, network calls or source
project checkout are needed. The data directory travels with this report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
from matplotlib.ticker import PercentFormatter, ScalarFormatter

BASE = Path(__file__).resolve().parents[1]
NAVY, TEAL, BLUE, OCHRE, CRIMSON = "#18354A", "#168577", "#507FAC", "#BE8D36", "#B64B56"
INK, MUTED, GRID, PALE = "#263A49", "#647381", "#DCE3E8", "#F3F6F8"
CATS = ("factual", "comparison", "summary", "reasoning")
CAT_LABEL = {"factual": "Factual", "comparison": "Comparison", "summary": "Summary", "reasoning": "Reasoning"}
METHODS = ("vector", "hybrid", "hybrid_rerank")
METHOD_LABEL = {"vector": "Vector", "hybrid": "Hybrid", "hybrid_rerank": "Hybrid + rerank"}
METHOD_SHORT = {"vector": "V", "hybrid": "H", "hybrid_rerank": "H+R"}
METHOD_COLOR = {"vector": NAVY, "hybrid": BLUE, "hybrid_rerank": TEAL}
CHUNKS = (256, 512, 1024)
CHUNK_COLOR = {256: BLUE, 512: TEAL, 1024: OCHRE}
SCORE_FIELDS = ("correctness", "completeness", "citation_accuracy")
SCORE_LABEL = {"correctness": "Correctness", "completeness": "Completeness", "citation_accuracy": "Citation support"}
ERRORS = ("retrieval", "generation", "citation", "agent")
ERROR_LABEL = {"retrieval": "Retrieval", "generation": "Generation", "citation": "Citation", "agent": "Agent"}
HEAT = LinearSegmentedColormap.from_list("report_teal", ["#F4F7F8", "#9BCDC5", TEAL, NAVY])
HAS_CJK = False


def setup_style():
    global HAS_CJK
    for name in ("msyh.ttc", "msyhbd.ttc"):
        candidate = Path("C:/Windows/Fonts") / name
        if candidate.exists():
            font_manager.fontManager.addfont(str(candidate))
            HAS_CJK = True
    plt.rcParams.update({
        "font.family": ["DejaVu Sans", "Microsoft YaHei"] if HAS_CJK else ["DejaVu Sans"],
        "font.size": 7.3, "axes.titlesize": 8.2, "axes.titleweight": "semibold",
        "axes.labelsize": 7.3, "axes.labelcolor": INK, "text.color": INK,
        "axes.edgecolor": GRID, "axes.linewidth": .65,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 6.6,
        "ytick.labelsize": 6.6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "grid.color": GRID, "grid.linewidth": .5, "axes.spines.top": False,
        "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "pdf.fonttype": 42, "ps.fonttype": 42,
        "axes.unicode_minus": False, "legend.frameon": False,
    })


def figure(title, subtitle, height=11.2):
    fig = plt.figure(figsize=(16.8 / 2.54, height / 2.54))
    fig.text(.065, .96, title, fontsize=11, fontweight="bold", color=NAVY, va="top")
    fig.text(.065, .912, subtitle, fontsize=7.1, color=MUTED, va="top")
    return fig


def panel(ax, letter, title):
    ax.set_title(f"{letter}   {title}", loc="left", pad=10, color=NAVY)


def note(fig, text):
    fig.text(.065, .032, text, fontsize=6.4, color=MUTED, va="bottom", linespacing=1.4)


def tidy(ax, direction="x"):
    ax.set_axisbelow(True)
    ax.grid(axis=direction, alpha=.8)


def annotate_matrix(ax, array, fmt="d", max_value=None, fontsize=6.6):
    maximum = max_value if max_value is not None else max(1, float(np.nanmax(array)))
    for i in range(array.shape[0]):
        for j in range(array.shape[1]):
            value = array[i, j]
            label = format(int(value), fmt) if fmt == "d" else format(value, fmt)
            ax.text(j, i, label, ha="center", va="center", fontsize=fontsize,
                    color="white" if value > .57 * maximum else INK)


def matrix_plot(ax, array, cmap=HEAT, vmin=0, vmax=None):
    """Keep every heatmap cell vector-native in the PDF export."""
    rows, columns = array.shape
    mesh = ax.pcolormesh(np.arange(columns + 1) - .5, np.arange(rows + 1) - .5,
                         array, cmap=cmap, vmin=vmin, vmax=vmax,
                         shading="flat", edgecolors="none", rasterized=False)
    ax.set_xlim(-.5, columns - .5); ax.set_ylim(rows - .5, -.5)
    return mesh


def group_retrieval(data):
    grouped = defaultdict(list)
    for row in data["retrieval"]:
        grouped[(int(row["chunk_size"]), row["method"])].append(row)
    expected = {(chunk, method) for chunk in CHUNKS for method in METHODS}
    if set(grouped) != expected:
        raise ValueError("Expected all 9 chunk-size/retrieval configurations.")
    n = len(data["qa"])
    for key, rows in grouped.items():
        if len(rows) != n or len({r["id"] for r in rows}) != n:
            raise ValueError(f"Incomplete/duplicate question IDs for {key}")
    return grouped


def dataset_profile(data):
    fig = figure("Dataset profile", "Frozen questions, annotated evidence and the complete PDF corpus", 12.3)
    ax = fig.add_axes([.145, .36, .205, .40])
    heat = fig.add_axes([.65, .18, .27, .62])
    counts = Counter(row["category"] for row in data["qa"])
    y = np.arange(4)
    ax.barh(y, [counts[c] for c in CATS], color=[NAVY, BLUE, TEAL, OCHRE], height=.56)
    ax.set_yticks(y, [CAT_LABEL[c] for c in CATS])
    ax.invert_yaxis(); ax.set_xlim(0, max(counts.values()) * 1.28)
    ax.set_xlabel("Questions"); tidy(ax)
    for i, cat in enumerate(CATS):
        ax.text(counts[cat] + .5, i, str(counts[cat]), va="center", fontsize=8, fontweight="bold")
    panel(ax, "A", "Question mix")
    fig.text(.145, .205, f"{len(data['qa'])} questions\n{len(data['corpus'])} papers", fontsize=11,
             color=NAVY, fontweight="bold", linespacing=1.6, va="center")
    coverage = np.zeros((len(data["corpus"]), 4), dtype=int)
    for i, paper in enumerate(data["corpus"]):
        for row in data["qa"]:
            if paper["source"] in {e["source"] for e in row["gold_evidence"]}:
                coverage[i, CATS.index(row["category"])] += 1
    short = ["Video-LLaVA", "Vision Mamba", "ViT", "Post-disaster perception", "Transformer", "ResNet",
             "SBRF-Det / dental", "Thermal image fusion", "Cone manipulation", "Watermelon size",
             "Segmentation methods", "Foundation model benchmark", "Tooth segmentation", "Water monitoring", "Xiangyunsha defects"]
    labels = [f"{p.get('paper_id', f'P{i+1:02d}')}  {short[i]}" for i, p in enumerate(data["corpus"])]
    im = matrix_plot(heat, coverage, vmax=max(1, coverage.max()))
    heat.set_yticks(range(len(labels)), labels, fontsize=6.0)
    heat.set_xticks(range(4), ["Fact.", "Comp.", "Summ.", "Reason."], rotation=35, ha="right")
    heat.tick_params(length=0); annotate_matrix(heat, coverage, fontsize=5.9)
    panel(heat, "B", "Gold-evidence coverage")
    cax = fig.add_axes([.94, .18, .010, .62])
    fig.colorbar(im, cax=cax, ticks=range(int(coverage.max()) + 1))
    cax.set_title("QA", fontsize=6.1, pad=5)
    note(fig, "Cells count questions whose gold evidence includes the paper; paper assignments can overlap.\nEvidence labels refer to the PDF filename and one-based physical page.")
    return fig


def retrieval_quality(data):
    fig = figure("Retrieval quality across nine configurations", "Same 55 questions and corpus; recursive character chunks; recall pool 20, final top 5", 11.0)
    grouped = group_retrieval(data)
    configurations = [(chunk, method) for chunk in CHUNKS for method in METHODS]
    axes = [fig.add_axes([.20 + i * .255, .20, .225, .59]) for i in range(3)]
    for ax, metric, title in zip(axes, ("hit_at_5", "mrr_at_5", "recall_at_5"), ("Hit@5", "MRR@5", "Recall@5")):
        values = [np.mean([r[metric] for r in grouped[c]]) for c in configurations]
        ax.axhspan(4.58, 5.42, color=TEAL, alpha=.08, zorder=0)
        ax.barh(range(9), values, color=[METHOD_COLOR[m] for _, m in configurations], height=.59)
        ax.set_xlim(0, 1.04); ax.set_ylim(8.6, -.6); ax.set_xticks([0, .5, 1]); tidy(ax)
        ax.set_yticks(range(9))
        if ax is axes[0]:
            ax.set_yticklabels([f"{c}   {METHOD_SHORT[m]}" for c, m in configurations], fontsize=7)
            ax.set_ylabel("Chunk characters / method", labelpad=10)
        else:
            ax.set_yticklabels([])
        for y, value in enumerate(values):
            ax.text(value + .025, y, f"{value:.3f}", va="center", fontsize=6.2)
        for boundary in (2.5, 5.5): ax.axhline(boundary, color=GRID, lw=.8)
        ax.set_title(title, loc="left", color=NAVY)
    fig.legend(handles=[Patch(color=METHOD_COLOR[m], label=METHOD_LABEL[m]) for m in METHODS],
               ncol=3, loc="lower center", bbox_to_anchor=(.52, .085), fontsize=7)
    note(fig, "Each bar is the mean over 55 paired questions. Shading marks the 512-character + rerank configuration.\nGold matching unit: paper + physical PDF page. These metrics do not measure answer correctness.")
    return fig


def retrieval_tradeoff(data):
    fig = figure("Quality, latency and index cardinality", "Query latency includes retrieval only; no LLM generation or index-build timing", 11.4)
    grouped = group_retrieval(data)
    ax = fig.add_axes([.11, .26, .52, .51]); bar = fig.add_axes([.75, .26, .20, .51])
    markers = {"vector": "o", "hybrid": "s", "hybrid_rerank": "D"}
    offsets = {(256, "vector"): (12, -15), (256, "hybrid"): (5, 6), (256, "hybrid_rerank"): (5, 7),
               (512, "vector"): (-29, 5), (512, "hybrid"): (-30, -13), (512, "hybrid_rerank"): (-26, 8),
               (1024, "vector"): (15, 6), (1024, "hybrid"): (7, 7), (1024, "hybrid_rerank"): (-27, 7)}
    for (chunk, method), rows in grouped.items():
        latency = np.mean([r["wall_latency_s"] for r in rows]); recall = np.mean([r["recall_at_5"] for r in rows])
        ax.scatter(latency, recall, s=36, color=CHUNK_COLOR[chunk], marker=markers[method], edgecolors="white", linewidths=.6, zorder=3)
        ax.annotate(f"{chunk} {METHOD_SHORT[method]}", (latency, recall), xytext=offsets[(chunk, method)],
                    textcoords="offset points", fontsize=5.5, color=CHUNK_COLOR[chunk])
    ax.set_xscale("log"); ax.set_xlim(.11, 4.9); ax.set_ylim(.54, .77)
    ax.set_xticks([.15, .3, .6, 1.2, 2.4, 4.8]); ax.get_xaxis().set_major_formatter(ScalarFormatter())
    ax.set_xlabel("Mean query latency (seconds; log scale)"); ax.set_ylabel("Mean Recall@5"); tidy(ax, "both")
    panel(ax, "A", "Measured quality-latency tradeoff")
    inputs = {int(row["chunk_size"]): row for row in data["comparison"]["inputs"]}
    counts = [inputs[c]["chunk_count"] for c in CHUNKS]
    bar.bar(range(3), counts, color=[CHUNK_COLOR[c] for c in CHUNKS], width=.57)
    bar.set_xticks(range(3), [str(c) for c in CHUNKS]); bar.set_ylim(0, max(counts) * 1.25)
    bar.set_xlabel("Chunk characters"); bar.set_ylabel("Stored chunks", labelpad=4); tidy(bar, "y")
    for x, count in enumerate(counts): bar.text(x, count + max(counts) * .035, f"{count:,}", ha="center", fontsize=6.6)
    panel(bar, "B", "Index size")
    fig.legend(handles=[Line2D([], [], color=MUTED, marker=markers[m], linestyle="", markersize=5, label=METHOD_LABEL[m]) for m in METHODS],
               loc="lower center", bbox_to_anchor=(.50, .11), ncol=3, fontsize=6.9)
    note(fig, "The 512-character run reuses a validated index; 256 and 1024 rebuild embeddings.\nIndex cardinality is comparable; index-build duration is deliberately not compared.")
    return fig


def paired_hits(data):
    fig = figure("Paired question-level retrieval outcomes", "All configurations evaluated against the identical gold evidence on 55 questions", 10.4)
    grouped = group_retrieval(data)
    qa = sorted(data["qa"], key=lambda r: (CATS.index(r["category"]), r["id"]))
    ids = [q["id"] for q in qa]
    configurations = [(c, m) for c in CHUNKS for m in METHODS]
    matrix = np.array([[{r["id"]: r for r in grouped[(c, m)]}[identifier]["hit_at_5"] for identifier in ids] for c, m in configurations])
    ax = fig.add_axes([.16, .24, .79, .48])
    matrix_plot(ax, matrix, cmap=ListedColormap(["#E9EEF1", TEAL]), vmin=0, vmax=1)
    labels = [f"{c} {METHOD_SHORT[m]}  ({int(matrix[i].sum())}/55)" for i, (c, m) in enumerate(configurations)]
    ax.set_yticks(range(9), labels, fontsize=6.5); ax.set_xticks(range(len(ids)), ids, rotation=90, fontsize=5.1)
    ax.tick_params(length=0, pad=3)
    for boundary in (2.5, 5.5): ax.axhline(boundary, color="white", lw=2)
    start = 0
    for cat in CATS:
        count = sum(q["category"] == cat for q in qa)
        if start: ax.axvline(start - .5, color="white", lw=2)
        ax.text((start + (count - 1) / 2) / len(ids), 1.07, f"{CAT_LABEL[cat]} (n={count})", transform=ax.transAxes,
                ha="center", fontsize=6.6, color=NAVY)
        start += count
    fig.legend(handles=[Patch(color=TEAL, label="Hit: any gold page in top 5"), Patch(color="#E9EEF1", label="Miss")],
               ncol=2, loc="lower center", bbox_to_anchor=(.56, .09), fontsize=7)
    note(fig, "Each column is one frozen question; each row is one retrieval configuration.\nRepeated chunks from a single page cannot increase evidence-page Recall@5.")
    return fig


def agent_performance(data):
    rows = data["agent"]; failures = [r for r in rows if r.get("success") is False]
    latency = np.array([r["wall_latency_s"] for r in rows], dtype=float)
    fig = figure("Agent execution cost and reliability", f"{len(rows)} questions | {len(rows)-len(failures)} completed successfully | {len(failures)} execution failures", 11.9)
    left = fig.add_axes([.10, .25, .37, .52]); right = fig.add_axes([.60, .25, .35, .52])
    groups = [[r["wall_latency_s"] for r in rows if r["category"] == c] for c in CATS]
    bp = left.boxplot(groups, widths=.49, patch_artist=True, showfliers=False,
                      medianprops={"color": NAVY, "linewidth": 1.3}, whiskerprops={"color": MUTED}, capprops={"color": MUTED})
    for patch in bp["boxes"]: patch.set(facecolor="#DDE9EF", edgecolor=BLUE, linewidth=.8)
    rng = np.random.default_rng(12)
    for i, cat in enumerate(CATS, 1):
        subset = [r for r in rows if r["category"] == cat]
        jitter = rng.uniform(-.13, .13, len(subset))
        for delta, row in zip(jitter, subset):
            failed = row.get("success") is False
            left.scatter(i + delta, row["wall_latency_s"], s=22 if failed else 11,
                         marker="x" if failed else "o", c=CRIMSON if failed else BLUE,
                         linewidths=1 if failed else 0, alpha=1 if failed else .62, zorder=3)
            if failed: left.annotate(row["id"], (i + delta, row["wall_latency_s"]), xytext=(4, 3), textcoords="offset points", fontsize=5.6, color=CRIMSON)
    left.set_xticks(range(1, 5), [f"{label}\n(n={len(g)})" for label, g in zip(["Fact.", "Comp.", "Summ.", "Reason."], groups)])
    left.set_ylabel("Wall-clock latency (seconds)"); left.set_ylim(0, latency.max() * 1.15); tidy(left, "y")
    panel(left, "A", "Latency by question category")
    modes = {"direct_tool": (NAVY, "s", "Direct tool"), "react": (TEAL, "o", "ReAct")}
    measured = 0
    for row in rows:
        usage = row.get("token_usage", {})
        if not usage.get("complete") or not isinstance(usage.get("total_tokens"), (int, float)):
            continue
        measured += 1
        color, marker, _ = modes.get(row.get("execution_mode"), (BLUE, "o", "Other"))
        x = usage["total_tokens"] / 1000; y = row["wall_latency_s"]
        right.scatter(x, y, c=color, marker=marker, s=23, alpha=.8, edgecolors="white", linewidths=.35)
        if row.get("success") is False:
            right.scatter(x, y, c=CRIMSON, marker="x", s=40, linewidths=1.1, zorder=4)
            right.annotate(row["id"], (x, y), xytext=(4, -9), textcoords="offset points", fontsize=5.6, color=CRIMSON)
    right.set_xlabel("Measured total tokens (thousands)"); right.set_ylabel("Wall-clock latency (seconds)")
    right.set_ylim(0, latency.max() * 1.15); tidy(right, "both"); panel(right, "B", "Token use and execution mode")
    handles = [Line2D([], [], color=c, marker=marker, linestyle="", markersize=4.5, label=label) for c, marker, label in modes.values()]
    handles += [Line2D([], [], color=CRIMSON, marker="x", linestyle="", markersize=5, label="Execution failure")]
    fig.legend(handles=handles, ncol=3, loc="lower center", bbox_to_anchor=(.53, .12), fontsize=6.7)
    note(fig, f"Complete measured Token coverage: {measured}/{len(rows)} questions. Mean latency: {latency.mean():.1f}s; P95: {np.quantile(latency, .95, method='higher'):.1f}s.\nExecution success is separate from factual quality; failed calls retain complete observed Token costs.")
    return fig


def ai_quality(data):
    fig = figure("Answer quality under the evidence-based rubric", "AI-assisted assessment - not an independent human review", 11.4)
    left = fig.add_axes([.22, .30, .30, .44]); right = fig.add_axes([.69, .30, .23, .44])
    scores = data["scores"]; n = len(scores)
    colors = [CRIMSON, OCHRE, TEAL]
    starts = np.zeros(3)
    for score in range(3):
        counts = np.array([sum(row[f] == score for row in scores) for f in SCORE_FIELDS])
        percentages = counts / n
        left.barh(range(3), percentages, left=starts, height=.55, color=colors[score], edgecolor="white", linewidth=.8)
        for i, (count, proportion) in enumerate(zip(counts, percentages)):
            if count: left.text(starts[i] + proportion / 2, i, str(count), ha="center", va="center", color="white", fontweight="bold", fontsize=7)
        starts += percentages
    left.set_yticks(range(3), [SCORE_LABEL[f] for f in SCORE_FIELDS]); left.invert_yaxis()
    left.set_xlim(0, 1); left.set_xticks([0, .5, 1]); left.xaxis.set_major_formatter(PercentFormatter(1))
    left.set_xlabel("Share of 55 answers (counts shown)"); tidy(left)
    panel(left, "A", "Score distribution")
    category = {row["id"]: row["category"] for row in data["qa"]}
    values = np.array([[np.mean([s[f] for s in scores if category[s["id"]] == c]) for f in SCORE_FIELDS] for c in CATS])
    im = matrix_plot(right, values, vmax=2)
    right.set_yticks(range(4), [CAT_LABEL[c] for c in CATS], fontsize=6.6)
    right.set_xticks(range(3), ["Correct", "Complete", "Citation"], rotation=38, ha="right", fontsize=6.2)
    right.tick_params(length=0); annotate_matrix(right, values, ".2f", 2, 6.7)
    panel(right, "B", "Mean score by category")
    cax = fig.add_axes([.94, .30, .010, .44]); fig.colorbar(im, cax=cax, ticks=[0, 1, 2])
    cax.set_title("0-2", fontsize=6.1, pad=5)
    fig.legend(handles=[Patch(color=c, label=label) for c, label in zip(colors, ["0  Incorrect / absent", "1  Partial", "2  Fully supported"])],
               ncol=3, loc="lower center", bbox_to_anchor=(.52, .14), fontsize=6.5)
    note(fig, "All three dimensions use the 0/1/2 rubric; source pages were checked during AI-assisted assessment.\nThese ratings remain subject to independent human verification and potential assessor bias.")
    return fig


def bad_cases(data):
    sets = []
    for row in data["scores"]:
        tags = {tag.strip() for tag in row.get("bad_case", "none").split(";") if tag.strip() and tag.strip() != "none"}
        if tags - set(ERRORS): raise ValueError(f"Unknown error tags: {tags - set(ERRORS)}")
        sets.append(tags)
    counts = [sum(error in tags for tags in sets) for error in ERRORS]
    co = np.array([[sum(a in tags and b in tags for tags in sets) for b in ERRORS] for a in ERRORS])
    fig = figure("Bad-case taxonomy and co-occurrence", "AI-assisted multi-label classification of the 55 Agent answers", 11.3)
    left = fig.add_axes([.17, .28, .32, .48]); right = fig.add_axes([.65, .28, .27, .48])
    left.barh(range(4), counts, height=.58, color=[BLUE, OCHRE, CRIMSON, NAVY])
    left.set_yticks(range(4), [ERROR_LABEL[e] for e in ERRORS]); left.invert_yaxis()
    left.set_xlim(0, max(counts) * 1.23); left.set_xlabel("Questions carrying the error tag"); tidy(left)
    for i, count in enumerate(counts): left.text(count + .5, i, f"{count} / 55", va="center", fontsize=6.8)
    panel(left, "A", "Tag frequency")
    im = matrix_plot(right, co, vmax=max(1, co.max()))
    labels = [ERROR_LABEL[e] for e in ERRORS]
    right.set_yticks(range(4), labels, fontsize=6.5); right.set_xticks(range(4), labels, rotation=42, ha="right", fontsize=6.4)
    right.tick_params(length=0); annotate_matrix(right, co, fontsize=7.3)
    panel(right, "B", "Within-question co-occurrence")
    cax = fig.add_axes([.94, .28, .010, .48]); fig.colorbar(im, cax=cax, ticks=[0, 10, 20, 30, 40])
    cax.set_title("QA", fontsize=6.1, pad=5)
    clean = sum(not tags for tags in sets)
    fig.text(.17, .15, f"No labeled error: {clean} / {len(sets)} answers", fontsize=8, color=NAVY, fontweight="semibold")
    note(fig, "Tags overlap: one answer can contribute to multiple bars and cells. Diagonal cells are marginal tag counts.\nCo-occurrence describes observed labeling and does not establish a causal failure chain.")
    return fig


def architecture(data):
    fig = figure("System architecture and the evaluation side path", "Implemented RAG + Agent flow, with the Module 5 evidence and reporting workflow", 15.4)
    ax = fig.add_axes([.035, .08, .93, .77]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    def box(x, y, w, h, text, color=NAVY, fill=PALE, fontsize=6.6):
        patch = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.008,rounding_size=0.013", linewidth=.9, edgecolor=color, facecolor=fill, zorder=3)
        ax.add_patch(patch); ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, color=color, linespacing=1.45, zorder=4)
    def arrow(start, end, dashed=False, color=MUTED, connection="arc3,rad=0"):
        ax.add_patch(FancyArrowPatch(start,end,arrowstyle="-|>",mutation_scale=8,linewidth=.9,color=color,linestyle="--" if dashed else "-",connectionstyle=connection,zorder=2))
    ax.text(.02, 1.01, "APPLICATION AND KNOWLEDGE PIPELINE", fontsize=7, fontweight="bold", color=NAVY)
    box(.11,.91,.18,.085,"Streamlit UI\nuser question",fontsize=6.9)
    box(.37,.91,.18,.085,"Fast router\nintent + confidence",fontsize=6.9)
    box(.65,.91,.21,.085,"Tool registry\nsearch / summary / compare",fontsize=6.5)
    box(.90,.91,.16,.085,"Answer +\nsource pages",color=TEAL,fill="#EDF6F4")
    arrow((.21,.91),(.27,.91)); arrow((.47,.91),(.535,.91)); arrow((.765,.91),(.81,.91))
    box(.37,.74,.18,.095,"ReAct fallback\nthink / act / observe",color=BLUE,fill="#EDF2F7")
    arrow((.37,.86),(.37,.798)); arrow((.47,.76),(.55,.86),color=BLUE)
    ax.text(.315,.822,"uncertain",fontsize=5.6,color=MUTED)
    arrow((.43,.69),(.48,.73),color=BLUE,connection="arc3,rad=.6")
    box(.11,.69,.18,.085,f"PDF corpus\n{len(data['corpus'])} source papers",fontsize=6.9)
    box(.11,.53,.18,.095,"Page text extraction\nfilename + physical page",fontsize=6.2)
    box(.11,.36,.18,.095,"Recursive chunks\n256 / 512 / 1024 chars",fontsize=6.4)
    arrow((.11,.645),(.11,.585)); arrow((.11,.475),(.11,.415))
    box(.39,.36,.20,.10,"BGE embeddings\nChroma vector index",color=BLUE,fill="#EDF2F7",fontsize=6.7)
    box(.39,.52,.20,.085,"BM25\nlexical index",color=BLUE,fill="#EDF2F7",fontsize=6.8)
    arrow((.21,.36),(.28,.36)); arrow((.19,.40),(.28,.49))
    box(.68,.44,.22,.17,"Vector + BM25\nRRF: 20 candidates\nBGE rerank: top 5",color=TEAL,fill="#EDF6F4",fontsize=7)
    arrow((.50,.36),(.56,.40)); arrow((.50,.52),(.56,.48))
    box(.88,.68,.19,.11,"Ollama / Qwen2.5\ngrounded generation",color=TEAL,fill="#EDF6F4",fontsize=6.4)
    arrow((.70,.535),(.82,.62),color=TEAL); arrow((.88,.745),(.90,.86),color=TEAL)
    arrow((.65,.86),(.67,.535)); ax.text(.69,.73,"evidence tools",fontsize=5.7,color=MUTED,rotation=90,ha="center")
    ax.plot([.02,.98],[.235,.235],color=GRID,lw=.9)
    ax.text(.02,.205,"MODULE 5 EVALUATION SIDE PATH",fontsize=7,fontweight="bold",color=OCHRE)
    box(.11,.105,.18,.10,"Frozen 55-QA set\ngold answer + evidence",color=OCHRE,fill="#FBF7ED",fontsize=6.3)
    box(.37,.105,.21,.10,"Evaluation harness\n9 retrieval configs + Agent",color=OCHRE,fill="#FBF7ED",fontsize=6.2)
    box(.65,.105,.21,.10,"Persisted observations\nanswers / traces / tokens",color=OCHRE,fill="#FBF7ED",fontsize=6.1)
    box(.90,.105,.16,.10,"AI rubric +\nreport figures",color=OCHRE,fill="#FBF7ED",fontsize=6.2)
    arrow((.21,.105),(.255,.105),color=OCHRE);arrow((.485,.105),(.535,.105),color=OCHRE);arrow((.765,.105),(.81,.105),color=OCHRE)
    arrow((.45,.164),(.57,.35),dashed=True,color=OCHRE)
    ax.text(.605,.285,"retrieval / agent_chat hooks",fontsize=5.4,color=OCHRE)
    cjk = " 架构示意，非系统界面截图。" if HAS_CJK else ""
    note(fig, f"Architecture schematic - not a UI screenshot.{cjk}\nEvaluation uses isolated sessions (use_memory=False); AI-assisted scoring remains subject to human verification.")
    return fig


BUILDERS = (
    ("01_dataset_profile", dataset_profile), ("02_retrieval_quality", retrieval_quality),
    ("03_retrieval_tradeoff", retrieval_tradeoff), ("04_paired_hits", paired_hits),
    ("05_agent_performance", agent_performance), ("06_ai_quality", ai_quality),
    ("07_bad_cases", bad_cases), ("08_architecture", architecture),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE / "data" / "report_data.json")
    parser.add_argument("--out", type=Path, default=BASE / "figures")
    parser.add_argument("--dpi", type=int, default=240)
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8-sig"))
    for key in ("qa", "corpus", "agent", "scores", "retrieval", "comparison", "provenance"):
        if key not in data: raise ValueError(f"Missing frozen data key: {key}")
    if data["provenance"].get("independent_human_review") is not False:
        raise ValueError("Verify assessment provenance before labeling figures as AI-assisted.")
    setup_style(); args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(), "png_dpi": args.dpi, "width_cm": 16.8,
                "figure_count": len(BUILDERS), "figures": []}
    for name, builder in BUILDERS:
        fig = builder(data)
        # Matplotlib auto-rasterizes dense colorbar gradients; keep those vector too.
        for axis in fig.axes:
            for collection in axis.collections:
                collection.set_rasterized(False)
        for extension in ("pdf", "png"):
            fig.savefig(args.out / f"{name}.{extension}", dpi=args.dpi,
                        metadata={"Creator": "Module 5 reproducible matplotlib figures"} if extension == "pdf" else None)
        manifest["figures"].append({"basename": name, "width_inches": float(fig.get_figwidth()), "height_inches": float(fig.get_figheight())})
        plt.close(fig)
        print(f"Saved {name}.pdf + .png")
    (args.out / "figure_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
