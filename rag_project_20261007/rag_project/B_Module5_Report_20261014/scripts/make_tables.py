"""Generate portable, evidence-based LaTeX table fragments using only stdlib.

Run from any directory: python path/to/scripts/make_tables.py
Requires booktabs, tabularx, longtable and array in the parent LaTeX document.
No source results, scores, figures or main.tex are modified.
"""
import argparse
import collections
import json
import math
import re
import statistics
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
CATEGORIES = ("factual", "comparison", "summary", "reasoning")
CATEGORY_LABELS = {"factual": "事实", "comparison": "对比", "summary": "归纳", "reasoning": "推理"}
METHODS = ("vector", "hybrid", "hybrid_rerank")
METHOD_LABELS = {"vector": "向量", "hybrid": "混合（RRF）", "hybrid_rerank": "混合＋重排"}
SCORE_FIELDS = ("correctness", "completeness", "citation_accuracy")
CASE_IDS = ("F02", "F07", "F16", "C14", "S10", "R08")
ESCAPES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
           "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def tex(value):
    return "".join(ESCAPES.get(char, char) for char in str(value))


def english(value):
    """Allow narrow English title columns to break at explicit hyphens/slashes."""
    return tex(value).replace("-", r"-\allowbreak{}").replace("/", r"/\allowbreak{}")


def number(value, digits=3):
    if value is None:
        return "--"
    return f"{float(value):,.{digits}f}".replace(",", r"\,")


def integer(value):
    return f"{int(value):,}".replace(",", r"\,")


def percent(value, digits=2):
    return number(100 * value, digits) + r"\%"


def ratio(numerator, denominator):
    return f"{integer(numerator)}/{integer(denominator)}（{percent(numerator / denominator)}）" if denominator else "--"


def average(values):
    return statistics.fmean(values) if values else None


def header(*lines):
    return r"\shortstack{" + r"\\".join(lines) + "}"


def row(*cells):
    return " & ".join(str(cell) for cell in cells) + r" \\"


def note(text):
    return r"\par\vspace{4pt}{\footnotesize " + text + r"\par}"


def table_start(columns, small=True, stretch="1.16"):
    return [r"\begingroup", r"\small" if small else r"\footnotesize",
            r"\setlength{\tabcolsep}{5pt}", r"\renewcommand{\arraystretch}{" + stretch + "}",
            r"\begin{tabularx}{\linewidth}{" + columns + "}", r"\toprule"]


def table_end(lines, text=None):
    lines += [r"\bottomrule", r"\end{tabularx}"]
    if text:
        lines.append(note(text))
    lines.append(r"\endgroup")
    return "\n".join(lines) + "\n"


def longtable_start(columns, headings, count, explanation, caption, label):
    return [r"\begingroup", r"\small", r"\setlength{\tabcolsep}{5pt}",
            r"\renewcommand{\arraystretch}{1.13}", note(explanation),
            r"\begin{longtable}{" + columns + "}",
            r"\caption{" + tex(caption) + r"}\label{" + label + r"}\\",
            r"\toprule", row(*headings), r"\midrule",
            r"\endfirsthead", r"\multicolumn{" + str(count) + r"}{@{}l}{\footnotesize（续表）} \\",
            r"\toprule", row(*headings), r"\midrule", r"\endhead", r"\midrule",
            r"\multicolumn{" + str(count) + r"}{r@{}}{\footnotesize 续下页} \\", r"\endfoot",
            r"\bottomrule", r"\endlastfoot"]


def keyed(records, label):
    result = {record["id"]: record for record in records}
    if len(result) != len(records):
        raise ValueError(f"Duplicate IDs in {label}.")
    return result


