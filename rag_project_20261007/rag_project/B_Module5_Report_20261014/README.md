# 成员 B：模块五评测与项目交付报告

打开 `main.pdf` 阅读，编辑 `main.tex` 修改正文。整个文件夹可以复制、压缩或上传；编译报告不需要访问原项目。

## 包含内容

- `main.tex`：按课程交付模板七章组织的中文 LaTeX 主文件，包含摘要、职责、逐模块交付、实验、技术设计、总结和附录。
- `main.pdf`：本次编译的阅读版。
- `figures/`：8 张图，每张含可缩放矢量 PDF 与高分辨率 PNG。
- `tables/`：7 个由冻结数据生成的 LaTeX 表片段，包含九组配置、Agent 指标、评分、案例、逐题明细、环境与论文清单。
- `data/report_data.json`：本报告固定输入（15 篇、296 页、55 题 Agent、495 条检索与评分）。
- `data/qa.jsonl`、`scores_audit.json`、`grading_verification.json`：问题与参考证据、逐题评分原因、原始结果未被评分修改的验证记录。
- `data/source_manifest.json`：原始输入 SHA-256 与运行元数据；绝对路径只用于追溯，不是编译依赖。
- `data/requirements_audit.md`：课程与交付模板的逐项核对。
- `scripts/`：图、表、数据冻结及交付检查脚本。
- `build.ps1`：调用现有 XeLaTeX 或 Tectonic 编译；不自动安装软件，不改系统环境。

## 编译

在本文件夹打开 PowerShell。已安装 XeLaTeX 时执行：

```powershell
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Tectonic 用户执行 `tectonic main.tex`。中文默认优先采用 Windows 仿宋/黑体；无此字体时使用 Fandol。源文件按 UTF-8 保存。请使用支持 XeTeX 的编译方式；不要用 pdfLaTeX。

## 重建图表

需要 Python 3、NumPy、Matplotlib。使用你现有的环境即可；图表脚本只读取本包 JSON，不会启动 Ollama、重新评分或重跑模型。

```powershell
python .\scripts\make_figures.py
python .\scripts\make_tables.py
```

`freeze_data.py` 是原项目资料冻结入口，需要原项目 `evaluation/`，不用于日常编译。若重新冻结，须重新核对论文题名、评分来源和所有指标，再生成全部图表。当前 `report_data.json` 是交付用固定快照。

## 使用与提交前需填写的内容

1. 填写 `main.tex` 封面的姓名、学号、班级、指导教师，以及团队成员姓名。
2. 55 题分数是 **AI 辅助量表评分，未做独立人工复核**；不要把标签改成人工实验或教师评分。完成独立复核后应另存日期、评审者与逐题记录。
3. 本轮比较的是 **recursive 字符分块的 256/512/1024 长度**，没有完成三类分块策略的检索质量实验。
4. 工程恢复与参数筛选已完成；修复后的生成/Agent 质量复测尚未完成。报告未编造优化后数值。
5. 全项目模板 4.4.2 要求的 **3–5 张真实界面截图** 尚待 A/D 补齐。八张数据图/架构图不能替代它们。

## 图表索引

| 文件 | 内容 |
|---|---|
| `01_dataset_profile` | 问题类型与 15 篇论文的金标证据覆盖 |
| `02_retrieval_quality` | 九组配置的 Hit@5、MRR@5、Recall@5 |
| `03_retrieval_tradeoff` | 质量与查询时延权衡、索引规模 |
| `04_paired_hits` | 55 题 × 九配置逐题命中矩阵 |
| `05_agent_performance` | Agent 时延分布、Token 与执行模式 |
| `06_ai_quality` | AI 辅助评分分布、分任务均分 |
| `07_bad_cases` | 四类多标签错误计数与共现 |
| `08_architecture` | 被测系统与 B 评测流程示意 |

原始论文 PDF 未随包复制；问题参考摘录、文件名和物理页码均保留在数据中。需要对照全文时，使用原项目 `evaluation/corpus/`。

便携编译器来源：[Tectonic 官方发布](https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0)。报告包没有捆绑编译器或改变原 NLP 环境。
