# 55 题评测集

研究范围为视觉表征学习与图像感知应用。评测语料从项目现有 PDF 中选取 15 篇不重复的研究论文，覆盖 Transformer、ViT、ResNet、Vision Mamba、多模态表征、分割基准，以及工业、农业、医疗和监控图像感知应用。论文清单与文件指纹见 corpus_manifest.json。

qa.jsonl 包含事实 20 题、对比 15 题、归纳 10 题、推理 10 题。每题提供中文问题、参考答案、可接受工具集合，以及源 PDF 文件名、从 1 开始的物理页码和原文证据。题目清单见 qa_questions.md。

corpus/ 使用源论文的独立目录项，保持原始 data/ 内容。重复的 Transformer 文件、重复的西瓜论文文件以及非视觉研究论文的 Prompt Engineering 指南不纳入本次语料。正式调用需使用 corpus/，不能把原始 data/ 的重复文件重新混进来。

在你已激活的 Python 环境中，从任何工作目录执行一条命令：

```powershell
python "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project\scripts\run55.py"
```

默认运行全部 55 题的端到端 Agent 评测，chunk_size=512。脚本自动定位评测集和去重语料，并创建独立时间戳输出目录，保存为 evaluation/runs/agent55_日期_时间_编号/。模型加载、建库、预热和 55 题问答会实际执行，Ollama 与 BGE 模型需按团队已有运行环境准备好。

开始前先用 `ollama pull qwen2.5:7b` 准备模型，用 `ollama run qwen2.5:7b "只回复OK"` 验证实际生成。模型缺失的错误日志用于运行诊断，不是可用的论文答案质量成绩。2026 年 10 月 11 日起，RAG/Agent 评测在建库前增加模型服务和最小生成检查，配置故障提前停止。用 `run55.py --smoke --limit 3` 可先跑 3 题；试跑仍需载入检索模型并建立索引，其结果与正式成绩分开保存。

每题的答案、引用、工具、耗时和实际 Token 计数保存到结果目录。review.csv 的人工评分初始留空，需按参考答案和证据核对填写；参考答案不会作为问题上下文传给被测模型。数据集的准备与校验不代表模型已通过评测。

2026 年 10 月 11 日显存故障后的复测：在原 NLP 环境中，保留 qwen2.5:7b、context=4096，设置每个模型请求 keep_alive=30m，复用已有索引，真实 3 题均执行成功并返回引用与完整 Token 计数。该检查只确认运行链路，答案正确性仍需人工评价。试跑记录在 runs/agent55_smoke3_20261011_223155_eaa599/。

继续完整 55 题可执行：

```powershell
& "D:\Anaconda\envs\NLP\python.exe" "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project\scripts\run55.py" --reuse-index latest --context-size 4096
```

复用会核对语料指纹、分块参数、Embedding 模型、索引相关源码，以及全部已存 chunk 的 ID、内容、文件名和页码。不匹配时拒绝复用。仍需加载检索模型、解析 PDF 并恢复 BM25，但省去向量化；新结果目录中的 build_index_s=0 代表复用，不能当成新建库成绩。原始索引与结果保留，新的问答结果写入新目录。模型会在请求后驻留 30 分钟；评测结束后可执行 `ollama stop qwen2.5:7b` 释放本次模型资源。

可选参数 --llm-model 明确更换模型，--llm-device cpu 将所有模型请求设置 num_gpu=0，--context-size 固定上下文。更换模型/设备/上下文是新的实验配置，metadata 会记录；CPU 模式还需考虑系统内存容量和运行速度，不能仅凭 CUDA 不再报错认定所有请求成功。

如需另外测试检索三档或直接 RAG，可在同一命令末尾加 --mode retrieval 或 --mode rag。仅核查数据且不加载模型时加 --check-only。

检索指标按文件名与物理页码计算，是证据页级 Hit@5、MRR@5、Recall@5；人工引用评分继续核对具体内容。不同论文的不同数据集与任务指标不能直接用于排列模型优劣。

2026 年 10 月 14 日的中断记录：Windows 在 16:48:37 报告 NLP 环境的 python.exe 在 PyTorch 的 c10.dll 中以 0xc0000005 崩溃。结果文件实际保存 23 题，至 C03；下一题为 C04。该证据能确认原生进程崩溃，不能确定具体模型操作或认定为显存不足。诊断见 ../docs/module5_crash_20261014.md。

从最近一次未完成的正式运行续跑：

```powershell
& "D:\Anaconda\envs\NLP\python.exe" "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project\scripts\run55.py" --resume latest
```

也可把 latest 换成明确的旧结果目录。续跑自动读取原模型、设备和上下文设置，并复用原索引；严格核对 QA、语料、后端源码、Python/依赖和模型 digest。已有结果（包括已记录的失败）连同来源编号与已有人工评分写入新目录，只执行缺失题；原 metadata.json、results.jsonl 和题集快照不修改。本次应显示保留 23 条、补跑 32 条，正式进度从 [start 24/55] C04 开始，初始化和预热先执行。

新脚本为每题写入开始/完成状态并同步结果到磁盘，终端输出及 Python faulthandler 信息保存在 evaluation/logs/。这些机制帮助保全结果和定位再次发生的底层故障，不代表已经消除 c10.dll 崩溃。续跑结果属于多段实验；新进程的启动/结束时间及初始化耗时不能作为完整 55 题的全程耗时。旧记录没有保存的 Token 仪表哈希和检索模型 revision 无法追溯补证，metadata 中会注明。

同日的 metadata.json.tmp → metadata.json / WinError 5 中断另行修复：JSON 改用唯一临时文件，对 Windows 的 5/32/33 替换错误执行有限退避重试。若目标持续被锁，完整且已同步的元数据临时文件作为恢复快照保留，评测继续；启动器、续跑、索引复用及汇总统一读取同一 run_id 的最高 metadata_revision。请保留结果目录中的 .metadata.json.*.tmp 文件，它们可能是最新进度。创建/写入/同步文件失败仍会报告，不会被当作临时锁忽略。结果完成题数以 results.jsonl 的实际完整行数为准。

已在 Windows 上用禁止文件替换的真实文件句柄验证短暂锁自动重试、持续锁恢复快照，并对续跑全过程注入持续锁验证得到 55 条唯一结果；后者使用模拟后端，未生成正式模型成绩。17:42 的运行有 6 条重复测试结果，16:22 的运行仍保存 23 条。为减少重复运行，可明确续跑 23 条的原目录：

```powershell
& "D:\Anaconda\envs\NLP\python.exe" "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project\scripts\run55.py" --resume "D:\codex workshop\personal page\other agent\my-project\rag_project_20261007\rag_project\evaluation\runs\agent55_20261014_162205_a10fcc"
```