def validate(data):
    for key, count in (("qa", 55), ("agent", 55), ("scores", 55), ("retrieval", 495), ("corpus", 15)):
        if not isinstance(data.get(key), list) or len(data[key]) != count:
            raise ValueError(f"Expected {count} records in {key}.")
    ids = set(keyed(data["qa"], "qa"))
    if set(keyed(data["agent"], "agent")) != ids or set(keyed(data["scores"], "scores")) != ids:
        raise ValueError("QA, Agent and score IDs do not match exactly.")
    for score in data["scores"]:
        for field in SCORE_FIELDS + ("routing",):
            value = score.get(field)
            allowed = (0, 1) if field == "routing" else (0, 1, 2)
            if type(value) is not int or value not in allowed:
                raise ValueError(f"Invalid/missing {field} score for {score['id']}.")
    if any(record.get("category") not in CATEGORIES for record in data["qa"]):
        raise ValueError("Unknown QA category.")
    groups = collections.defaultdict(list)
    for record in data["retrieval"]:
        groups[(record["chunk_size"], record["method"])].append(record)
        for field in ("hit_at_5", "mrr_at_5", "recall_at_5", "wall_latency_s"):
            value = record.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Missing/nonfinite retrieval {field}.")
    if set(groups) != {(size, method) for size in (256, 512, 1024) for method in METHODS}:
        raise ValueError("Expected all nine chunk-size/method configurations.")
    for key, records in groups.items():
        if len(records) != 55 or {record["id"] for record in records} != ids:
            raise ValueError(f"Incomplete/duplicate retrieval IDs for {key}.")
    for paper in data["corpus"]:
        if not paper.get("title") or not isinstance(paper.get("pages"), int):
            raise ValueError("Corpus requires verified title and physical page count.")
    return groups


def retrieval_table(data, groups):
    chunks = {record["chunk_size"]: record["chunk_count"] for record in data["comparison"]["inputs"]}
    results = []
    for (size, method), records in sorted(groups.items(), key=lambda item: (item[0][0], METHODS.index(item[0][1]))):
        results.append({"size": size, "method": method, "n": len(records),
                        "hits": sum(record["hit_at_5"] for record in records),
                        "hit": average([record["hit_at_5"] for record in records]),
                        "mrr": average([record["mrr_at_5"] for record in records]),
                        "recall": average([record["recall_at_5"] for record in records]),
                        "latency": average([record["wall_latency_s"] for record in records])})
    # Verify the independently recomputed values against the frozen comparison.
    for record in results:
        source = next(r for r in data["comparison"]["overall"] if r["chunk_size"] == record["size"] and r["method"] == record["method"])
        for field, original in (("hit", "hit_at_5"), ("mrr", "mrr_at_5"), ("recall", "recall_at_5"), ("latency", "avg_wall_latency_s")):
            if not math.isclose(record[field], source[original], abs_tol=1e-7):
                raise ValueError("Frozen comparison does not match its raw retrieval records.")
    best = {key: (min if key == "latency" else max)(record[key] for record in results)
            for key in ("hits", "hit", "mrr", "recall", "latency")}
    def strongest(key, value, text):
        return r"\textbf{" + text + "}" if math.isclose(value, best[key], abs_tol=1e-12) else text
    lines = table_start(r"@{}r r >{\raggedright\arraybackslash}X r r r r r@{}")
    lines += [row(header("块长", "（字符）"), header("文本块", "（个）"), "检索方法", header("命中", "（题/55）"),
                  header("Hit@5", r"（\%）"), "MRR@5", header("Recall@5", r"（\%）"), header("平均查询", "（s/题）")), r"\midrule"]
    for index, record in enumerate(results):
        if index and index % 3 == 0:
            lines.append(r"\addlinespace[5pt]")
        first = index % 3 == 0
        lines.append(row(str(record["size"]) if first else "", integer(chunks[record["size"]]) if first else "",
                         METHOD_LABELS[record["method"]], strongest("hits", record["hits"], f"{int(record['hits'])}/55"),
                         strongest("hit", record["hit"], number(100 * record["hit"], 2)),
                         strongest("mrr", record["mrr"], number(record["mrr"])),
                         strongest("recall", record["recall"], number(100 * record["recall"], 2)),
                         strongest("latency", record["latency"], number(record["latency"]))))
    return table_end(lines, r"每配置 $n=55$；共 495 次检索，均为递归字符分块。相关性以文件名与 PDF 物理页共同匹配。粗体表示九配置中的最优值（延迟取最小），并列最优均标粗。")


