# 成员 A → C/D：服务器前端接入

最终界面由有服务器访问权限的成员在 C/D 已配置好模型的环境运行。成员 A 本次只交付代码和报告，部署、运行验证与截图交给其他成员。原文档路径为 `/root/autodl-tmp/rag_project`，部署人员应按自己的服务器信息核对目录与环境。

## 1. 交付包范围

工作区根目录的 `member-A-server.tar.gz` 包含 A 新增界面、接入层、配置、前端依赖、验证脚本、工作报告和交接文档，不包含 C/D 原来的 `src/agent/*.py`、`src/generation/*.py`、`src/retrieval/*.py`，也不包含任何 PDF、模型、运行日志或会话文件。

本机为兼容 Mac 修改的后端文件不会通过这个包覆盖服务器。原服务器已经使用同一 `/root/autodl-tmp/rag_project/data`，且依赖已经安装时，可沿用原 C/D 后端。

服务器如果将项目移到其他目录，原 C/D 后端的硬编码路径也需单独核对；不能只移动界面而忽略后端实际数据路径。

## 2. 上传与安装

把以下两个文件上传到服务器的临时交付目录：

- `member-A-server.tar.gz`
- `scripts/install_frontend.py`

不要直接把整个本机旧项目覆盖到服务器。

在服务器执行预检查（示例路径须按实际位置调整）：

```bash
python install_frontend.py --archive member-A-server.tar.gz --target /root/autodl-tmp/rag_project
```

安装器验证目标含有 C/D 入口，拒绝未知包路径、外部符号链接、缺失包文件以及已存在但内容不同的目标文件。它不会修改原后端文件。

确认预检查输出后执行：

```bash
python install_frontend.py --archive member-A-server.tar.gz --target /root/autodl-tmp/rag_project --apply
```

所有变更都是新增文件；同内容文件跳过。有文件冲突时先核对，不能用强制覆盖跳过检查。

## 3. 使用已有环境启动

```bash
conda activate rag_env
cd /root/autodl-tmp/rag_project
python -m pip install -r requirements-frontend.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

使用原环境，无需重复安装原 `requirements.txt`、重新下载 BGE 模型或替换 C/D 的环境。只有模型检查失败时再按 C/D 已有部署说明处理 Ollama。

本地浏览器通过 SSH 转发访问：

```bash
ssh -p <SSH端口> -L 8501:127.0.0.1:8501 <用户名>@<服务器地址>
```

保持该终端连接，浏览器打开 `http://localhost:8501`。启动地址绑定服务器本机回环，页面无需公开暴露到公网。

如果 AutoDL 提供已有的端口转发方式，也可以沿用团队配置。最终启动方式由 D 的部署规范决定。

## 4. 真实验收

安装后先运行 AppTest。随后检查批量上传、建库状态、Markdown、引用下载、历史切换/删除、实际工具轨迹与健康检查。

必须完成一轮 `上传论文 → 构建索引 → agent_chat → 答案和来源`，再运行双论文比较和同会话指代问答。当前本机验证不等于服务器链路通过。

截图可在可访问页面的 Mac 上运行 `scripts/capture_frontend.py --with-rag`。需要先安装 `requirements-checks.txt` 并保持 SSH 转发；脚本默认使用本机 Chrome，图片会保存到执行目录下的 `docs/screenshots/`。

完成后更新 `docs/member_A_validation.md`，附上实际运行结果及 3–5 张 PNG，再交给 B 汇总报告。

## 5. 注意测试与正式指标的区别

单元测试中的索引替身仅验证界面接入协议，不能计作检索评测。时间工具是真实运行，但不需要 RAG。服务器上的论文测试和性能数字必须来自实际模型执行。

当前 A 界面提供逐字展示和完成后的 trace；如果课程要求模型生成阶段实时传输 token 和工具事件，需要 D 扩展统一接口，再由 A 接入。Token、检索命中率和工具耗时字段的缺口见成员 A 技术交接文档。
