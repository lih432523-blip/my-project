# 2026-10-15 GitHub 同步记录

本次将成员 B 的关键代码与已完成结果同步至既有项目仓库。报告与正式实验日期保持 2026-10-14，不将上传日期写成新实验日期。

## 同步范围

- `src/config.py`、`src/agent/llm_client.py`、`src/generation/rag_pipeline.py`：本地模型上下文、设备选项、模型驻留等共享请求配置。
- `scripts/run55.py`、`module5_eval.py`、`module5_tokens.py`、`module5_charts.py`：评测入口、模型预检、受校验的索引复用、逐题保存、中断续跑、Windows 文件替换恢复、实际 Token 计量与汇总绘图。
- `evaluation/`：55 题及原文证据、15 篇语料指纹、正式 Agent 与三组检索记录、AI 辅助评分审计、检索对比与优化交接。
- `evaluation/runs/agent55_20261014_162205_a10fcc/`：正式续跑的 23 题来源，只用于追溯，不能与最终 55 题重复计数。
- `docs/member_B_runbook.md`、`member_B_after55.md`、`module5_crash_20261014.md`：运行与异常诊断说明。
- `B_Module5_Report_20261014/` 和同名 ZIP：LaTeX 源、已编译 PDF、8 组图、7 个数据表片段、冻结数据与重建脚本。

本地原始论文、模型、向量库、运行缓存、会话数据、临时故障/冒烟目录及 IDE 文件不在同步范围内。Git 忽略规则仅防止误提交，不删除这些本地文件。

仓库 `.gitattributes` 对实验数据、报告及参与运行指纹的代码关闭自动换行转换；上传前逐一核对 Git 暂存对象与本地原始文件，避免 Windows 的 CRLF/LF 转换使审计 SHA-256 失效。评分前备份和 23 题续跑来源保留在正式目录中，供追溯原评分字段及继承记录。

## 上传前验证

1. `python scripts/run55.py --check-only`：通过；55 题、15 个 PDF、四类题型分布正确。该检查验证结构与源文件存在，不等同于答案质量验证。
2. `python B_Module5_Report_20261014/scripts/verify_package.py --check-original`：通过；28 页报告、8 组图、7 个表片段、55 题 Agent、495 条检索记录及原始输入 SHA-256 一致。原有版面核验记录随报告保留。
3. 关键 Python 文件 AST 解析：通过；未检出嵌入凭据或个人用户目录硬编码。
4. 原有 `python -m unittest discover -s tests -v`：共 16 项，15 项通过，1 项 UI 测试报错。当前 NLP 环境的 Streamlit 版本为 1.65.0；`test_chat_history_switch_delete_and_reload` 在 AppTest 获取 widget 状态时抛出 `ValueError: '现在几点？' is not in list`。本次没有修改前端代码，也不将该结果记为全套测试通过。

未重新运行完整模型评测或重新评分；上传不改变已有 55 题/495 条正式实验结论。

## 配置和评分使用说明

评测入口会向被测后端注入记录的模型与连接设置；原有普通应用调用仍有服务器默认路径及部分硬编码，不能据共享配置改动宣称所有应用路径都完全支持环境变量。`RAG_LLM_TIMEOUT` 对 Agent urllib/预检适用；原 SDK 生成调用尚未明确接入该超时值。

`module5_charts.py` 的通用人工评分图名只适用于真正的人工审阅输入。本轮 AI 辅助评分应使用报告目录 `scripts/make_figures.py` 的图形，其标题已明确 AI-assisted。AI 分数、执行成功、自动工具匹配和页级检索指标分别保留，不互相替代。
