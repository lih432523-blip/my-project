# B 同学模块五报告：课程、模板与已完成证据审计

审计日期：2026-10-14。仅据两份本地 DOCX、已保存评测数据、QA 与 PDF 文本缓存核对；未联网、未重新调用模型，未改动原始评测数据。本文件为报告编写约束，不是新增实验结果。

## 1. 范围与两份文档的关系

- 课程方案：`D:/codex workshop/personal page/RAG Agent ass/-RAG-Agent-/南京农业大学课程实践.docx`。
- 课程报告模板：`D:/codex workshop/personal page/RAG Agent ass/-RAG-Agent-/项目交付模板.docx`。
- 本报告应定位为“智能科研助理项目——B 同学模块五评测与交付阶段报告”，正文重点为 B 已组织完成的评测、复核、分析与材料整理；不能写成全组所有功能都由 B 开发或已验收。
- 课程原文要求 **10–20 篇相关论文**，不是固定 15 篇；本次 15 篇满足数量范围。原文为 **50+ QA、四类问题**，20/15/10/10 是本团队采用的分布，不是教师规定的分类配额。
- 模板中模块交付表的“已实现/未实现/部分实现”属于待填示例，不能原样照抄为实际验收状态。身份、班级、学号、姓名未知时保留待填字段，不编造。
- 模板封面的“2026年12月30日”为模板原有日期，不是当前实验日期，不应伪装为已发生的答辩或签署日期。

## 2. 模块五要求与证据状态

| 要求 | 本次可证实的状态 | 报告严格用语 |
|---|---|---|
| 明确研究方向、10–20 篇论文 | 已有去重语料 15 篇，共 296 个 PDF 物理页；清单、SHA256 和排除理由已保存 | “构建了以视觉表征学习与图像感知应用为范围的 15 篇本地论文语料” |
| 50+ QA，事实/对比/归纳/推理四类 | 55 题，20/15/10/10；有参考答案、证据摘录、物理页码和可接受工具集合 | “固定了 55 题评测集及参考证据”；不能称模型输出本身为标准答案 |
| Hit@5、MRR、Recall | 3 个 chunk_size × 3 档检索 × 55 题 = 495 条真实记录，0 执行失败 | 写清本实现测量的是 PDF 文件名与物理页码证据匹配的 Hit@5、MRR@5、Recall@5 |
| 工具调用准确率、平均推理轮次 | Agent 55 题；自动工具集合匹配 46/55；另有 AI 辅助路由判定 45/55 | 两种口径分开。总体步骤 1.2 混合直达工具与 ReAct；ReAct 27 题平均 1.407407 步，不能将总体步骤直接称为纯 ReAct 推理轮次 |
| 平均延迟、Token 统计 | 平均问答调用墙钟延迟 64.095769 s；均 Token 4394.6，计数覆盖 100% | “串行本地后端调用测量”；不含人工输入与浏览器渲染，不证明并发性能 |
| 人工正确性/完整性/引用准确性 | 55 题三个维度已由 AI 结合输出和本地证据辅助评分；尚未提供独立人工评价 | 必须显著标注“AI 辅助评分，待独立人工复核”；不能称“人工评测已完成” |
| 参数对比图 | 三尺寸三档检索的真实质量/时延对比已完成 | “本评测集下的参数比较”；单次串行实验，不声称统计显著性或全局最优 |
| 四类 Bad Case、根因分析 | 已有 retrieval/generation/citation/agent 标签与逐题理由、修复交接 | “AI 辅助分类与证据审阅”；标签重叠，不能将四类计数之和当作失败题数 |
| 至少一轮迭代优化，前后对比 | 尚未完成修改后生成/Agent 质量复测；当前为参数比较与问题定位 | “完成参数对比和优化方案，尚待按固定题集实施质量优化复测”；不能写“优化闭环已完成” |
| 技术设计文档、用户手册等 | 本次可整理 B 的评测设计和已存在运行方案；全项目最终说明需 A/C/D 补充核实 | B 的评测接口/数据流可如实写，不能伪造其余成员未提供的已验收实现记录 |

## 3. 已保存结果的正确引用

### 3.1 Agent 基线

- 原始运行：`evaluation/runs/agent55_20261014_175735_da23d1/`；55 个唯一题号，2 个执行失败。
- AI 辅助评分后的汇总：`evaluation/ai_review_20261014_191222/summary/summary.csv`。原运行目录 18:35 生成的 `summary.csv` 是评分前快照，质量评分均为空，不应混用。
- 评分报告与审计：`evaluation/ai_review_20261014_191222/AI评分报告.md`、`scores_audit.json`。
- 53/55 = 96.36% 是 **执行成功率**，并非答案正确率。
- 46/55 = 83.64% 是 **预标注可接受工具集合的自动匹配率**，并非答案正确率，也不等同于 AI 结合参数/轨迹判定的路由有效率 45/55 = 81.82%。
- 正确性、完整性、引用准确性均分分别为 **0.9818/2、0.8182/2、0.9636/2**。它们是 0–2 量表均分，不能直接标作二元“正确率”；即使除以 2 归一化，也必须称归一化量表分数。
- 汇总列 `manual_n=55` 只是脚本“可读取评分字段数”的历史命名，不证明评分来自人工。正文和图注都须说明实际评分主体为 AI 辅助。
- Agent 的 Hit@5/MRR/Recall 为 N/A 是模式边界；Agent `sources` 不是统一排名的 Top-5 检索序列。检索成绩应引用独立 retrieval 实验。
- F07/F12 均误选 `paper_metadata` 并报 `TypeError: sequence item 0: expected str instance, dict found`，可作为真实优先修复案例；应保留原失败结果，不能删除或用续跑结果悄然替换。
- 续跑保留了其他运行的 origin 记录，不得以最后一次进程开始到结束的时长冒充全部 55 题总运行时长。平均延迟应按逐题 `wall_latency_s` 计算。

### 3.2 检索参数实验

- 汇总与复核：`evaluation/retrieval_comparison_20261014_214329/comparison.json`、`检索参数对比报告.md`。
- 原运行：`retrieval55_20261014_193104_b35edd`、`retrieval55_20261014_210831_0865ca`、`retrieval55_20261014_212257_280fb9`。
- 3 个分块大小全部使用 **recursive 字符分块**；绝不能写成 fixed/recursive/semantic 三种策略的检索质量实验。
- 候选召回 20，最终 Top-5；重叠参数配置为 50，但当前递归实现不保证每对输出块之间均重叠 50 字符。报告可写“overlap 参数为 50”，不应作实现保证。
- 页级指标定义：Hit@5 为至少命中一项标准证据页的题目比例；MRR@5 为第一项相关证据块在前 5 名的倒数排名均值；Recall@5 为覆盖的不同金标证据页单位数/全部金标证据页单位数的题均值。重复同页不重复计数。
- `chunk_size=512 + hybrid_rerank` 为 46/55 命中，Hit@5 83.64%、MRR@5 0.6245、Recall@5 72.73%，平均检索 1.7860 s；1024 重排同样命中 46/55，但 MRR@5 0.5921、Recall@5 71.36%、3.2577 s。
- 可写“512 在本次数据上兼顾质量与时延，适合作为后续固定基线”，不能称“已证明所有场景下 512 最优”。
- 512 使用复用索引，`build_index_s=0` 不代表新索引构建零耗时，也不能同其他新建索引直接比较建库速度。
- 三档检索参数对比不是生成/Agent 修复后的质量提升证据，不能充当课程要求的已完成质量优化闭环。

## 4. 七章模板映射建议

| 模板章节 | B 阶段报告可写内容 | 范围限制 |
|---|---|---|
| 一、项目概述 | 背景不超过 200 字；目标；实际技术栈；本报告为模块五阶段评测 | 不以产品宣传或方案中的示例成绩替代实测 |
| 二、团队分工说明 | A 前端 15%、B 评测与文档 15%、C RAG 35%、D Agent/集成 35%，合计 100%；姓名待填 | 比例来自团队方案，不是自动证明的实际代码贡献；标明团队约定 |
| 三、模块交付物清单 | 按模板逐模块给表；模块五细列已完成/部分完成/待完成；其他模块列“评测依赖/接口可观察，待对应负责人最终验收” | 不能只因评测脚本能调用就宣布全部模块完成；不替 C/D 写虚假完成证明 |
| 四、技术实现记录 | 保留 4.1–4.4 的项目定位和依赖概述，4.5 为主要篇幅：数据构建、指标定义、55 题 Agent、495 条检索、AI 辅助评分、Bad Case、效能权衡 | 系统架构图可画实际依赖示意，必须注明架构/数据流图，不冒充运行截图 |
| 五、技术设计文档 | B 评测流水线架构、输入输出、QA schema、独立运行目录、指纹、Token 采集、汇总/绘图接口、配置与复现边界 | 区分被测系统与评测系统；全系统 API/部署实现由 C/D 核实 |
| 六、总结与展望 | 已完成的数据与基线事实、主要失效原因、下一步优先修复与独立人工复核计划 | 优化计划不得写为既成成果；无直接 RAG 基线则不作真实 RAG/Agent 答案质量对照 |
| 七、附录 | 15 论文清单、关键运行目录/哈希、数据文件说明、评分口径、代表题证据、复现命令、待补项表 | 附录代码树按实际项目而不是照抄模板示例；命令使用真实 app.py 和模型路径 |

模板还规定：目录黑体二号加粗；章标题黑体三号加粗；正文示例为仿宋四号、1.5 倍行距。若采用学术 LaTeX 版式，可以保留七章顺序及封面待填项，并让可读性与表格排版服从用户希望的美观学术报告；避免宣称精确复刻 Word 模板而实际字体/字号不一致。

### 4.1 必须主动披露的截图缺口

**真正的《项目交付模板.docx》4.4.2 明确要求“附上3–5张界面截图，标注核心功能区域”。** 课程方案正文虽然没有截图数量要求，但模板有，所以本次全项目交付仍缺真实 UI 截图。B 的数据图、流程图、架构图与 PDF 证据图都不能冒充前端界面运行截图。

建议报告写：“本报告提供模块五的评测图表与原始记录；模板 4.4.2 所要求的 3–5 张真实界面截图尚待前端/集成负责人补充。”不要放虚构网页 mockup 充数，也不要把 LaTeX 表格截图标成“系统运行截图”。

## 5. 不可虚构、不可过度推断项

1. 独立人工评审、双人一致性、专家打分、盲评或人工复核 55 题均未被证据证明。
2. 55 题平均质量提升、修复后的零失败、优化后分数与新版本前后曲线尚不存在，不可绘制猜测值。
3. 未有直接 RAG 生成基线，不能画真实 RAG 与 Agent 质量/延迟胜负比较；检索耗时不能放在同轴当 RAG 端到端耗时。
4. recursive 的 256/512/1024 是大小实验，不是三类分块策略质量对比；已有块数量统计也不能替代检索质量测量。
5. 单次串行 CPU 实验不证明统计显著、并发能力、产品级稳定性或通用最优；图上不要伪造误差棒、置信区间或 p 值。
6. F07/F12 的失败不能删除；`success=True` 也不能证明答案有用，例如 S10 可能只产生诊断文本。
7. 四类 Bad Case 的 10/39/42/11 为 AI 辅助重叠标签计数，不是独立互斥错误分布；不应画为加和 100% 的饼图。
8. 源 PDF 证据页命中不等于整页被输入模型，不等于语义证据充分，更不等于引用句句正确。
9. 团队成员姓名、学号、硬件品牌/显存、未测的 GPU 速度、Docker 成功部署、真实页面截图、教师签名或成绩不得补造。
10. LaTeX 中出现的“完成”“实现”“验证”需有对应文件或实验支持；其余用“设计”“建议”“待复核”“待补齐”。

## 6. 15 篇本地论文题名与物理页数核对

清单来自 `evaluation/corpus_manifest.json`；题名同时与 `evaluation/qa.jsonl` 中题目及 `.runtime/module5_sources/<stem>.json` 第一页正文核对。页数为 manifest 物理页数，并与各缓存页数一致。共 **15 篇、296 页、15 个不同 SHA256**；不是从网页补齐的书目信息。

| 编号 | 本地文件 | 题名 | 页数 |
|---|---|---|---:|
| P01 | `2311.10122v3.pdf` | Video-LLaVA: Learning United Visual Representation by Alignment Before Projection | 14 |
| P02 | `2401.09417v3.pdf` | Vision Mamba: Efficient Visual Representation Learning with Bidirectional State Space Model | 14 |
| P03 | `An_Image_is_Worth_16x16_Words.pdf` | An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale | 22 |
| P04 | `applsci-16-10003.pdf` | Multi-View Semantic–Geometric Perception for Post-Disaster Flexible Suction with Metric 3D Scene Reconstruction | 26 |
| P05 | `attention_is_all_you_need.pdf` | Attention Is All You Need | 15 |
| P06 | `Deep_Residual_Learning_for_Image_Recognition.pdf` | Deep Residual Learning for Image Recognition | 9 |
| P07 | `diagnostics-16-03259.pdf` | SBRF-Det: Scale-Boundary Representative Fusion for Multi-Finding Detection in Panoramic Dental Radiographs | 35 |
| P08 | `energies-19-04788.pdf` | A Thermal-Aware Infrared–Visible Image Fusion Method for Defect Detection in Power Transmission Equipment | 58 |
| P09 | `engproc-157-00021.pdf` | Vision-Guided Cone Manipulation with Collaborative Robotic Arm | 10 |
| P10 | `engproc-159-00004.pdf` | Occlusion-Aware Watermelon Size Estimation Using YOLO11-OBB and Amodal GAN | 8 |
| P11 | `How_to_Choose_a_Suitable_Method_in_Image_Semantic_Segmentation-An_Experimental_Study.pdf` | How to Choose a Suitable Method in Image Semantic Segmentation—An Experimental Study | 6 |
| P12 | `Kerssies_How_to_Benchmark_Vision_Foundation_Models_for_Semantic_Segmentation_CVPRW_2024_paper.pdf` | How to Benchmark Vision Foundation Models for Semantic Segmentation? | 10 |
| P13 | `oral-06-00131.pdf` | An Intelligent Framework for Tooth Segmentation and Classification Through Fusion of Transfer Learning with Advanced Optimization Algorithms Using Biomedical Images | 19 |
| P14 | `sensors-26-06403.pdf` | Zero-Shot Water Monitoring from Fixed Drainage Surveillance Imagery Across Day/Night and Rain/No-Rain Conditions: A SAM 3 Benchmark at 25 Urban Sites | 23 |
| P15 | `sustainability-18-10291.pdf` | Constructing a Xiangyunsha Defect Dataset and a Lightweight Detection Model for Sustainability | 27 |

P11 的大小写、连接符在 QA 中存在两种规范化写法，但对应同一 PDF，不计作两篇。P05 为 Transformer 理论基础、不是视觉应用论文，应在纳入规则中明确其作为 P03/P02 等视觉表征工作的基础文献；不能声称 15 篇全部是纯视觉应用论文。

已排除：`1706.03762v7.pdf` 与 P05 完全重复；`Attention Is All You Need.pdf` 为同论文逐页文本重复；`engproc-159-00004 (1).pdf` 与 P10 完全重复；`Prompt Engineering_v7.pdf` 因不属于既定视觉研究主题排除。重复版本不计入 15 篇数量。

## 7. 可直接采用的报告范围声明

> 本报告依据课程实践方案及课程报告模板，整理成员 B 在模块五已完成的语料与评测集构建、Agent 基线测试、检索参数实验、AI 辅助答案审阅与 Bad Case 分析。结论仅适用于所固定的本地语料、55 题评测集和已记录配置。55 题质量分数来自 AI 辅助量表评分，尚待独立人工复核；本阶段尚未完成修改后生成/Agent 质量复测及全项目真实界面截图补充。报告据实展示已完成成果，并将未完成要求列入后续验收清单。
