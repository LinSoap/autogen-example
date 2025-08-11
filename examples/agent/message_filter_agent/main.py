from autogen_agentchat.agents import AssistantAgent, MessageFilterAgent, MessageFilterConfig, PerSourceFilter
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from config.model_config import model_client
import asyncio

name_agent = AssistantAgent(
    name="name_agent",
    model_client=model_client,
    system_message="你负责提取用户的名字",
    model_client_stream=True,
)

age_agent = AssistantAgent(
    name="age_agent",
    model_client=model_client,
    system_message="你负责提取用户的年龄",
    model_client_stream=True,
)

filter_age_agent = MessageFilterAgent(
    name="filter_age_agent",
    wrapped_agent=age_agent,
    filter=MessageFilterConfig(
        per_source=[
            PerSourceFilter(source="name_agent", position="last", count=1),
        ]
    ),
)

team = RoundRobinGroupChat(
    [name_agent, filter_age_agent],
    termination_condition=SourceMatchTermination(sources=["age_agent"])
)


async def assistant_run() -> None:
    await Console(
        team.run_stream(
            task=
            [TextMessage(content="我叫张伟，今年18岁", source="user")],

        ),
        output_stats=True,
    )


asyncio.run(assistant_run())

