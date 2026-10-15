# B 同学：55 题完成后的操作清单

本清单对应 2026-10-14 完成的真实结果：evaluation/runs/agent55_20261014_175735_da23d1。下面的命令均使用原 NLP 环境，在 PowerShell 中执行。它提供后续操作，不代表人工评分、检索对照及优化已经完成。

2026-10-14 后续更新：按用户要求，review.csv 已完成 55/55 题的 AI 辅助评分，原始未评分表已备份。逐题理由、核验依据、新汇总和图表位于 evaluation/ai_review_20261014_191222/。这是 AI 辅助评价，尚不属于独立人工复核。以下表格的“人工评分0/55”保留为18:35运行结束时的原始状态；现在查看评分结果请使用新评审目录的 summary/，而不是运行刚结束时生成的旧 summary.csv。检索对照和优化复测仍待完成。

2026-10-14 21:43 更新：256/512/1024 三组递归字符分块检索评测均已完成，各165条、总495条、0失败。对比图、数值核验和报告位于 evaluation/retrieval_comparison_20261014_214329/。本次建议后续固定512＋混合检索＋重排。接下来由C/D按模块实施明确的Bad Case修复，B组织同题复测和报告；优化尚未实施或验证。这里完成的是递归分块的三个大小对比，三种分块策略的完整检索质量对比仍不能据此宣称已完成。

## 1 当前已完成什么

| 项目 | 实际结果与解释 |
| --- | --- |
| 题目 | 55 条、55 个唯一编号，事实 20 / 对比 15 / 归纳 10 / 推理 10 |
| 执行状态 | completed_with_failures：55 题全部处理完，53 题 success=true，F07、F12 失败 |
| 执行成功率 | 53/55 = 96.36%，不能写成答案正确率 |
| 工具集合匹配率 | 46/55 = 83.64%，依据预先标注的可接受工具集合；不等于人工路由评分 |
| 平均单题延迟 | 64.10 秒；P95 为 168.35 秒；不含建库和预热 |
| 平均 Token | 4394.6，prompt + completion，完整计数覆盖 55/55 |
| 执行步数 | 全体平均 1.20；仅 ReAct 组平均 1.41（27 题），其余为直接工具路由 |
| 人工评分 | 0/55，正确性、完整性和引用准确性尚无成绩 |
| Hit@5 / MRR@5 / Recall@5 | Agent 汇总为 N/A；需另跑检索实验 |

本次是多段续跑：前 23 条来自原运行，之后补跑 32 条。报告中注明续跑；新目录 17:57–18:35 的时间不能当作全部 55 题总耗时。保留完整结果目录、日志和来源记录；后续以这一份完整目录作为 Agent 基线，不把旧中断目录或试跑混入汇总。

## 2 现在先打开人工评分表

在同一个 PowerShell 窗口先执行这一段，后面命令会复用这些变量：

```powershell
$projectRoot = "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project"
$pythonExe = "D:\Anaconda\envs\NLP\python.exe"
$runDir = Join-Path $projectRoot "evaluation\runs\agent55_20261014_175735_da23d1"
Set-Location -LiteralPath $projectRoot
Invoke-Item -LiteralPath (Join-Path $runDir "review.csv")
```

用 Excel 或编辑器打开即可。只填写下列人工字段，保留其他列、55 行、编号、run_id 和原始答案，保存为 UTF-8 CSV。不要因为答案差或请求失败删除行。

| 字段 | 填写方法 |
| --- | --- |
| correctness | 2：关键事实/数字/结论正确；1：部分正确；0：核心错误、幻觉或没有有效回答 |
| completeness | 2：必答点完整；1：缺部分要点；0：主要内容缺失或请求失败 |
| citation_accuracy | 2：来源及物理页码正确并支持关键结论；1：部分支持不足；0：关键引用错误、缺失或请求失败 |
| routing | 1：实际工具选择有效；0：错误或无效。结合题意及实际调用，独立于自动集合匹配率 |
| bad_case | retrieval / generation / citation / agent，可用英文分号多选；没有问题填 none |
| note | 写具体错误、遗漏、引用文件和页码；不要只写“回答不好” |

