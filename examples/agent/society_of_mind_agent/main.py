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


inner_termination = SourceMatchTermination(["query_agent", "modify_agent"])
inner_team = SelectorGroupChat(
    [query_agent, modify_agent],
    model_client=model_client,
    termination_condition=inner_termination,
    selector_prompt="""
        选择一个智能体来执行任务。
        {roles}
        当前对话上下文：
        {history}
        当用户的询问性质的意图，则使用 query_agent 来回答。
        当用户的请求是修改内容意图，则使用 modify_agent 来修改内容。
        阅读上述对话，然后从 {participants} 中选择一个智能体来执行下一个任务。
        确保规划智能体在其他智能体开始工作之前已分配任务。
        只选择一个智能体。
    """,
)

society_of_ming_agent = SocietyOfMindAgent(
    name="society_of_ming_agent",
    model_client=model_client,
    team=inner_team,
    description="这是一报告助手，用于修改报告的内容或者对用户对报告提出的疑问进行解答",
)


def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    # 获取已经发言的智能体名称
    agent_names = set()
    for msg in messages:
        if hasattr(msg, "source") and msg.source:
            agent_names.add(msg.source)

    print(f"已发言的智能体: {agent_names}")

    # 如果没有任何智能体发言，从insight_agent开始
    if "insight_agent" not in agent_names:
        return "insight_agent"

    # 如果包含insight_agent，则使用outline_agent
    if "insight_agent" in agent_names and "outline_agent" not in agent_names:
        return "outline_agent"

    # 如果包含insight_agent和outline_agent，则使用genearte_agent
    if (
        "insight_agent" in agent_names
        and "outline_agent" in agent_names
        and "genearte_agent" not in agent_names
    ):
        return "genearte_agent"

    # 如果3个特定agent都有了，则选择society_of_ming_agent
    if all(
        agent in agent_names
        for agent in ["insight_agent", "outline_agent", "genearte_agent"]
    ):
        return "society_of_ming_agent"

    # 默认返回None
    return None


team = SelectorGroupChat(
    [insight_agent, outline_agent, genearte_agent, society_of_ming_agent],
    model_client=model_client,
    selector_func=selector_func,
    termination_condition=SourceMatchTermination(
        [
            "insight_agent",
            "outline_agent",
            "genearte_agent",
            "society_of_ming_agent",
        ]
    ),
)


async def main() -> None:
    while True:
        try:
            task = input("请输入您的任务（输入'quit'退出）: ")
            if task.lower() == "quit":
                break

            await Console(
                team.run_stream(
                    task=task + "/no_think",
                    cancellation_token=CancellationToken(),
                ),
                output_stats=True,
            )
            await team.save_state()
        except KeyboardInterrupt:
            print("\n程序已中断")
            break


asyncio.run(main())
