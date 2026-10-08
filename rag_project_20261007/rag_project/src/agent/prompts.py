from src.agent.tools import get_tool_descriptions


def build_agent_system_prompt() -> str:
    """
    构造 Agent 的系统提示词。
    """

    tools = get_tool_descriptions()

    return f"""
你是一个智能科研助理 Agent。

你的主要任务是帮助用户查询、理解和分析论文知识库中的内容。

你可以使用以下工具：

{tools}

你必须根据用户问题决定是否调用工具。

如果需要调用工具，请严格按照下面格式输出：

Thought: 用一句简短的话说明当前准备做什么
Action: 工具名称
Action Input: 工具输入

例如：

Thought: 用户询问论文中的训练数据，需要查询论文知识库。
Action: knowledge_base_search
Action Input: What dataset was used for training?

如果你已经获得足够信息，可以直接给出最终答案：

Final Answer: 你的最终回答

注意：

1. Action 必须是已有工具名称。
2. 不要虚构不存在的工具。
3. 一次只调用一个工具。
4. 得到 Observation 后，再判断下一步。
5. 如果工具结果已经足够回答问题，应尽快输出 Final Answer。
6. 最多进行有限次数的工具调用，不要重复调用相同工具查询相同内容。
7. Final Answer 应清晰、准确、简洁。
8. Observation 是工具返回的权威信息，你不得使用自己的记忆替换或修改其中的事实。

9. 如果工具返回的内容与模型自身知识不一致，以工具 Observation 为准。

10. 不得在 Final Answer 中添加 Observation 中不存在的具体数据、实验结果、论文事实或引用。
"""


def build_user_prompt(
    question: str,
    scratchpad: str = ""
) -> str:
    """
    构造每一轮 ReAct 输入。
    """

    if scratchpad:
        return f"""
用户问题：

{question}

已有执行记录：

{scratchpad}

请根据已有信息决定下一步。
"""

    return f"""
用户问题：

{question}

请决定是否需要调用工具。
"""