def agent_table(data):
    agents, scores = data["agent"], data["scores"]
    overall = next(record for record in data["agent_summary"]["groups"]
                   if record.get("category") == "all" and record.get("execution_mode") == "all")
    observed = [record["auto_tool_match"] for record in agents if record.get("auto_tool_match") in (0, 1)]
    semantic = [record["routing"] for record in scores]
    steps = [record["steps"] for record in agents if isinstance(record.get("steps"), (int, float))]
    react = [record["steps"] for record in agents if record.get("execution_mode") == "react" and isinstance(record.get("steps"), (int, float))]
    tokens = [record["token_usage"]["total_tokens"] for record in agents
              if record.get("token_usage", {}).get("complete") and isinstance(record["token_usage"].get("total_tokens"), (int, float))]
    metrics = [
        ("执行成功率", ratio(sum(record.get("success") is True for record in agents), len(agents)), "后端执行标志；包含失败题。"),
        ("自动工具集合匹配率", ratio(sum(observed), len(observed)), "与预标允许工具集合精确匹配；不评估参数语义。"),
        ("AI 辅助语义路由合理率", ratio(sum(semantic), len(semantic)), "AI 同时检查选用工具、调用参数与完整任务意图。"),
        ("平均端到端延迟", number(average([record["wall_latency_s"] for record in agents])) + " s", f"$n={len(agents)}$；包含失败题与保留的原始测量。"),
        ("P95 端到端延迟", number(overall["p95_wall_latency_s"]) + " s", f"$n={len(agents)}$；按冻结汇总的第 95 百分位口径。"),
        ("平均执行步骤", number(average(steps), 2) + " 步/题", f"$n={len(steps)}$；含直接工具执行与 ReAct。"),
        ("ReAct 平均执行步骤", number(average(react), 2) + " 步/题", f"仅 $n={len(react)}$ 个 ReAct 请求。"),
        ("完整计量 Token 总量", integer(sum(tokens)) + " token", f"$n={len(tokens)}$；每题所有 LLM 调用的输入与输出之和。"),
        ("平均 Token 消耗", number(average(tokens), 1) + " token/题", f"分母为 $n={len(tokens)}$ 个计量完整的题目。"),
        ("Token 计量覆盖率", ratio(len(tokens), len(agents)), "缺失计数不按零处理。"),
    ]
    lines = table_start(r"@{}p{0.29\linewidth}p{0.27\linewidth}>{\raggedright\arraybackslash}X@{}")
    lines += [row("指标", "结果", "分母与判定口径"), r"\midrule"]
    lines += [row(*cells) for cells in metrics]
    return table_end(lines, "自动工具匹配与 AI 语义路由是不同指标。评分未作独立人工复核；执行成功不等于答案正确。")


def scores_table(data):
    qa, scores = keyed(data["qa"], "qa"), keyed(data["scores"], "scores")
    lines = table_start(r"@{}>{\raggedright\arraybackslash}X r r r r r@{}")
    lines += [row("问题类别", "$n$", header("正确性", "（0--2）"), header("完整性", "（0--2）"),
                  header("引用准确性", "（0--2）"), header("AI 语义路由", r"合理率（\%）")), r"\midrule"]
    for category in CATEGORIES + ("all",):
        selected = [scores[qid] for qid, question in qa.items() if category == "all" or question["category"] == category]
        if category == "all":
            lines.append(r"\midrule")
        cells = ["总体" if category == "all" else CATEGORY_LABELS[category], str(len(selected))]
        cells += [number(average([record[field] for record in selected])) for field in SCORE_FIELDS]
        cells.append(number(100 * average([record["routing"] for record in selected]), 2))
        if category == "all":
            cells = [r"\textbf{" + cell + "}" for cell in cells]
        lines.append(row(*cells))
    return table_end(lines, "三项答案评分取 0、1、2 分；表中为均值。各维度均覆盖对应类别全部题目，失败题保留。语义路由逐题判 0/1，结果为 AI 辅助评分。")


def cases_table(data):
    papers = {paper["source"]: paper.get("paper_id", f"P{index:02d}") for index, paper in enumerate(data["corpus"], 1)}
    def p(source, pages):
        return tex(papers[source]) + "，第 " + pages + " 页"
    cases = {
        "F02": ("生成／传参偏移", "将集成模型测试集 3.57\\% 误写为单模型验证集结果。",
                p("Deep_Residual_Learning_for_Image_Recognition.pdf", "2、7") + "区分两种设置；建议保留原题限定，并逐项绑定模型、数据划分与指标。"),
        "F07": ("Agent 执行失败", "事实问题误走元数据工具，字符串拼接 TypeError 导致无答案、无引用。",
                p("Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf", "1") + "包含所问设置；建议修正意图判定、规范字段类型，并保留真实失败状态。"),
        "F16": ("检索证据缺失", "未返回 ViT 数据集规模所在页，最终拒答三组类别数／图像数。",
                p("An_Image_is_Worth_16x16_Words.pdf", "4") + "有完整数据；建议约束目标来源与章节，再检验召回和答案完整性。"),
        "C14": ("来源匹配／生成", "Vim 匹配成另一篇论文；又将 ResNet 的 ImageNet 指标误归 CIFAR-10。",
                p("2401.09417v3.pdf", "2、5") + "及 ResNet 第 7 页可核对；建议使用确定的题名—文件映射，并按数据集组织证据。"),
        "S10": ("任务分解／状态", "三篇论文被交给双篇比较工具；返回错误信息，却以 success=True 结束。",
                "三篇原文第 1 页均有相应内容；建议逐篇抽取后汇总，并将工具失败状态向上传递。"),
        "R08": ("推理归因错误", "以色彩基线缺少端到端评估，解释复合规则 0/102 不能算独立验证误报率。",
                p("sensors-26-06403.pdf", "8、11") + "说明同集设计偏差及冻结后独立验证；建议区分评估对象、设计集与验证集。"),
    }
    lines = table_start(r"@{}p{0.06\linewidth}p{0.15\linewidth}p{0.31\linewidth}>{\raggedright\arraybackslash}X@{}", small=False, stretch="1.2")
    lines += [row("题号", "主要问题", "已观察现象", "核查证据与待验证改进"), r"\midrule"]
    for qid in CASE_IDS:
        lines.append(row(r"\textbf{" + qid + "}", *cases[qid]))
        if qid != CASE_IDS[-1]:
            lines.append(r"\addlinespace[4pt]")
    return table_end(lines, "案例由冻结的 AI 辅助评分与实际结果归纳；P 编号对应文献表，页码均为 PDF 物理页。改进为待实施、待复测建议，不代表已取得优化后结果。")


def questions_table(data):
    agents, scores = keyed(data["agent"], "agent"), keyed(data["scores"], "scores")
    headings = ["题号", "类别", header("正确性", "（0--2）"), header("完整性", "（0--2）"),
                header("引用准确性", "（0--2）"), header("AI 语义路由", "（0/1）"), header("自动工具匹配", "（0/1）")]
    lines = longtable_start(r"@{}l l r r r r r@{}", headings, 7,
                            "答案三维评分为 0--2；AI 语义路由与自动工具匹配为 0/1。AI 语义评分未经独立人工复核。",
                            "55题逐题AI辅助评分与工具匹配明细", "tab:questions")
    previous_category = None
    for question in data["qa"]:
        qid, category = question["id"], question["category"]
        if previous_category is not None and category != previous_category:
            lines.append(r"\addlinespace[4pt]")
        score = scores[qid]
        auto = agents[qid].get("auto_tool_match")
        lines.append(row(qid, CATEGORY_LABELS[category], *[str(score[field]) for field in SCORE_FIELDS],
                         str(score["routing"]), str(auto) if auto in (0, 1) else "--"))
        previous_category = category
    lines += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines) + "\n"


