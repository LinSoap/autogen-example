from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from config.model_config import model_client
import asyncio

agent = AssistantAgent(
    name="assistant_agent",
    model_client=model_client,
    system_message="你是一个智能助手，擅长回答用户的问题。",
    model_client_stream=True,
)


async def assistant_run() -> None:
    await Console(
        agent.on_messages_stream(
            [TextMessage(content="你可以做什么", source="user")],
            cancellation_token=CancellationToken(),
        ),
        output_stats=True,
    )


asyncio.run(assistant_run())