每题按 question → reference_answer → answer → gold_evidence 的顺序核验。实际引用列表及完整执行信息在同目录 results.jsonl 的 sources、raw_result 中；参考答案和逐字证据也可在 evaluation/qa_questions.md 查阅。源 PDF 在 evaluation/corpus；page 是 PDF 从第一页开始的物理页码。

优先核查以下已有线索，再完成全部 55 题。它们是核查提示，人工分数保持留空，由实际证据决定：

| 题号 | 本次输出中的线索 |
| --- | --- |
| F07、F12 | paper_metadata 报 TypeError：expected str instance, dict found，执行失败 |
| F03 | 问具体实验事实，却返回 Paper Metadata；核对是否漏答和路由错误 |
| F02 | 回答将 3.57% 说成验证集指标；对照参考答案和原文核查测试集/验证集混淆 |
| C03 | Vision Mamba 被匹配到 Kerssies 的分割基准 PDF，核对论文范围和引用 |
| S06 | 单篇总结进入双篇 paper_compare，输出混入另一篇论文 |
| S10 | success=true，但答案为“两篇论文被解析到了同一个 PDF”的提示；仍需按实际回答评分 |

对 retrieval 标签，应进一步确认证据确实没有被检索到；仅凭最终答案错误不能区分检索失败和生成错误。没有观察到某类案例时写“本次未发现”，不编造四类各一题。

## 3 评分后重新汇总并生成图表

保存并关闭评分表，再执行。输出带时间戳，避免覆盖之前的汇总：

```powershell
$tag = Get-Date -Format "yyyyMMdd_HHmmss"
$summaryDir = Join-Path $projectRoot "evaluation\summary_agent_$tag"
$chartDir = Join-Path $projectRoot "evaluation\charts_agent_$tag"
& $pythonExe "$projectRoot\scripts\module5_eval.py" summarize --results $runDir --out $summaryDir
```

查看新生成的 summary.csv：总体行是 category=all 且 execution_mode=all。确认 correctness_n、completeness_n、citation_accuracy_n 均为 55；若 routing 也全部评分，routing_n 应为 55。各列分母不满时先检查漏填、空白和保存路径，不用 N/A 代替人工分数。确认后绘图：

```powershell
& $pythonExe "$projectRoot\scripts\module5_charts.py" --summary "$summaryDir\summary.csv" --review "$runDir\review.csv" --out $chartDir
Invoke-Item -LiteralPath $chartDir
```

如缺 matplotlib，只在原环境补装后重新执行绘图：

```powershell
& $pythonExe -m pip install matplotlib
```

预期得到平均延迟、人工三维评分、工具与步骤、Token 图；有实际 Bad Case 标签时还会生成案例分类图。保存 PNG 原文件，报告直接使用，不必截图图表。未评分时不应出现人工质量图。

## 4 补齐检索指标和参数对比

当前只完成 Agent 基线，Hit@5=None 是该模式的指标边界。它的引用汇总不具备统一 Top-5 排名，不能直接用来计算检索指标。

先跑 chunk_size=512 的三档检索，复用已有 2082 个 chunk，不调用 Ollama 生成答案：

```powershell
& $pythonExe "$projectRoot\scripts\run55.py" --mode retrieval --chunk-size 512 --reuse-index latest
```

脚本对每题实际运行 vector、hybrid、hybrid_rerank，55 题共 165 条结果。完成后把终端 Output 路径记为这次的检索目录。查看该目录 summary.csv 的三条总体行，使用实际 Hit@5、MRR@5 和证据页级 Recall@5。

继续做分块大小对比；256 和 1024 与旧 512 索引不同，需各自新建，不加 --reuse-index：

