# 成员 B 模块五运行和交付方案

本方案用于当前 Windows 本地项目，假定你已激活团队准备好的 Python 环境。B 负责组织真实评测、核对答案证据、分析失败案例并汇总交付材料。先跑通少量题，再开展正式实验；截图、图表和报告中的数字都要对应保存的原始运行记录。

项目目录：`D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project`。

2026 年 10 月 10 日补充：现已根据新增论文准备好 `evaluation/qa.jsonl`，包含事实 20、对比 15、归纳 10、推理 10 题，以及参考答案、证据和页码；去重语料位于 `evaluation/corpus/`，共 15 篇。题目和证据已核对，见 `evaluation/qa_questions.md` 与 `evaluation/qa_validation.json`。在已有环境中执行 `python scripts/run55.py` 可直接运行全部 55 题 Agent 评测；脚本自动定位文件并创建新的时间戳结果目录。若从其他目录运行，使用 run55.py 的绝对路径。下文第 6 节的空白模板步骤用于自行重建评测集，已有这份完成的数据集时可跳过。

## 1 明确任务和材料范围

课程模块五明确要求：选定研究方向并收集 10–20 篇论文；构建 50+ 问答对，覆盖事实、对比、归纳、推理四类；评测 Hit@5、MRR、Recall、工具调用准确率、平均推理轮次、平均延迟、Token 消耗；人工评价正确性、完整性、引用准确性；绘制参数对比图；对检索、生成、引用、Agent 决策四类 Bad Case 分析原因；至少进行一轮优化并记录前后对比。

课程最终交付包括代码仓库、系统评测报告、技术设计文档、演示 PPT、用户手册。粘贴的 RAG 分工将 B 定为模块五负责人，建议 55 题，分布为事实 20、对比 15、归纳 10、推理 10，贡献比例 15%。这些配额是团队建议，课程没有规定各类题目数量。

你附的 `团队分工.docx` 是 InterviewPilot 面试项目的 PPT 规划，其 B 分工为后端与数据，与本 RAG 项目不一致。本方案按你明确指定的模块五和粘贴的 RAG 分工执行，不把另一个项目的要求套进来。

课程原文没有规定截图数量。本文截图清单是建议保留的验收证据。粘贴分工中 A 的 3–5 张界面截图，可以作为最终报告的核心展示图；B 另保存评测与失败案例证据。

## 2 先检查已有环境

所有命令在 PowerShell 中运行。每个新终端都要激活你原有的环境，不需要新建环境。先确认解释器来自该环境。

```powershell
Set-Location -LiteralPath "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project"
python -c "import sys; print(sys.executable); print(sys.version)"
python -c "import streamlit, pdfplumber, chromadb, sentence_transformers, rank_bm25, jieba, ollama; print('Runtime imports OK')"
ollama list
```

若第二条检查提示缺包，只在这个已有环境补装报错的包。不要直接重新安装原来的完整 `requirements.txt`，它含有 Linux/CUDA 相关依赖。Ollama 列表应包含 `qwen2.5:7b`；当前 Agent 实际固定使用这个模型和 `127.0.0.1:11434`。

如果 Ollama 未启动，在另一终端执行 `ollama serve` 并保持运行。服务已经运行时不重复启动。如果模型未准备好，执行 `ollama pull qwen2.5:7b`。

截图 `01_environment.png`：解释器路径和版本、依赖导入成功、Ollama 模型列表。记录 CPU/GPU、内存、模型版本，正式实验期间保持一致。

## 3 修正前端运行所需的本地路径

本版本的 `src/config.py` 支持本地配置，但原 C/D 后端部分文件仍写死 `/root/autodl-tmp/...`。环境已经准备好，也不等于这些路径已经修正。仅设置 `RAG_*` 环境变量不能覆盖所有硬编码。

若已修正可跳过。以下命令会把原 Linux 项目和模型目录改为当前项目绝对路径，并为修改的源文件保存 `.py.bak`。它还补齐 `rag_pipeline.py` 中漏掉的 `load_pdf` 导入。务必在上述项目目录执行。

```powershell
@'
import ast
from pathlib import Path
root = Path.cwd()
assert (root / "app.py").is_file(), "Run in the project directory"
mapping = {
    "/root/autodl-tmp/models": (root / "models").as_posix(),
    "/root/autodl-tmp/rag_project": root.as_posix(),
}
for p in (root / "src").rglob("*.py"):
    original = p.read_text(encoding="utf-8")
    updated = original
    for old, new in mapping.items():
        updated = updated.replace(old, new)
    if p.name == "rag_pipeline.py":
        updated = updated.replace(
            "from src.data_loader.pdf_loader import load_pdfs_from_dir\n",
            "from src.data_loader.pdf_loader import load_pdfs_from_dir, load_pdf\n",
        )
    if updated != original:
        ast.parse(updated)
        backup = p.with_suffix(".py.bak")
        if not backup.exists():
            backup.write_text(original, encoding="utf-8")
        p.write_text(updated, encoding="utf-8")
        print("Updated:", p.relative_to(root))
'@ | python -
```

若团队已有 BGE 模型，将模型文件夹放到 `models/bge-large-zh` 和 `models/bge-reranker-base`，或与 C/D 一起把上面两个模型默认路径改成他们实际的绝对路径。不要把一个空文件夹当成已准备好的模型。模型尚未下载且环境已有 ModelScope 时可执行：

```powershell
python -c "from modelscope import snapshot_download; snapshot_download('AI-ModelScope/bge-large-zh-v1.5', local_dir='models/bge-large-zh')"
python -c "from modelscope import snapshot_download; snapshot_download('BAAI/bge-reranker-base', local_dir='models/bge-reranker-base')"
```

新增的评测脚本在其独立进程中显式使用共享配置和专属向量库，不覆盖前端知识库。但是前端页面仍需上述路径适配。前端、正式评测必须使用同一批论文、同一组模型。

## 4 软件检查和文档解析检查

```powershell
New-Item -ItemType Directory -Force -Path evaluation, evaluation\evidence, evaluation\evidence\screenshots | Out-Null
python -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath evaluation\evidence\software_tests.txt
python -m src.data_loader.pdf_loader data 2>&1 | Tee-Object -FilePath evaluation\evidence\pdf_loading.txt
python -c "from src.data_loader.pdf_loader import load_pdfs_from_dir; from src.chunking.experiment import run_experiment; run_experiment(load_pdfs_from_dir('data'), output_csv='evaluation/evidence/chunk_statistics.csv')"
```

检查测试失败数、跳过数，以及每篇 PDF 是否有可提取正文。扫描 PDF 无文本时应先 OCR 或更换论文。已有测试包含 mock：测试通过可以证明相应软件逻辑通过，不能代替真实模型检索、生成和答案评分。当前历史分块 CSV 只有块数、长度，不是检索质量成绩。

截图 `02_software_tests.png`：最终测试输出，包括失败和跳过情况。不要只截中途某一条 `ok`。

## 5 先完成一次页面真实问答

在一个终端启动页面并保持运行：

```powershell
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

浏览器打开 `http://127.0.0.1:8501`。先用现有三份论文跑通。左侧点击“构建 / 更新知识库”，等待建库完成。确认文档为“已向量化”，记录文本块数量和首次建库耗时。

按以下顺序进行页面功能检查，每次等当前问题完成后再继续：

| 检查项 | 可直接输入的内容或操作 | 核对点 |
| --- | --- | --- |
| 时间工具 | 现在几点？ | 当前时间与实际系统时间合理一致；这是工具测试，不计入论文 QA 集 |
| 事实与引用 | 《Attention Is All You Need》的作者是谁？ | 答案和原文一致；来源文件与 PDF 物理页码可定位 |
| 总结 | 请总结论文《Attention Is All You Need》 | 覆盖背景、方法、结果、结论；不要凭 success 判答案正确 |
| 对比 | 比较《Attention Is All You Need》和《An Image is Worth 16x16 Words》的输入、模型结构和任务 | 区分两篇论文，有双方证据；检查 paper_compare 实际执行结果 |
| 推理与轨迹 | 《Attention Is All You Need》中为什么缩放点积注意力需要除以 sqrt(d_k)？ | 解释对应论文证据；展开实际 Agent 执行过程 |
| 多轮 | 新建会话并开启上下文；先总结一篇论文，再问“它的核心关键词是什么？” | 指代指向刚才的论文；换新会话后不串用旧论文 |
| 历史 | 新建、切换、重新加载、导出、删除一个临时会话 | 历史内容和切换状态正确；只删除测试会话 |
| 状态 | 展开“系统状态与运行统计” | Ollama、模型、索引状态；请求数、平均耗时、平均步骤 |

每个答案至少核对其关键结论和引用 PDF。页码使用 PDF 从第一页开始的物理页码，不使用论文页脚印刷页号。若不正确，保留为 Bad Case，而不是反复改问法直到截图看起来正确。

截图 `03_index_ready.png`、`04_factual_answer.png`、`05_source_pdf.png`、`06_comparison.png`、`07_reasoning_trace.png`、`08_memory_history.png`。导出的完整 JSON/Markdown 与截图一起保留。

## 6 扩充论文库并固定评测集

当前项目只有三份示例论文，不能据此写“已完成 10–20 篇论文评测”。先选一个清楚的研究方向，收集 10–20 篇对应论文；若保留现有 ResNet、Transformer、ViT，可选择“视觉模型从 CNN 到 Transformer 的方法演进”，并解释纳入原则。不相关的论文不要为了凑数量加入。

将真实 PDF 放入 `data/`，或通过页面批量上传。文件名固定后不要在实验之间改名。记录题名、作者、年份、文件名、论文原始来源和选入理由。不要从课程方案中的示例准确率抄成绩。

新增工具的命令如下：

```powershell
python scripts/module5_eval.py init --out evaluation/templates
```

它在 `evaluation/templates/qa.template.jsonl` 生成待填写的 55 题 JSONL 模板。模板的空问题、空答案、空证据不代表已建好评测集，也不能用于正式评测。填写后保存为 `evaluation/qa.jsonl`。JSONL 每行一个 JSON 对象，建议用 UTF-8 保存。

字段含义以脚本生成的说明为准，关键内容是：

| 字段 | B 填什么 |
| --- | --- |
| id | 唯一稳定编号；优化前后保持同一编号 |
| category | factual、comparison、summary、reasoning |
| question | 清楚、可由纳入论文回答的真实问题 |
| reference_answer | 先查原文再写的参考答案，标明必答要点 |
| gold_evidence | 支持答案的 source、page、evidence；跨论文题应包含多份证据 |
| accepted_tool_sets | 在看实际输出之前标注可接受的完整工具集合；允许多种有效方案 |

例如作者问题通常接受 `["paper_metadata"]`；论文比较通常接受 `["paper_compare"]`。复杂科研问答可能有不同的有效工具组合，应先由 B 与 D 确认。不要用系统刚刚选出的工具反过来当标准答案。

建议 55 题采用 20/15/10/10 的团队分布，每篇论文有题目覆盖，对比/归纳题包含多个证据。推理题要求“有文献根据的解释”，不是让模型猜作者动机。参考答案不能直接复制被测系统的回答；如果先让模型草拟，仍须逐条核对原文。

完成后检查：

```powershell
python scripts/module5_eval.py check --qa evaluation/qa.jsonl
```

若失败，按提示修正后再运行。脚本校验格式和规模；B 仍要核验页码和证据实际内容。截图 `09_dataset_check.png`：题目数、四类分布、论文数和校验结果。保存最终 QA 文件，正式实验开始后冻结题目、参考答案和证据。

