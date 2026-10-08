# 成员 D → 成员 A / B 接口交付说明

项目：智能科研助理 —— 基于 RAG + Agent 的论文知识库问答系统

成员 D 负责范围：
- Agent ReAct 核心循环
- Router
- Agent Tools
- 多轮 Memory
- Error Recovery
- 多论文 Source Isolation
- Paper Compare
- 系统集成
- Observability
- Health Check

成员 D **不负责前端页面实现，也不负责最终评测报告撰写**。

---

## 1. D 对外统一入口

成员 A 和成员 B 不需要直接调用 Router、ReAct、Memory 或具体 Tool。

统一使用：

```python
from src.agent import agent_chat
```

调用：

```python
result = agent_chat(
    question="比较《Attention Is All You Need》和《An Image is Worth 16x16 Words》",
    session_id="demo_session",
    use_memory=True,
    verbose=False,
)
```

---

## 2. agent_chat 返回结构

核心字段：

```python
{
    "answer": "...",
    "sources": [...],
    "tools_used": [...],
    "steps": 1,
    "success": True,

    "route": "paper_compare",
    "route_confidence": "high",
    "route_reason": "...",

    "execution_mode": "direct_tool",

    "trace": [...],

    "timing": {
        "total_time": 12.34
    },

    "session_id": "demo_session",

    "memory_stats": {...}
}
```

### 前端成员 A 建议使用字段

```text
answer
sources
success
route
execution_mode
tools_used
timing.total_time
```

`trace` 可作为高级调试信息或折叠展示，不建议默认全部展开。

---

## 3. Session Memory

同一会话必须保持相同 `session_id`：

```python
agent_chat(
    question="请介绍论文 Attention Is All You Need",
    session_id="user_001",
)

agent_chat(
    question="它的核心关键词是什么？",
    session_id="user_001",
)
```

不同 `session_id` 的 Memory 相互隔离。

如不需要 Memory：

```python
agent_chat(
    question="...",
    session_id="eval_001",
    use_memory=False,
)
```

成员 B 做独立 QA 评测时，建议默认：

```python
use_memory=False
```

多轮上下文评测时再使用：

```python
use_memory=True
```

---

## 4. 当前 Agent Tools

当前工具包括：

```text
knowledge_base_search
knowledge_base_retrieve
paper_summary
paper_metadata
keyword_extract
paper_compare
current_time
```

其中：

- `knowledge_base_search`：论文知识库事实问答
- `knowledge_base_retrieve`：原始证据检索
- `paper_summary`：结构化论文总结
- `paper_metadata`：标题 / 作者 / 年份 / Abstract / DOI / Venue
- `keyword_extract`：核心概念 / 方法 / 任务 / 数据集关键词
- `paper_compare`：两篇论文方法 / 数据集 / 结果对比
- `current_time`：通用时间工具

---

## 5. 多论文知识库

当前已验证 3 篇论文：

```text
An_Image_is_Worth_16x16_Words.pdf
Deep_Residual_Learning_for_Image_Recognition.pdf
attention_is_all_you_need.pdf
```

多论文高级 Tool 使用 Paper Scope：

```text
Paper Name
   ↓
Resolve PDF Source
   ↓
Retrieve only from target source
```

已验证：

```text
3 / 3 Paper Source Isolation PASS
```

新增 PDF：

1. 将 PDF 放入：

```text
/root/autodl-tmp/rag_project/data/
```

2. 重新构建知识库：

```python
from src.agent.tools import refresh_knowledge_base

refresh_knowledge_base()
```

无需修改成员 C 的 `src/generation/__init__.py`。

---

## 6. Observability 接口

导入：

```python
from src.agent.observability import (
    get_agent_metrics,
    get_recent_requests,
    get_log_path,
)
```

### 获取整体指标

```python
metrics = get_agent_metrics()
print(metrics)
```

返回示例：

```python
{
    "total_requests": 100,
    "success_count": 94,
    "failure_count": 6,
    "success_rate": 0.94,
    "avg_steps": 1.37,
    "avg_latency": 8.52,
    "router_direct_rate": 0.63,
    "react_rate": 0.37,
    "retry_count": 3,
    "fallback_count": 1,
    "fallback_success_count": 1,
    "duplicate_block_count": 0,
    "tool_error_count": 2,
    "tool_usage": {...},
    "route_usage": {...},
    "execution_mode_usage": {...}
}
```

### 获取最近请求

```python
records = get_recent_requests(
    limit=20
)
```

### 日志位置

```python
print(
    get_log_path()
)
```

默认：

```text
logs/agent_requests.jsonl
```

每一行对应一次 Agent 请求。

---

## 7. Health Check 接口

导入：

```python
from src.agent.health import (
    get_system_health,
)
```

调用：

```python
health = get_system_health()
print(health)
```

返回内容包括：

```text
Agent Tool Registry
Ollama 状态
RAG 初始化状态
PDF 数量
PDF 文件名
vector_store 状态
Observability Log 状态
```

Health Check 不会主动执行 `build_index()`，因此不会因为查看状态而重新加载模型或重建索引。

---

## 8. 成员 A 接入建议

A 只需使用两个入口：

### 问答

```python
from src.agent import agent_chat
```

### 系统状态

```python
from src.agent.health import (
    get_system_health,
)
```

如需展示运行统计：

```python
from src.agent.observability import (
    get_agent_metrics,
)
```

A 不需要：

```text
直接调用 retrieve()
直接操作 Chroma
直接调用 Router
直接调用 ReAct
直接操作 Memory
直接调用具体 Tool
```

这些都由 D 的统一层负责。

---

## 9. 成员 B 评测建议

B 可直接使用：

```python
result = agent_chat(
    question=question,
    session_id=f"eval_{case_id}",
    use_memory=False,
)
```

建议记录：

```text
success
route
execution_mode
tools_used
steps
timing.total_time
sources
answer
```

Agent 指标可从：

```python
get_agent_metrics()
```

直接读取。

B 仍需人工或自动统计：

```text
Tool Selection Accuracy
Answer Correctness
Citation Correctness
Human Score
Bad Case Category
```

D 提供的日志负责：

```text
Agent Success Rate
Average Steps
Average Latency
Tool Usage
Route Distribution
Retry Count
Fallback Count
Duplicate Guard Count
Tool Error Count
```

---

## 10. 已知 Bad Cases

当前建议保留以下 Bad Cases：

1. Query Drift  
   冗余论文标题曾降低单论文检索质量。

2. Secondary-generation Hallucination  
   RAG 已回答正确，Agent 二次生成后改错。

3. Adjacent Concept Confusion  
   Multi-Head Attention 与 Scaled Dot-Product Attention 原因混淆。

4. Cross-task Contamination  
   不同实验任务的数据集 / 参数 / 结果混合。

5. Cross-paper Contamination  
   多论文知识库中可能召回其他论文内容；已通过 Paper Scope 修复。

6. Metadata Recall Insufficient  
   部分论文 Year / Venue 仍可能因证据召回不足为空。

7. Task Discovery Recall Insufficient  
   Summary 可能遗漏论文中的次要实验任务。

8. Comparison Evidence Ranking  
   Compare 可正确隔离两篇论文，但可能未总是选到最代表性的实验结果。

这些属于后续 B 评测和 Bad Case 分析材料，不代表系统主链路失败。

---

## 11. D 当前交付状态

```text
ReAct Core Loop                DONE
Fast Router                    DONE
Tool Registry                  DONE
RAG Tool Integration           DONE
Terminal Tool Early Stop       DONE
Evidence Guard                 DONE
Session Isolation              DONE
Sliding Window Memory          DONE
Summary Memory                 DONE
LLM Retry                      DONE
Tool Retry                     DONE
Fallback Tool                  DONE
Duplicate Call Guard           DONE
MAX_STEPS Termination          DONE
Paper Source Resolution        DONE
Multi-paper Source Isolation   DONE
Paper Compare                  DONE
Unified agent_chat             DONE
Observability                  DONE
Health Check                   DONE
```

成员 D 的主要编码任务至此完成。