def environment_table(data):
    meta = data["provenance"]["agent_metadata"]
    runtime, parameters, packages = meta["runtime"], meta["parameters"], meta["packages"]
    options = runtime.get("llm_options", {})
    os_build = re.search(r"\b(\d{5})\b", meta.get("platform", ""))
    rows = [("运行环境", "Python", tex(meta["python"].split()[0])),
            ("运行环境", "操作系统", "Windows（build " + os_build.group(1) + "）" if os_build else tex(meta.get("platform", "未记录"))),
            ("生成模型", "Ollama 模型", r"\texttt{" + tex(runtime["ollama_model"]) + "}"),
            ("检索模型", "Embedding", english(runtime["embedding_model"])),
            ("检索模型", "Reranker", english(runtime["reranker_model"])),
            ("检索模型", "推理设备", r"\texttt{" + tex(runtime["device"]) + "}"),
            ("依赖版本", "PyTorch", tex(packages["torch"])),
            ("依赖版本", "Sentence Transformers", tex(packages["sentence-transformers"])),
            ("依赖版本", "ChromaDB / rank-bm25", tex(packages["chromadb"] + " / " + packages["rank-bm25"])),
            ("依赖版本", "pdfplumber / Ollama SDK", tex(packages["pdfplumber"] + " / " + packages["ollama"])),
            ("生成参数", "上下文窗口", integer(options.get("num_ctx", 4096)) + " token"),
            ("生成参数", "请求超时", integer(runtime.get("llm_timeout_s", 120)) + " s"),
            ("Agent 参数", "分块／重叠", integer(parameters["chunk_size"]) + " / " + integer(parameters["overlap"]) + " 字符"),
            ("检索实验", "递归字符块长", "256 / 512 / 1024 字符"),
            ("检索参数", "候选／输出", integer(parameters["recall_k"]) + " / " + integer(parameters["top_k"]) + " 个文本块"),
            ("会话参数", "Memory", "关闭；每题独立会话" if not parameters["use_memory"] else "开启"),
            ("评分来源", "性质", "AI 辅助证据评分；未作独立人工复核")]
    lines = table_start(r"@{}p{0.16\linewidth}p{0.31\linewidth}>{\raggedright\arraybackslash}X@{}")
    lines += [row("类别", "项目", "版本或配置"), r"\midrule"]
    previous = None
    for category, item, value in rows:
        if previous is not None and category != previous:
            lines.append(r"\addlinespace[3pt]")
        lines.append(row(category if category != previous else "", item, value))
        previous = category
    return table_end(lines, "模型、依赖与请求参数取自冻结运行元数据；Ollama SDK 版本与独立服务版本不是同一概念。块长单位为字符，上下文窗口单位为 token。")


def corpus_table(data):
    lines = longtable_start(r"@{}l >{\raggedright\arraybackslash}p{0.79\linewidth}r@{}",
                            ["编号", "论文题名（原文）", "页数"], 3,
                            "共 15 篇论文；页数为文件的 PDF 物理页数。文件名与哈希映射保存在包内数据文件。",
                            "15篇本地论文与物理页清单", "tab:corpus")
    for index, paper in enumerate(data["corpus"], 1):
        lines.append(row(tex(paper.get("paper_id", f"P{index:02d}")), english(paper["title"]), integer(paper["pages"])))
        if index != len(data["corpus"]):
            lines.append(r"\addlinespace[3pt]")
    lines += [r"\midrule", row(r"\multicolumn{2}{@{}l}{\textbf{合计：15 篇}}", r"\textbf{" + integer(sum(paper["pages"] for paper in data["corpus"])) + "}"),
              r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PACKAGE / "data" / "report_data.json")
    parser.add_argument("--output", type=Path, default=PACKAGE / "tables")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8-sig"))
    groups = validate(data)
    tables = {"01_retrieval": retrieval_table(data, groups), "02_agent": agent_table(data),
              "03_scores": scores_table(data), "04_cases": cases_table(data),
              "05_questions": questions_table(data), "06_environment": environment_table(data),
              "07_corpus": corpus_table(data)}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in tables.items():
        (args.output / (name + ".tex")).write_text(
            "% Generated by scripts/make_tables.py from data/report_data.json.\n" + content,
            encoding="utf-8")
    print(json.dumps({"tables": len(tables), "qa": len(data["qa"]), "agent": len(data["agent"]),
                      "scores": len(data["scores"]), "retrieval": len(data["retrieval"]),
                      "corpus": len(data["corpus"]), "physical_pages": sum(paper["pages"] for paper in data["corpus"])}))


if __name__ == "__main__":
    main()
