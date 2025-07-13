from typing import List, Literal, Sequence
from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.tools import TeamTool
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    StructuredMessage,
)
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from pydantic import BaseModel
from config.model_config import model_client
import asyncio

from .insight_agent_tool import get_insight_agent_tool
from .tool_call_agent import ToolCallAgent


class WordInsightAnalysis(BaseModel):
    """insight_agent 的结构化分析模型"""

    class ExistingInformation(BaseModel):
        """已有信息确认"""

        document_type: str  # 文档类型
        target_audience: str  # 目标受众
        writing_purpose: str  # 写作目的
        style_requirement: str  # 风格要求
        key_content: List[str]  # 用户提供的关键内容要点

    class SupplementaryQuestion(BaseModel):
        """补充信息问题"""

        question: str  # 提出的具体问题
        options: List[str]  # 问题选项：供用户选择或参考，空列表表示开放式问题
        reason: str  # 需要此信息的原因
        type: Literal[
            "open", "single_choice", "multiple_choice"
        ]  # "open" | "single_choice" | "multiple_choice"，供前端识别渲染

    existing_information: ExistingInformation
    supplementary_questions: List[SupplementaryQuestion]


insight_agent_tool = get_insight_agent_tool()

insight_agent = ToolCallAgent(
    name="insight_agent",
    tool=insight_agent_tool,
)

outline_agent = AssistantAgent(
    name="outline_agent",
    model_client=model_client,
    system_message="你是一个大纲生成助手，擅长根据用户提供的关键信息和补充问题，生成详细的写作大纲。",
    model_client_stream=True,
)

genearte_agent = AssistantAgent(
    name="genearte_agent",
    model_client=model_client,
    system_message="你是一个内容生成助手，擅长根据大纲生成完整的文章内容。",
    model_client_stream=True,
)

query_agent = AssistantAgent(
    name="query_agent",
    model_client=model_client,
    system_message="你是一个查询助手，负责解答用户提出的问题，并提供相关信息。",
    model_client_stream=True,
)

modify_agent = AssistantAgent(
    name="modify_agent",
    model_client=model_client,
    system_message="你是一个修改助手，负责根据用户的反馈和要求，对生成的内容进行修改和优化。",
    model_client_stream=True,
)


def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    # 获取已经发言的智能体名称
    return messages[-1].metadata.get("select_agent", "query_agent")


team = SelectorGroupChat(
    [insight_agent, outline_agent, genearte_agent, query_agent, modify_agent],
    model_client=model_client,
    selector_func=selector_func,
    termination_condition=SourceMatchTermination(
        [
            "insight_agent",
            "outline_agent",
            "genearte_agent",
            "modify_agent",
            "query_agent",
            "json_agent",
        ]
    ),
    custom_message_types=[StructuredMessage[WordInsightAnalysis]],
)


async def main() -> None:
    while True:
        try:
            task = input("请输入您的任务（输入'quit'退出）: ")
            print("请选择一个agent: ")
            print("1. insight_agent")
            print("2. outline_agent")
            print("3. genearte_agent")
            print("4. modify_agent")
            print("5. query_agent")
            agent_options = {
                "1": "insight_agent",
                "2": "outline_agent",
                "3": "genearte_agent",
                "4": "modify_agent",
                "5": "query_agent",
            }
            agent_choice = input("输入编号选择agent（默认5）: ").strip()
            selected_agent = agent_options.get(agent_choice, "query_agent")
            metadata = {"select_agent": selected_agent}
            if task.lower() == "quit":
                break

            await Console(
                team.run_stream(
                    task=TextMessage(
                        content=task + "/no_think", source="user", metadata=metadata
                    )
                )
            )

            await team.save_state()
        except KeyboardInterrupt:
            print("\n程序已中断")
            break


asyncio.run(main())
