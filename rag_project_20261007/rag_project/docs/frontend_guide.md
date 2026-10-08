# 成员 A：前端使用说明

项目入口为 `app.py`，需 Python 3.10 或更高版本。请在含有 `app.py`、`src/`、`data/` 的 `rag_project` 目录运行下列命令。

用户已选择直接在 C/D 的服务器运行。优先按 [服务器前端交接说明](server_frontend_handoff.md) 使用现有 `rag_env`；以下 Mac 操作保留用于本地查看和截图。

## 1. 启动界面

Mac 上当前项目位置：

```bash
cd "/Users/kerley/项目/agent生产实习/my-project-main/rag_project_20261007/rag_project"
python -m pip install -r requirements-frontend.txt
python -m streamlit run app.py
```

如果使用本项目已创建的虚拟环境，将 `python` 换为 `.venv/bin/python`。浏览器打开终端输出的地址，通常是 `http://localhost:8501`。

只安装前端即可显示界面、管理文件和历史记录，并使用实际 Agent 的当前时间工具。论文问答还需要下面的后端配置。界面没有内置虚构答案或模拟建库。

## 2. 启用论文问答

已有 C/D 的 `rag_env` 环境时，在该环境安装 `requirements-frontend.txt` 即可。新建 Mac/CPU 环境时使用：

```bash
python -m pip install -r requirements-runtime.txt
```

启动 Ollama 服务，在另一终端准备所需模型：

```bash
ollama serve
```

```bash
ollama pull qwen2.5:7b
```

若团队已有本地 Embedding 和 Reranker，启动界面前指定位置：

```bash
export RAG_EMBEDDING_MODEL="/实际模型目录/bge-large-zh"
export RAG_RERANKER_MODEL="/实际模型目录/bge-reranker-base"
python -m streamlit run app.py
```

默认先检查项目下 `models/` 和原服务器 `/root/autodl-tmp/models/`；没有本地模型时使用 BAAI 模型标识，由 Sentence Transformers 首次下载。联网、磁盘与内存条件需要满足模型要求。模型不会因为打开页面或查看健康状态而被加载。

支持的环境变量：

| 变量 | 默认值 / 用途 |
| --- | --- |
| `RAG_DATA_DIR` | 项目下 `data/`，文档目录 |
| `RAG_VECTOR_DIR` | 项目下 `vector_store/`，向量数据库目录 |
| `RAG_EMBEDDING_MODEL` | 本地 bge-large-zh 路径或 `BAAI/bge-large-zh-v1.5` |
| `RAG_RERANKER_MODEL` | 本地 bge-reranker-base 路径或 `BAAI/bge-reranker-base` |
| `RAG_MODEL_DEVICE` | `cpu`，可在支持的服务器设为 `cuda` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` |
| `RAG_LLM_MODEL` | `qwen2.5:7b` |

当前代码读取进程环境变量，不自动读取 `.env` 文件。

## 3. 文档管理

左侧“文档管理”支持批量选择 PDF，再点击“上传选中文件”。上传进度条显示已处理的文件数；各文件单独显示成功或失败。每份限制 50 MB，禁止路径穿越、同名内容覆盖和非 PDF 上传。完全相同的文件会跳过。

点击“构建 / 更新知识库”，界面展示建库状态。C 当前接口会重建整个索引，不能据此声称支持增量建库。首次需要加载模型，进度状态不伪造百分比。遇到解析失败或扫描件没有可提取文本时显示失败，并允许重试。

论文列表展示文件名、大小及状态：

| 状态 | 含义 |
| --- | --- |
| 待向量化 | 新文件尚未建库，或文档发生变更 |
| 已向量化 | 本进程成功完成建库，且文件指纹仍一致 |
| 待恢复索引 | 磁盘上有历史建库记录，但进程尚未恢复 BM25 和检索器 |
| 建库失败，可重试 | 上次构建失败，不能视为已完成 |

服务器重启后，首次论文问答会重新建立内存检索器。上传、删除或外部修改文件后，下一次论文提问会先更新知识库，避免使用过期索引。

删除论文需勾选确认。文件移到 `data/.trash/<随机目录>/`，可以手动恢复；聊天中的历史引用记录仍保留。恢复文件到文档目录后重新建库。

目前 C 仅实现 PDF 加载器，所以前端只开放 PDF。Word、TXT/Markdown 需要 C 提供解析接口后再接入。

## 4. 对话与引用

中央输入框提问，回答支持 Markdown。任务处理中显示状态，完整答案返回后以逐字效果展示，可在侧栏关闭。前端使用 [Streamlit 的 `st.write_stream`](https://docs.streamlit.io/1.40.0/develop/api-reference/write-magic/st.write_stream) 展示文本生成器。

当前 `agent_chat()` 没有增量输出接口，因此逐字效果是展示层流式，不能声称是模型 token 实时推送。Agent 轨迹同样在后端完成后展示。

示例问题：

- `现在几点？`：直接使用时间工具，不需要知识库或模型。
- `《Attention Is All You Need》的作者是谁？`：元信息工具。
- `请总结论文《An Image is Worth 16x16 Words》`：论文总结工具。
- `比较《Attention Is All You Need》和《An Image is Worth 16x16 Words》`：论文对比工具。

回答下方引用卡片展示实际返回的文件名、页码、重排序分数，并提供原文下载。分数不是“正确率”。未返回引用时明确显示无引用，不自行生成来源。

## 5. 会话与历史

侧栏“历史会话”可以新建、切换、重命名、导出和删除会话。不同会话使用独立 UUID 传给 D 的 `agent_chat()`。删除时同时清理对应 Agent 记忆。

对话、引用、执行结果持久化在 `.runtime/sessions/`。保留浏览器 URL 中的 `workspace` 参数，可在刷新或重启服务后打开同一组历史记录。丢失该 URL 会打开新工作区；这是本地课程演示的工作区标识，不是登录鉴权机制。不要把这一 URL 用作公网多人系统的安全方案。

重启后再次提问，接入层使用 D 的已有记忆接口恢复最近 12 条消息和最近已确认的论文；全部历史仍可在界面查看与导出。长期压缩摘要不做完整持久化，具体 Memory 算法仍由 D 管理。

Markdown 导出适合报告附件，JSON 导出包含引用、路由、执行轨迹及后端原始字段，便于 B 分析。

## 6. 系统状态

底部“系统状态与运行统计”显示 Ollama、所需模型、当前索引、后端依赖以及真实日志中的累计请求、成功率、耗时和平均步骤。健康检查不会主动建库。

Token 与检索耗时只有在返回值包含对应字段时才展示；缺失显示“未提供”。检索命中率需 B 的评测结果，不从回答成功率推算。

## 7. 验证与截图

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py src tests scripts
```

安装 Streamlit 后，上面的测试会额外运行 AppTest，检查真实时间工具、创建和切换历史、删除与页面重跑。缺少 Streamlit 时该项会明确跳过。

截图前启动真实界面，在另一终端执行：

```bash
python -m pip install -r requirements-checks.txt
python scripts/capture_frontend.py
```

默认使用本机已安装的 Chrome，得到首页、文档管理、实际时间工具与 Agent 记录、历史与系统状态共 4 张截图。后端模型就绪后再执行：

```bash
python scripts/capture_frontend.py --with-rag
```

额外生成实际论文问答与引用截图，共 5 张，保存到 `docs/screenshots/`。Linux 没有 Chrome 时可执行 `python -m playwright install chromium`，并给截图命令添加 `--browser-channel chromium`。

截图脚本调用实际 Agent 并保留截图工作区，失败会报错；它不会用假回答代替成功结果。
