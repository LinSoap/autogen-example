from pydantic import BaseModel
from typing import Any, AsyncGenerator, Awaitable, Callable, List, Optional, Sequence

from autogen_core import CancellationToken
from autogen_core.memory import Memory
from autogen_core.tools import BaseTool, FunctionTool
from autogen_core.model_context import ChatCompletionContext, UnboundedChatCompletionContext

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage, MemoryQueryEvent


class ToolTaskArgs(BaseModel):
    """Input for the TaskRunnerTool."""

    task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None


class ToolCallAgent(BaseChatAgent):
    """
    An agent that provides assistance with tool usage capabilities.
    This class extends BaseChatAgent to handle messages, interact with tools,
    and manage memory and model context for task execution.

    Args:
        name: The name of the agent.
        description: A brief description of the agent's purpose. Defaults to a generic description.
        memory: A sequence of memory stores for contextual data. Defaults to None.
        model_context: The context for chat completion. Defaults to UnboundedChatCompletionContext if None.
        tool: A tool instance or callable to be used by the agent. Must be a BaseTool or callable.
    """

    def __init__(
        self,
        name: str,
        description: str = "An agent that provides assistance with ability to use tools.",
        memory: Optional[Sequence[Memory]] = None,
        model_context: Optional[ChatCompletionContext] = None,
        tool: Optional[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]] = None,
    ) -> None:
        super().__init__(name=name, description=description)
        self._memory = self._validate_memory(memory)
        self._tool = self._validate_tool(tool)
        self._model_context = model_context or UnboundedChatCompletionContext()

    def _validate_memory(self, memory: Optional[Sequence[Memory]]) -> Optional[List[Memory]]:
        """Validate and convert memory input to a list of Memory objects."""
        if memory is None:
            return None
        if not isinstance(memory, (list, tuple)):
            raise TypeError(f"Expected Sequence[Memory] or None, got {type(memory)}")
        return list(memory)

    def _validate_tool(self, tool: Optional[BaseTool | Callable[..., Any] | Callable[..., Awaitable[Any]]]) -> BaseTool:
        """Validate and convert tool input to a BaseTool instance."""
        if tool is None:
            raise ValueError("Tool cannot be None")
        if isinstance(tool, BaseTool):
            return tool
        if callable(tool):
            description = getattr(tool, "__doc__", "") or "No description provided"
            return FunctionTool(tool, description=description)
        raise ValueError(f"Unsupported tool type: {type(tool)}")

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext, messages: Sequence[BaseChatMessage]
    ) -> None:
        """Add incoming messages to the model context."""
        for msg in messages:
            await model_context.add_message(msg.to_model_message())

    @staticmethod
    async def _update_model_context_with_memory(
        memory: Optional[Sequence[Memory]], model_context: ChatCompletionContext, agent_name: str
    ) -> List[MemoryQueryEvent]:
        """Update model context with relevant memory content."""
        events: List[MemoryQueryEvent] = []
        if memory:
            for mem in memory:
                result = await mem.update_context(model_context)
                if result and result.memories.results:
                    events.append(MemoryQueryEvent(content=result.memories.results, source=agent_name))
        return events

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        """Return the types of messages this agent can produce."""
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        """Handle incoming messages and return a response."""
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("No final response produced in streaming mode.")

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """Stream events, messages, or responses based on incoming messages."""
        # step 1: Add new messages to the model context
        await self._add_messages_to_context(self._model_context, messages)

        # STEP 2: Update model context with memory, yielding memory query events
        for event in await self._update_model_context_with_memory(
            memory=self._memory,
            model_context=self._model_context,
            agent_name=self.name,
        ):
            yield event

        # STEP 3: Process tool execution and stream results
        async for inference_output in self._tool.run_stream(
            args=ToolTaskArgs(task=messages[-1].content),
            cancellation_token=cancellation_token,
        ):
            # Streaming chunk event
            if isinstance(inference_output, TaskResult):
                await self._model_context.add_message(inference_output.messages[-1].to_model_message())
                yield Response(chat_message=inference_output.messages[-1])
            else:
                if inference_output.source == "user":
                    continue
                yield inference_output

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the agent's state."""
        pass