## 7 少量题试跑

先停止前端（启动终端按 Ctrl+C），减少 CPU/内存争用。Ollama 保持运行。每次 run 使用独立输出目录，避免覆盖已有结果。

```powershell
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode retrieval --chunk-size 512 --smoke --limit 3 --out evaluation/smoke/retrieval512
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode agent --chunk-size 512 --smoke --limit 3 --out evaluation/smoke/agent512
```

检查每题是否有真实返回，是否出现模型目录、服务连接、PDF 文本、上下文或超时错误。试跑只能证明链路和输出文件可用，不能写成“55 题成绩”。同一目录已有结果时，换一个新目录，不删除旧证据后重新包装为同一次运行。

## 8 正式检索实验

脚本对同一组题分别运行三档：纯向量、向量+BM25+RRF、混合+Reranker。候选召回统一为 20，最终指标统一取前 5 个 chunk。正式实验分别运行三种 chunk_size，其余参数保持一致：

```powershell
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode retrieval --chunk-size 256 --out evaluation/baseline/retrieval256
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode retrieval --chunk-size 512 --out evaluation/baseline/retrieval512
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode retrieval --chunk-size 1024 --out evaluation/baseline/retrieval1024
```

这三次运行形成“3 个 chunk_size × 3 档检索”的真实结果。当前 build_index 固定采用 recursive；不能把以上实验写成 fixed/recursive/semantic 三种策略的检索实验。C 如果需要对比分块策略，应提供另外的完整检索实验结果。

本脚本的检索指标定义：

- Hit@5：前 5 个 chunk 至少命中一个标注的“文件名＋物理页码”证据单位，该题记 1，否则记 0。
- MRR@5：第一个匹配证据的 chunk 在前 5 名中的倒数排名；未命中记 0。
- Recall@5：前 5 个 chunk 覆盖的标注证据单位数，除以该题所有标注证据单位数；重复命中同一页只计一次。

这是文档页级标注评测，必须在报告注明。页码匹配不能证明该页上的所有结论都被精确召回；人工评分需继续核对 evidence 内容。只有一个证据单位时 Recall@5 与 Hit@5 相同，多证据问题更能体现召回差异。它不是无截断的完整 MRR，也不是对所有相关 chunk 的 Recall。检索失败题保留在分母中。

## 9 正式 RAG 和 Agent 实验

固定一个基线（这里用 chunk_size=512），分别测试直接 RAG 与 Agent。每题采用独立会话，关闭记忆；多轮能力已在单独页面测试中验证。

```powershell
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode rag --chunk-size 512 --out evaluation/baseline/rag512
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode agent --chunk-size 512 --out evaluation/baseline/agent512
```

每次运行保存 results.jsonl、per_question.csv、review.csv、metadata.json、qa_snapshot.jsonl 和汇总。metadata 保存参数、论文和 QA 指纹等复现信息；专属向量库位于各次实验输出目录。不要只留下截图而丢失原始数据。

查看 results.jsonl 中真实答案、sources、工具和 trace。Agent 的 sources 是回答引用汇总，不能当作有全局排名的 Top-5 检索列表；Agent 的检索三指标保持 N/A，正式检索成绩取第 8 步实验。延迟采用包围实际问答调用的墙钟时间，建库/首题预热另列；它是串行本地后端响应时间，不包括人工输入和浏览器打字机展示，也不证明并发性能。若需要网页端完整体验延迟，应另记录提交到显示完成的时间。

steps 为系统返回的执行步骤。汇总同时按 execution_mode 分组，ReAct 的平均 steps 可在 react 组中读取；直接路由的 1 步不能被解释为一轮完整 ReAct 推理。

独立 Token 采集工具在评测进程中读取 urllib 与 ollama.chat 的实际响应，按每题汇总所有捕获调用的 prompt_eval_count 和 eval_count。失败、流式调用或缺字段会明确标记不完整；没有完整计数的题不填成 0。最终报告同时列出 token_coverage；不足 100% 时不能声称全部请求的完整平均 Token 消耗。它不改变原前端的“未提供”显示。

