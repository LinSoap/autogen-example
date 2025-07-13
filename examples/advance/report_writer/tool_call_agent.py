from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    List,
    Literal,
    Optional,
    Sequence,
)

from autogen_agentchat.base import TaskResult
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    TextMessage,
    MemoryQueryEvent,
)
from autogen_core import CancellationToken
from autogen_core.memory import Memory
from autogen_core.tools import BaseTool, FunctionTool
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
)
from pydantic import BaseModel

# -------------------- 类型和数据模型 --------------------


class TaskRunnerToolArgs(BaseModel):
    """Input for the TaskRunnerTool."""

    # task: Annotated[str, "The task to be executed."]

    # 修改了源码
    task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = (None,)


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


# -------------------- 工具和 Agent 类定义 --------------------


class ToolCallAgent(BaseChatAgent):
    def __init__(
        self,
        name: str,
        description: str = "An agent that provides assistance with ability to use tools.",
        model_context: ChatCompletionContext | None = None,
        memory: Sequence[Memory] | None = None,
        tool: (
            BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]
        ) = None,
    ):
        super().__init__(name=name, description=description)
        self._memory = None
        if memory is not None:
            if isinstance(memory, list):
                self._memory = memory
            else:
                raise TypeError(
                    f"Expected Memory, List[Memory], or None, got {type(memory)}"
                )
        if isinstance(tool, BaseTool):
            self._tool = tool
        elif callable(tool):
            if hasattr(tool, "__doc__") and tool.__doc__ is not None:
                description = tool.__doc__
            else:
                description = ""
            self._tool = FunctionTool(tool, description=description)
        else:
            raise ValueError(f"Unsupported tool type: {type(tool)}")

        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        agent_name = self.name
        memory = self._memory
        model_context = self._model_context

        # STEP 1: Add new user/handoff messages to the model context
        await self._add_messages_to_context(
            model_context=model_context,
            messages=messages,
        )

        # STEP 2: Update model context with any relevant memory
        inner_messages: List[BaseAgentEvent | BaseChatMessage] = []
        for event_msg in await self._update_model_context_with_memory(
            memory=memory,
            model_context=model_context,
            agent_name=agent_name,
        ):
            inner_messages.append(event_msg)
            yield event_msg

        # STEP 3: Generate a message ID for correlation between streaming chunks and final message

        async for inference_output in self._tool.run_stream(
            args=TaskRunnerToolArgs(task=messages[-1].content),
            cancellation_token=cancellation_token,
        ):
            # Streaming chunk event
            if isinstance(inference_output, TaskResult):
                await model_context.add_message(
                    inference_output.messages[-1].to_model_message()
                )
                yield Response(chat_message=inference_output.messages[-1])
            else:
                if inference_output.source == "user":
                    continue
                yield inference_output

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext,
        messages: Sequence[BaseChatMessage],
    ) -> None:
        """
        Add incoming messages to the model context.
        """
        for msg in messages:
            await model_context.add_message(msg.to_model_message())

    @staticmethod
    async def _update_model_context_with_memory(
        memory: Optional[Sequence[Memory]],
        model_context: ChatCompletionContext,
        agent_name: str,
    ) -> List[MemoryQueryEvent]:
        """Update model context with memory content.

        Args:
            memory: Optional sequence of memory stores to query
            model_context: Context to update with memory content
            agent_name: Name of the agent for event tracking

        Returns:
            List of memory query events generated during update
        """
        events: List[MemoryQueryEvent] = []
        if memory:
            for mem in memory:
                update_context_result = await mem.update_context(model_context)
                if (
                    update_context_result
                    and len(update_context_result.memories.results) > 0
                ):
                    memory_query_event_msg = MemoryQueryEvent(
                        content=update_context_result.memories.results,
                        source=agent_name,
                    )
                    events.append(memory_query_event_msg)
        return events

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass
