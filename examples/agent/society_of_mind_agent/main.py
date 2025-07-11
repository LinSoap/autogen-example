from typing import Sequence
from autogen_agentchat.agents import AssistantAgent, SocietyOfMindAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from config.model_config import model_client
import asyncio

insight_agent = AssistantAgent(
    name="insight_agent",
    model_client=model_client,
    system_message="你是一个需求收集助手，擅长从用户的输入中提取关键信息并总结，并向用户提出补充问题以获取更多信息。",
    model_client_stream=True,
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
    if len(messages) == 1:
        return "insight_agent"
    if len(messages) == 3:
        return "outline_agent"
    if len(messages) == 5:
        return "genearte_agent"
    return "society_of_ming_agent"


inner_termination = SourceMatchTermination(["query_agent", "modify_agent"])
inner_team = SelectorGroupChat(
    [insight_agent, outline_agent, genearte_agent],
    model_client=model_client,
    selector_func=selector_func,
    termination_condition=inner_termination,
)

society_of_ming_agent = SocietyOfMindAgent(
    name="society_of_ming_agent",
    model_client=model_client,
    team=inner_team,
    description="这是一报告助手，用于修改报告的内容或者对用户对报告提出的疑问进行解答",
)


team = RoundRobinGroupChat(
    [insight_agent, outline_agent, genearte_agent, society_of_ming_agent],
    termination_condition=SourceMatchTermination(
        [
            "insight_agent",
            "outline_agent",
            "genearte_agent",
            "society_of_ming_agent",
        ]
    ),
)


async def assistant_run() -> None:
    await Console(
        team.run_stream(
            task="帮我生成一篇300字的麦当劳实习生周报",
            cancellation_token=CancellationToken(),
        ),
        output_stats=True,
    )


asyncio.run(assistant_run())
