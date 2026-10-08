# 成员 A：当前验证记录

日期：2026-10-08。环境：Mac 本地项目副本，验证解释器为项目 `.venv` 中的 Python 3.13.13；代码兼容目标为 Python 3.10+。

## 1. 已实际执行

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py src tests scripts
```

结果：15 项测试通过，1 项 Streamlit UI 测试因未安装 Streamlit 明确跳过；语法检查通过。

| 已验证范围 | 证据 |
| --- | --- |
| 会话保存、重新加载、切换与删除后的状态 | `test_round_trip_switch_delete_and_export` |
| 工作区隔离、文件损坏时不覆盖原记录 | `test_owners_are_isolated_and_corrupt_file_is_preserved` |
| 工作区标识不能作为路径穿越入口 | `test_owner_path_cannot_escape` |
| PDF 上传、后缀统一、重复跳过、同名不覆盖、删除可恢复 | `test_upload_duplicates_and_recoverable_delete` |
| 错误格式、空文件、路径穿越、符号链接保护 | `test_invalid_files_and_path_traversal` |
| 上传大小限制 | `test_upload_size_limit` |
| 实际调用 D 的当前时间工具，空知识库下不加载模型 | `test_real_agent_time_route_does_not_load_models` |
| 空库论文提问、空问题、超长问题的提示 | `test_empty_corpus_and_long_question` |
| 建库失败/成功/重启恢复状态区分 | `test_index_failure_and_success_are_distinct`（解析器与建库结果使用测试替身，仅验证接入协议） |
| 扫描件无文本不能标成成功 | `test_scanned_pdf_is_not_marked_indexed`（解析器替身） |
| 最近消息及论文指代恢复、删除某会话不清理其他会话 | `test_memory_rehydrates_and_clear_does_not_affect_other_session` |
| 引用去重、空分数、缺失耗时和文本展示保持原文 | `test_sources_unknown_metrics_and_stream_text_preserved` |
| 服务器安装预检查不写文件、重复安装跳过、后端文件保持原样 | `test_dry_run_and_idempotent_install_keep_backend` |
| 服务器已有不同前端文件时拒绝全部安装 | `test_conflict_rejects_all_writes` |
| 交付包不能写出目录或替换 C/D 后端入口 | `test_archive_cannot_escape_or_replace_backend` |

额外实际检查：

- `agent_chat("现在几点？", use_memory=False)` 返回 `success=True`，路由 `current_time`，工具 `current_time`，真实系统时间与统一返回结构正常。
- 健康检查可导入，不触发模型加载；能识别项目中的 3 篇 PDF 和实际 7 个工具。
- `.venv` 中目前缺少 `streamlit`、`pdfplumber`、`chromadb`、`sentence_transformers`、`rank_bm25`、`jieba`、`ollama`。
- Ollama 检查在当前沙箱返回连接不允许。这只能证明当前执行环境无法连接，不能证明用户电脑或团队服务器上的服务一定未启动。
- pip 连接 `pypi.org` 失败，日志显示 DNS 无法解析，未能安装 Streamlit；不是通过了界面测试。
- 当前目录不是 Git 工作树，本次文件修改位于下载副本，没有 Git 提交或远程推送。

## 2. 完成审核：实现与验证分开

| 成员 A 的要求 | 实现状态 | 实际验证状态 |
| --- | --- | --- |
| Streamlit 页面与布局 | 已写入 `app.py` | 语法通过，实际页面未运行 |
| 文件/批量上传、进度、列表、删除 | 已实现 | 文件接入逻辑通过，浏览器交互未验证 |
| 建库状态和失败重试 | 已实现 | 协议测试通过，真实模型建库未验证 |
| 聊天、Markdown、逐字展示 | 已实现 | 时间工具真实运行通过，浏览器显示未验证 |
| 来源文件名/页码、原文下载 | 已实现 | 引用数据处理通过，真实论文答案和下载按钮未验证 |
| 新建/切换/删除历史、保存与导出 | 已实现 | 状态测试通过，AppTest 尚未执行 |
| Agent 执行状态和工具记录 | 已实现 | 已接实际时间工具结果，真实页面未检查 |
| 健康状态与已有指标 | 已实现 | 接口可运行，模型服务连接在沙箱内受限 |
| 模块四说明与界面操作文档 | 已交付 | 见 `member_A_implementation.md`、`frontend_guide.md` |
| 上传 → 建库 → 问答 → 引用完整联调 | 接入代码已实现 | 待具备后端模型的运行环境验证 |
| 3–5 张系统截图 | 自动截图脚本已交付 | PNG 尚未生成，不能算截图交付完成 |

按最终确认的范围，成员 A 本次交付前端代码、使用说明及工作报告；服务器运行验证和截图由其他成员完成。上表中的未验证项是交接清单，不再要求成员 A 获取服务器连接信息后才能交付。

已准备只包含 A 新增文件的服务器交付包及安全安装器。本次没有上传或运行服务器上的代码；安装测试在隔离临时目录进行，不表示服务器已经部署。完成内容和项目缺口见 `member_A_work_report.md`。

## 3. 交给运行验证人员的检查顺序

1. 安装 `requirements-frontend.txt`，运行 `python -m unittest discover -s tests -v`。检查原先跳过的 AppTest 是否实际通过。
2. `python -m streamlit run app.py`。检查首页、批量上传、进度提示、会话切换和错误状态。
3. 在 C/D 已有环境或配置好的 Mac 环境中构建知识库；确认文件状态真实变为“已向量化”。
4. 查询 `《Attention Is All You Need》的作者是谁？`，核对实际答案、页码与原文下载；随后执行双论文对比与后续指代提问。
5. 上传一份新的有效 PDF 后重建；删除该测试论文后确认下一次检索不引用已移除文件。删除只针对临时测试文档，原有论文保持可恢复。
6. 执行 `python scripts/capture_frontend.py --with-rag`，得到 5 张实际运行截图，人工检查排版、引用和状态。

所有结果应以新执行的输出更新本记录。没有执行的测试不能根据代码存在而填为通过。
