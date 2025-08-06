from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_agentchat.ui import Console
from config.model_config import model_client
import asyncio

web_surfer_agent = MultimodalWebSurfer(
    name="MultimodalWebSurfer",
    model_client=model_client
)



async def assistant_run() -> None:
    await Console(
        web_surfer_agent.on_messages_stream(
            [TextMessage(content="今天特斯拉的股票价格是多少？", source="user")],
            cancellation_token=CancellationToken(),
        ),
        output_stats=True,
    )


asyncio.run(assistant_run())