工具集合匹配是自动判定的“可接受工具集合准确率”，与人工 routing 判断分别报告。后端 success 只是执行成功标志，不等于答案正确性、工具选择正确性或检索命中率。

## 10 人工评分

用 VS Code、Excel 或其他编辑器打开以下 CSV，编辑时保留原列、id、行和 UTF-8 格式：

```powershell
Invoke-Item evaluation/baseline/rag512/review.csv
Invoke-Item evaluation/baseline/agent512/review.csv
```

正确性、完整性、引用准确性分别评分 0/1/2：

| 项目 | 2 分 | 1 分 | 0 分 |
| --- | --- | --- | --- |
| correctness | 关键事实、数字、结论正确 | 核心基本正确，部分错误 | 核心结论错误、幻觉或请求失败 |
| completeness | 覆盖问题全部必答要点 | 漏掉部分要点 | 主要内容缺失或没有有效回答 |
| citation_accuracy | 来源和物理页码正确且支持关键结论 | 部分结论缺支持或引用不充分 | 关键引用错误、伪造、缺失或请求失败 |

agent 的 routing 填 1（有效工具选择）或 0（错误或无效），结合 trace 核查，不能只看答案碰巧正确。rag 的 routing 留空，不适用的字段保留空白而不是人为填满。

bad_case 使用 `retrieval`、`generation`、`citation`、`agent`，可用分号标多个类别；没有失败可写 `none`。note 写具体理由和原文位置。所有失败请求也要评分，不通过删除失败题提高平均分。人工评分最好由另一成员抽查至少 10 题，存在分歧时对照原文解决；这是质量建议，不是课程额外规定。

## 11 汇总和绘图

完成评分后再生成全体基线汇总，输出目录用一个新的名字：

```powershell
python scripts/module5_eval.py summarize --results evaluation/baseline --out evaluation/summary_baseline
```

打开 summary.csv，核对总体与四类分组、有效题目分母、失败数、人工评分覆盖数、工具标准覆盖数、工具实际可观察覆盖率和 Token 覆盖率。只有填写并被读取的评分才参与人工均分，缺失项保持 N/A。工具选择正确但调用失败的情况，执行成功率与工具选择评价应分别记录。

若现有环境缺 matplotlib，仅补装绘图依赖：

```powershell
python -m pip install matplotlib
```

生成真实数据图表：

```powershell
python scripts/module5_charts.py --summary evaluation/summary_baseline/summary.csv --review evaluation/baseline/agent512/review.csv --out evaluation/charts_baseline
```

保存检索三指标对比、平均延迟、人工三维评分、Agent 工具与步骤、完整 Token 统计、实际 Bad Case 分布。没有有效测量的图不生成，不能补造示例数据当运行结果。

截图 `10_retrieval_comparison.png`：检索表/图。截图 `11_agent_quality_performance.png`：Agent、RAG、人工评分和性能汇总，保留对应 CSV/PNG 原文件。

## 12 做至少一轮真正的优化复测

先完成并冻结基线，再从真实 Bad Case 中选问题。至少记录问题 id、预期答案/证据、实际答案、实际 Top-5/trace、失败类别、根因、修改内容、负责人、修改后复测结果。

| 失败类型 | 看什么证据定位 | 可与 C/D 实施的改进 |
| --- | --- | --- |
| retrieval | 正确页是否在 Top-5，是否被其他论文占据 | 调整 chunk_size、查询、召回候选、重排或论文范围 |
| generation | 已召回正确证据却回答错误/遗漏 | 修改 Prompt、上下文组织或生成参数 |
| citation | 答案引用的文件/页码是否支持结论 | 修复来源传递与引用组装，禁止无证据补引 |
| agent | 路由、工具输入、循环和无效调用 | 修正规则、论文指代解析、工具选择与终止条件 |

