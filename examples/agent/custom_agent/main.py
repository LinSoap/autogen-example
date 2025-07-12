from typing import Any, Awaitable, Callable, List, Sequence

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool, FunctionTool
import asyncio
from pydantic import BaseModel


class ToolCallAgent(BaseChatAgent):
    def __init__(
        self,
        name: str,
        description: str = "An agent that provides assistance with ability to use tools.",
        tools: (
            List[
                BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]
            ]
            | None
        ) = None,
    ):
        super().__init__(name=name, description=description)
        self._tools: List[BaseTool[Any, Any]] = []
        if tools is not None:
            for tool in tools:
                if isinstance(tool, BaseTool):
                    self._tools.append(tool)
                elif callable(tool):
                    if hasattr(tool, "__doc__") and tool.__doc__ is not None:
                        description = tool.__doc__
                    else:
                        description = ""
                    self._tools.append(FunctionTool(tool, description=description))
                else:
                    raise ValueError(f"Unsupported tool type: {type(tool)}")
        # 确保工具名称唯一
        tool_names = [tool.name for tool in self._tools]
        if len(tool_names) != len(set(tool_names)):
            raise ValueError(f"Tool names must be unique: {tool_names}")

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:

        class ArgsModel(BaseModel):
            city: str = messages[-1].content

        args = ArgsModel()
        response = await self._tools[0].run(
            args=args, cancellation_token=cancellation_token
        )
        return response

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


async def run_tool_call_agent() -> None:
    async def get_weather(city: str) -> str:
        """根据给定城市获取天气信息"""
        return f"{city}的天气是晴天，温度25度。"

    tool_call_agent = ToolCallAgent(
        "tool_call_agent",
        description="这是一个自动调用第一个工具的智能体",
        tools=[get_weather],
    )

    tool_call_result = await tool_call_agent.on_messages(
        messages=[TextMessage(content="北京", source="user")],
        cancellation_token=CancellationToken(),
    )
    print(tool_call_result)


asyncio.run(run_tool_call_agent())