```powershell
& $pythonExe "$projectRoot\scripts\run55.py" --mode retrieval --chunk-size 256
& $pythonExe "$projectRoot\scripts\run55.py" --mode retrieval --chunk-size 1024
```

依次运行，保持相同题集、语料、模型和硬件。每次保存 Output 路径。三次结果的 summary.csv 共同提供三种分块大小 × 三档检索对比。用实际路径替换下面三个字符串后绘图：

```powershell
# 路径占位符必须换为上述三次真实 Output 目录；不要原样执行本段。
& $pythonExe "$projectRoot\scripts\module5_charts.py" --summary "512检索结果目录\summary.csv" --summary "256检索结果目录\summary.csv" --summary "1024检索结果目录\summary.csv" --out "$projectRoot\evaluation\charts_retrieval_$tag"
```

如果还需要直接 RAG 与 Agent 的对照，可另运行 --mode rag --chunk-size 512 --reuse-index latest，并对其 review.csv 独立评分。课程关键指标及优化证据优先完成；这项作为对照实验单独报告。

## 5 从真实 Bad Case 做一轮优化

先保留并完成当前基线评分，再选择一个明确问题，与负责后端/Agent 的同学修正。已有优先方向是：元数据返回值的类型处理、事实问题误入元数据工具、单篇总结误入比较工具、论文名称与 PDF 匹配。

每个案例记录：题号、原问题、参考答案/原文、旧输出、实际工具/来源、失败类别、原因、修改点和负责人。实现修改后，在同一语料和 55 题上启动新实验；不要使用 --resume 搬运旧答案作为优化结果。

若仅修改路由、生成或来源匹配且分块与 Embedding 不变，可复用经过校验的索引：

```powershell
& $pythonExe "$projectRoot\scripts\run55.py" --mode agent --chunk-size 512 --reuse-index latest --context-size 4096
```

若改变分块大小，按实际参数启动并新建相应索引。对新结果另行人工评分、汇总，比较相同题号。优化前后保持主变量明确；没有改善也如实写结果，不先承诺提升。多次相同配置的基线/优化目录分开汇总，不对整个 evaluation/runs 一次性 summarize。

## 6 现在起需要保存的截图

课程没有限定截图张数。以下是这一阶段最有用的证据；PNG 图表保留原文件即可。

| 建议文件名 | 截什么 |
| --- | --- |
| 16_agent55_complete.png | 真实终端的最后题 R10、55/55、Saved 输出路径；或完整结果文件与汇总表 |
| 17_human_review.png | 已填写的正确性、完整性、引用与路由字段，保留题号 |
| 18_pdf_evidence.png | 一个代表题的实际回答、来源，以及对应 PDF 物理页原文 |
| 19_retrieval_metrics.png | 三档检索与分块参数的真实指标表；图表直接保留 PNG |
| 20_badcase_before.png | 真实错误题 id、原问题、旧回答、工具/来源和原文证据 |
| 21_badcase_after.png | 同一题修改后的真实结果，带新结果目录或配置 |
| 22_optimization_comparison.png | 同一题集的优化前后真实指标表或图 |

已关闭的终端无需重新运行 55 题来补截图。可用完整结果及其 summary.csv 截图说明完成情况；不要制造假的终端完成画面。

## 7 整理 B 的报告和交付

报告依次写：研究方向及 15 篇论文的纳入规则；55 题四类分布和证据标注；环境与指标定义；检索/分块对比；Agent 执行性能与人工质量；四类 Bad Case 核查；一轮优化前后结果；续跑及实验限制。

交付保留 QA/证据、论文清单、完整 results.jsonl/metadata 与恢复快照、已评分 review.csv、summary、图表、案例和截图。技术设计、部署和界面资料继续由对应成员提供；完整团队材料与先前步骤见 docs/member_B_runbook.md。当前核心下一步是完成 55 行人工评分，而后补齐检索参数实验与一轮优化，不能只凭跑完 55 题宣布模块五全部完成。