一种省改动的真实迭代是：基线采用 chunk_size=512，根据第一轮检索和 Bad Case 结果，选择 256 或 1024，再对同一组题运行 RAG/Agent。不要提前保证某个大小更好。也可以由 C/D 修复确定的 Prompt/路由问题后复测；记录代码版本与唯一主要变量。

下面以“根据证据选出 256”为例；实际选择 1024 时相应替换数字：

```powershell
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode retrieval --chunk-size 256 --out evaluation/optimized/retrieval256
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode rag --chunk-size 256 --out evaluation/optimized/rag256
python scripts/module5_eval.py run --qa evaluation/qa.jsonl --mode agent --chunk-size 256 --out evaluation/optimized/agent256
```

继续填写 optimized 下两个 review.csv，随后：

```powershell
python scripts/module5_eval.py summarize --results evaluation/optimized --out evaluation/summary_optimized
python scripts/module5_charts.py --summary evaluation/summary_baseline/summary.csv --summary evaluation/summary_optimized/summary.csv --out evaluation/charts_before_after
```

比较同一题、同一论文库、同一模型和硬件的前后结果，不用更简单的题替换失败题。数据没有改善也应如实记录原因。建议失败案例逐题对比，完整 55 题复测；CPU 耗时很长时，至少固定一组明确的复测子集并标出子集规模，不能把子集成绩与全体 55 题直接相减。

截图 `12_bad_case_before.png`、`13_bad_case_after.png`、`14_optimization_comparison.png`；三张图必须能关联同一问题 id 与前后配置。课程要求四类分析；实际未观察到某类失败时写明本次未发现及样本规模，不编造案例。

## 13 边缘场景和部署核验

在隔离的临时目录测试空库、空问题、超长问题和超大上传，不删除正式论文。下面调用真实 BackendService 的校验逻辑，不使用 mock，也不需要造出真实模型答案：

```powershell
@'
import tempfile
from pathlib import Path
from src.config import MAX_UPLOAD_BYTES
from src.frontend.service import BackendService, FrontendError
with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    backend = BackendService(data_dir=root / "data", runtime_dir=root / "runtime")
    cases = [
        ("empty corpus", "知识库为空", lambda: backend.chat("请总结论文《Attention Is All You Need》", "edge_empty", False)),
        ("empty question", "问题不能为空", lambda: backend.chat("", "edge_blank", False)),
        ("long question", "问题过长", lambda: backend.chat("x" * 12001, "edge_long", False)),
        ("oversized upload", "50 MB", lambda: backend.upload("large.pdf", b"%PDF-1.4\n" + b"0" * MAX_UPLOAD_BYTES)),
    ]
    failed = 0
    for name, expected, action in cases:
        try:
            action()
            print("FAIL", name, "unexpected acceptance")
            failed += 1
        except FrontendError as error:
            passed = expected in str(error)
            print("PASS" if passed else "FAIL", name, str(error))
            failed += not passed
    if failed:
        raise SystemExit(1)
'@ | python -
```

保存终端输出和截图 `15_edge_cases.png`，检查错误原因确实对应空库/输入长度/上传大小，不把其他异常误当通过。对话历史切换、临时文件删除、重新建库属于页面检查；并发只有部署确实支持且测试了时才报告，串行锁不代表已经完成多用户性能测试。

当前项目未提供 Dockerfile/Compose 文件；工具注册数量目前为 7，而课程模块三要求 8 个。B 应把这类验收缺口记录给 D。按团队分工由 D 提供真实部署配置和必要补齐后，B 按其 README 在干净环境复现，并记录成功/失败与日志；不要填写“Docker 一键部署已完成”。

## 14 最终报告和答辩材料

B 的模块五报告按以下顺序组织：研究方向和论文纳入规则；55 题的构建与四类分布；测试环境和代码版本；指标定义/分母/评测边界；三档检索与参数对比；RAG/Agent 性能和人工评分；四类 Bad Case；一轮优化前后结果；未完成项及局限。

