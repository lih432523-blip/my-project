"""Member A's Streamlit entry point: run `streamlit run app.py`."""
import json
import uuid
from pathlib import Path

import streamlit as st

from src.config import RUNTIME_DIR, OLLAMA_MODEL
from src.frontend.service import BackendService, FrontendError, number, typewriter
from src.frontend.state import SessionStore, markdown_export

st.set_page_config(page_title="知研 · 智能科研助理", page_icon="📚", layout="wide")
st.markdown("""<style>
    .block-container {padding-top: 2.2rem; max-width: 1180px;}
    [data-testid="stSidebar"] {border-right: 1px solid #dce6e2;}
    [data-testid="stChatMessage"] {border: 1px solid #e2eae7; border-radius: 14px;}
    [data-testid="stMetricValue"] {font-size: 1.45rem;}
    h1 {letter-spacing: -.045em;} h3 {letter-spacing: -.02em;}
    .eyebrow {color:#18776f; font-size:.78rem; letter-spacing:.12em; font-weight:600;}
    .intro {color:#62736e; margin-bottom:1.6rem;}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def get_backend():
    return BackendService()


@st.cache_resource
def get_store(owner):
    return SessionStore(RUNTIME_DIR / "sessions", owner)


@st.cache_data(ttl=5)
def get_health(_backend):
    return _backend.health()


def show_notice():
    notice = st.session_state.pop("notice", None)
    if notice:
        st.success(notice)


def format_seconds(value):
    value = number(value)
    return f"{value:.2f} s" if value is not None else "未提供"


def render_trace(result, expanded=False):
    with st.expander("Agent 执行过程", expanded=expanded):
        st.caption(f"路由：{result.get('route') or '未提供'} · 执行方式：{result.get('execution_mode') or '未提供'}")
        if result.get("route_reason"):
            st.write("路由依据：", result["route_reason"])
        trace = result.get("trace", [])
        if not trace:
            st.caption("本次请求没有返回工具轨迹。")
        for item in trace:
            with st.container(border=True):
                action = item.get("action") or item.get("tool") or item.get("fallback_tool") or item.get("type") or "执行记录"
                st.markdown(f"**步骤 {item.get('step', '?')} · {action}**")
                if item.get("thought"):
                    st.write("Thought · 执行计划：", item["thought"])
                if item.get("action"):
                    st.write("Action · 工具：", item["action"])
                tool_input = item.get("effective_input") or item.get("action_input") or item.get("tool_input")
                if tool_input:
                    st.write("工具输入：", tool_input)
                observation = item.get("observation") or item.get("answer")
                if not observation and item.get("mode") == "router_direct" and result.get("tool_result") is not None:
                    observation = json.dumps(result["tool_result"], ensure_ascii=False, indent=2, default=str)
                if observation:
                    st.caption("Observation · 工具输出")
                    st.text(str(observation))
                if item.get("error"):
                    st.error(str(item["error"]))
                if "success" in item:
                    st.caption("执行成功" if item["success"] else "执行失败 / 已触发恢复")
                elapsed = item.get("elapsed") or item.get("total_time") or item.get("duration")
                if elapsed is not None:
                    st.caption("工具耗时：" + format_seconds(elapsed))
        st.caption("轨迹来自后端记录；当前接口在任务完成后返回。")


def render_sources(result, backend, key_prefix):
    sources = result.get("sources", [])
    if not sources:
        st.caption("本次回答未返回文献引用。")
        return
    with st.expander(f"引用来源 · {len(sources)} 条", expanded=True):
        for index, source in enumerate(sources):
            name = str(source.get("source", "未知文档"))
            page = source.get("page", "?")
            with st.container(border=True):
                st.write(f"📄 {name} · 第 {page} 页")
                score = number(source.get("rerank_score"))
                if score is not None:
                    st.caption(f"重排序分数：{score:.3f}")
                if source.get("text"):
                    st.text(str(source["text"]))
                try:
                    data = backend.read_document(name)
                except FrontendError:
                    st.caption("原文件已不在当前知识库中，历史引用信息仍保留。")
                else:
                    st.download_button("下载原文 PDF", data=data, file_name=name, mime="application/pdf",
                                       key=f"source_{key_prefix}_{index}")
        st.caption("展示后端返回的检索来源；引用是否支持具体结论需结合原文核验。")


def render_result(result, backend, key_prefix, stream=False):
    if not result.get("success"):
        st.warning("本次任务未成功完成，可查看执行记录后重试。")
    if stream:
        st.write_stream(typewriter(result["answer"], st.session_state.get("typewriter", True)))
    else:
        st.markdown(result["answer"])
    tools = "、".join(str(tool) for tool in result.get("tools_used", [])) or "未调用工具"
    st.caption(f"{tools} · {result.get('steps', 0)} 步 · 耗时 {format_seconds(result.get('timing', {}).get('total_time'))}")
    render_sources(result, backend, key_prefix)
    render_trace(result)
    if result.get("logging_error"):
        st.warning("回答已返回，但后端运行日志写入失败。")


def documents_panel(backend):
    st.caption("支持批量 PDF，每份不超过 50 MB。")
    uploaded = st.file_uploader("添加论文", type=["pdf"], accept_multiple_files=True,
                                key=f"upload_{st.session_state.get('upload_version', 0)}")
    if st.button("上传选中文件", disabled=not uploaded, use_container_width=True):
        progress = st.progress(0, text="准备上传…")
        for index, item in enumerate(uploaded):
            try:
                result = backend.upload(item.name, item.getvalue())
                st.success(result["name"] + "：" + result["status"])
            except FrontendError as exc:
                st.error(f"{item.name}：{exc}")
            progress.progress((index + 1) / len(uploaded), text=f"已处理 {index + 1}/{len(uploaded)}")
        st.session_state["upload_version"] = st.session_state.get("upload_version", 0) + 1
        get_health.clear()
    documents = backend.documents()
    if st.button("构建 / 更新知识库", use_container_width=True, disabled=not documents):
        with st.status("正在解析论文、分块并向量化…", expanded=True) as status:
            st.write("首次运行需要加载检索模型，请耐心等待。")
            try:
                count = backend.build_index()
            except FrontendError as exc:
                status.update(label="建库失败，可再次点击重试", state="error")
                st.error(str(exc))
            else:
                status.update(label=f"建库完成 · {count} 个文本块", state="complete")
                st.success("知识库已更新。")
            get_health.clear()
        documents = backend.documents()
    st.markdown(f"**论文列表 · {len(documents)}**")
    if not documents:
        st.info("还没有论文，请先上传。")
    for doc in documents:
        with st.expander(doc["name"]):
            st.caption(f"{doc['size'] / 1024:.1f} KB · {doc['status']}")
            st.download_button("下载 PDF", backend.read_document(doc["name"]), file_name=doc["name"],
                               mime="application/pdf", key="download_" + doc["name"])
            confirm = st.checkbox("确认从知识库移除", key="confirm_" + doc["name"])
            if st.button("删除论文", disabled=not confirm, key="delete_" + doc["name"]):
                target = backend.delete_document(doc["name"])
                st.session_state["notice"] = f"已移除 {doc['name']}；可从 data/.trash 恢复。"
                get_health.clear()
                st.rerun()
    st.caption("Word / TXT 解析需由 C 补齐后接入；当前只开放后端已支持的 PDF。")


def history_panel(store, state, backend):
    if st.button("＋ 新建会话", use_container_width=True):
        store.create(state)
        st.rerun()
    sessions = state["sessions"]
    ids = sorted(sessions, key=lambda sid: sessions[sid]["updated_at"], reverse=True)
    selected = st.selectbox("历史会话", ids, index=ids.index(state["active_id"]),
                            format_func=lambda sid: sessions[sid]["title"],
                            key="picker_" + "_".join(sorted(ids)))
    if selected != state["active_id"]:
        state["active_id"] = selected
        store.save(state)
        st.rerun()
    session = sessions[state["active_id"]]
    st.caption(f"创建于 {session['created_at'][:16].replace('T', ' ')}")
    st.caption(f"已保存 {len(session['messages'])} 条消息")
    title = st.text_input("会话名称", value=session["title"], key="title_" + session["id"])
    if st.button("保存名称", disabled=not title.strip()):
        session["title"] = title.strip()[:80]
        store.save(state)
        st.rerun()
    memory = st.toggle("记住本次会话上下文", value=session.get("use_memory", True), key="memory_" + session["id"])
    if memory != session.get("use_memory", True):
        session["use_memory"] = memory
        # Toggling off/on starts from the persisted history, rather than stale backend memory.
        backend.clear_session(session["id"])
        store.save(state)
    st.download_button("导出会话 Markdown", markdown_export(session), file_name="conversation.md",
                       mime="text/markdown", use_container_width=True)
    st.download_button("导出完整记录 JSON", json.dumps(session, ensure_ascii=False, indent=2, default=str),
                       file_name="conversation.json", mime="application/json", use_container_width=True)
    with st.expander("删除当前会话"):
        confirmed = st.checkbox("确认删除历史记录", key="confirm_session_" + session["id"])
        if st.button("删除会话", disabled=not confirmed):
            backend.clear_session(session["id"])
            store.delete(state, session["id"])
            st.session_state["notice"] = "会话记录和对应的 Agent 记忆已删除。"
            st.rerun()


def monitor_panel(backend, last_result):
    with st.expander("系统状态与运行统计", expanded=False):
        if st.button("刷新系统状态"):
            get_health.clear()
        health = get_health(backend)
        columns = st.columns(3)
        columns[0].metric("Ollama 服务", "在线" if health["ollama"]["status"] == "ok" else "未连接")
        columns[1].metric("问答模型", "已就绪" if health["model_available"] else "未就绪")
        columns[2].metric("知识库索引", "已就绪" if health["rag"]["initialized"] else "待构建 / 恢复")
        missing = [name for name, installed in health["dependencies"].items() if not installed]
        if missing:
            st.warning("缺少后端依赖：" + "、".join(missing) + "。请按前端使用说明安装运行依赖。")
        if not health["model_available"]:
            st.caption(f"当前配置的问答模型：{OLLAMA_MODEL}。服务启动并载入该模型后可进行论文问答。")
        if health.get("index_error"):
            st.error(health["index_error"])
        metrics = backend.metrics()
        columns = st.columns(4)
        count = metrics.get("total_requests", 0)
        columns[0].metric("累计请求", count)
        columns[1].metric("请求成功率", f"{metrics.get('success_rate', 0) * 100:.1f}%" if count else "暂无数据")
        columns[2].metric("平均耗时", format_seconds(metrics.get("avg_latency")) if count else "暂无数据")
        columns[3].metric("平均步骤", f"{metrics.get('avg_steps', 0):.1f}" if count else "暂无数据")
        if last_result:
            tool = last_result.get("tool_result")
            tool = tool if isinstance(tool, dict) else {}
            columns = st.columns(3)
            usage = last_result.get("token_usage") or {}
            columns[0].metric("本次 Token", usage.get("total_tokens", "未提供"))
            columns[1].metric("检索耗时", format_seconds(tool.get("retrieve_time")))
            columns[2].metric("检索命中率", "待评测")
        st.caption("统计来自真实请求日志。Token、工具耗时和检索命中率需后端或评测模块提供。")
        st.caption("详细健康检查")
        st.json(health, expanded=False)


def main():
    backend = get_backend()
    # Save the URL to reopen this browser workspace after a server/browser restart.
    # This is a local classroom app, not an authentication mechanism.
    owner = st.query_params.get("workspace", "")
    try:
        owner = uuid.UUID(owner).hex
    except (ValueError, AttributeError):
        owner = uuid.uuid4().hex
        st.query_params["workspace"] = owner
    store = get_store(owner)
    try:
        state = store.load()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    with st.sidebar:
        st.markdown("### 📚 知研")
        st.caption("让每个答案，都有文献可循。")
        documents_tab, history_tab = st.tabs(["文档管理", "历史会话"])
        with documents_tab:
            documents_panel(backend)
        with history_tab:
            history_panel(store, state, backend)
        st.divider()
        st.toggle("逐字展示回答", value=True, key="typewriter")
        st.caption("南京农业大学 · 生产实习\n\n智能科研助理 / RAG + Agent")
    session = state["sessions"][state["active_id"]]
    st.markdown('<div class="eyebrow">RESEARCH WORKSPACE / 论文知识库</div>', unsafe_allow_html=True)
    st.title("把论文，变成可以对话的知识。")
    st.markdown('<p class="intro">阅读、提问、比较。基于你的文献寻找答案，查看引用与执行过程。</p>', unsafe_allow_html=True)
    show_notice()
    documents = backend.documents()
    columns = st.columns(3)
    columns[0].metric("知识库论文", len(documents))
    columns[1].metric("已向量化", sum(doc["status"] == "已向量化" for doc in documents))
    columns[2].metric("当前会话", session["title"])
    st.divider()
    if not session["messages"]:
        st.subheader("从一个好问题开始")
        st.write("在左侧上传论文并构建知识库，或先询问当前时间验证 Agent 连接。")
        examples = ["现在几点？"]
        if documents:
            title = Path(documents[0]["name"]).stem.replace("_", " ")
            examples += [f"请总结论文《{title}》", f"《{title}》的作者是谁？"]
        else:
            st.info("知识库为空。论文相关问题需要先上传文档。")
        for column, example in zip(st.columns(len(examples)), examples):
            if column.button(example, use_container_width=True):
                st.session_state["pending_question"] = example
                st.rerun()
    last_result = None
    for index, message in enumerate(session["messages"]):
        with st.chat_message(message["role"], avatar="📚" if message["role"] == "assistant" else "👤"):
            if message["role"] == "assistant" and "result" in message:
                last_result = message["result"]
                render_result(last_result, backend, f"{session['id']}_{index}")
            else:
                st.markdown(message["content"])
    question = st.chat_input("询问论文的方法、数据集、实验结果，或比较两篇论文…", max_chars=12000)
    question = st.session_state.pop("pending_question", None) or question
    if question and question.strip():
        question = question.strip()
        history = list(session["messages"])
        store.append(state, "user", question)
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="📚"):
            with st.status("Agent 正在处理问题…", expanded=True) as status:
                st.write("正在准备知识库与会话上下文；完成后展示答案和工具记录。")
                try:
                    result = backend.chat(question, session["id"], session.get("use_memory", True), history)
                except FrontendError as exc:
                    result = {"answer": str(exc), "success": False, "sources": [], "trace": [],
                              "tools_used": [], "steps": 0, "timing": {}}
                status.update(label="处理完成" if result["success"] else "处理失败，可重试",
                              state="complete" if result["success"] else "error", expanded=False)
            store.append(state, "assistant", result["answer"], result)
            render_result(result, backend, f"{session['id']}_{len(session['messages']) - 1}", stream=True)
            last_result = result
        get_health.clear()
    monitor_panel(backend, last_result)
    st.caption("当前界面保存于本机；保留浏览器地址可重新打开会话。")


if __name__ == "__main__":
    main()