汇总全项目材料时，A 提供界面及使用说明，C 提供模块一/二技术记录和检索原理，D 提供 Agent、系统架构、API、运行部署及限制，B 写模块五、核对证据并整合排版。不要让 B 凭空替其他成员编写未经核验的实现细节。

建议最终报告选 5 张核心系统图：建库状态、事实问答+引用、双论文比较、Agent 轨迹、多轮历史。模块五另放检索对比、质量/性能、优化前后三组实验图。15 张证据截图全量放附录或附件。

PPT 可安排背景与目标、实际架构、端到端展示、评测集、检索和 Agent 成绩、一个完整 Bad Case、前后优化、团队贡献与局限。手册写你实际验证过的已有环境启动、模型路径、上传建库、问答引用、会话、常见错误和停止服务。技术文档来自 C/D/A 的实做记录。

完整提交清单：

- 10–20 篇论文清单及纳入说明，符合课程允许的文件提交范围。
- 冻结的 qa.jsonl、参考答案、证据和预先标注的工具标准。
- 所有 results.jsonl、metadata.json、per_question.csv、已评分 review.csv、summary.csv。
- 图表原文件、软件检查日志、页面导出文件、截图与对应测试 id。
- 系统评测报告、Bad Case 分析、用户手册、技术设计文档、演示 PPT。
- 代码仓库、README、正确依赖/配置、贡献记录；D 提供的部署文件及 B 的复现记录。

包含向量库的 evaluation 输出可能较大，提交前可只打包原始结果、元数据、评分和图表，另说明如何重建专属向量库；保留本机运行目录用于复现。不要在完成评分前删掉结果，也不要向老师提交模板空白内容当评测成绩。

## 15 截图快速清单

| 文件名 | 必须能看见的证据 | 使用位置 |
| --- | --- | --- |
| 01_environment.png | 实际解释器、依赖、Ollama 模型 | 环境附录 |
| 02_software_tests.png | 通过/失败/跳过的完整结尾 | 软件测试 |
| 03_index_ready.png | 论文数、已向量化、真实建库结果 | 系统展示 |
| 04_factual_answer.png | 问题、答案、文件名与页码 | 答案与引用 |
| 05_source_pdf.png | 对应 PDF 物理页与原文依据 | 人工核验 |
| 06_comparison.png | 两篇论文、比较结果、双方引用 | 多论文能力 |
| 07_reasoning_trace.png | 实际工具、步骤、输入和观察 | Agent 过程 |
| 08_memory_history.png | 连续两轮与历史切换状态 | Memory 功能 |
| 09_dataset_check.png | 四类、题目数、论文数、校验结果 | 评测设计 |
| 10_retrieval_comparison.png | 三档检索与参数、三项指标 | 检索评测 |
| 11_agent_quality_performance.png | 工具/步骤、延迟、Token 覆盖、人工分数 | 系统评测 |
| 12_bad_case_before.png | 原问题 id、失败结果及证据 | Bad Case |
| 13_bad_case_after.png | 同题复测结果、修改后的配置 | 迭代核验 |
| 14_optimization_comparison.png | 同数据集的前后指标 | 优化结果 |
| 15_edge_cases.png | 空库、空/长问题、超大文件的实际拒绝理由 | 边缘测试 |

Windows 可用 Win+Shift+S 手动截取真实窗口并按表命名。图表 PNG 本身就是结果文件，无需再截图降低清晰度。截图应保留问题、结果和必要的配置/日期，隐藏无关个人信息即可。

现有 `scripts/capture_frontend.py --with-rag` 可在安装 Playwright/Chrome 后补充 5 张前端截图，它不覆盖 B 的检索、人工评分、Token 和优化评测，不是完整模块五验收。

本文件提供可执行方案和测量工具，不代表以上正式实验已经执行。最终完成以你本地保存的真实成绩、评分、案例、图表和交付材料为准。
