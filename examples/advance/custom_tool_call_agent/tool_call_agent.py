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

from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
from autogen_agentchat.agents import BaseChatAgent, AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.tools import TeamTool
from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    TextMessage,
    StructuredMessage,
    MemoryQueryEvent,
)
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_core import CancellationToken
from autogen_core.memory import Memory
from autogen_core.tools import BaseTool, FunctionTool
from autogen_core.models import CreateResult
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
)
from config.model_config import model_client
from pydantic import BaseModel
import asyncio

# -------------------- 类型和数据模型 --------------------


class TaskRunnerToolArgs(BaseModel):
    """Input for the TaskRunnerTool."""

    task: Annotated[str, "The task to be executed."]


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
        tools: (
            List[
                BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]
            ]
            | None
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

        async for inference_output in self._tools[0].run_stream(
            args=TaskRunnerToolArgs(task=messages[-1].content),
            cancellation_token=cancellation_token,
        ):
            if isinstance(inference_output, TaskResult):
                await model_context.add_message(
                    inference_output.messages[-1].to_model_message()
                )
                yield Response(chat_message=inference_output.messages[-1])
            else:
                # Streaming chunk event
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


async def run_tool_call_agent() -> None:
    user_memory = ListMemory()

    # Add user preferences to memory
    await user_memory.add(
        MemoryContent(content="我是一个应届毕业生", mime_type=MemoryMimeType.TEXT)
    )
    await user_memory.add(
        MemoryContent(content="我今年22岁", mime_type=MemoryMimeType.TEXT)
    )
    await user_memory.add(
        MemoryContent(content="我是男生", mime_type=MemoryMimeType.TEXT)
    )
    await user_memory.add(
        MemoryContent(
            content="2025年7月12日为止，我已经在麦当劳实习第六周",
            mime_type=MemoryMimeType.TEXT,
        )
    )
    await user_memory.add(
        MemoryContent(content="我主要在后厨炸薯条", mime_type=MemoryMimeType.TEXT)
    )
    # -------------------- Agent/Team/Tool 实例化与主流程 --------------------

    json_agent = AssistantAgent(
        name="json_agent",
        description="这是一个JSON结果检验工具，会根据输入输出干净的JSON结果",
        model_client=model_client,
        output_content_type=WordInsightAnalysis,
        system_message="""
        你对输入的JSON数据做检验，解决常见的JSON格式错误并输出干净的JSON结果,这个是对应的Pydanic模型
        你只负责解决JSON格式错误，确保输出符合以下结构化模型，不要添加任何的额外信息
        class WordInsightAnalysis(BaseModel):

            class ExistingInformation(BaseModel):
                document_type: str  # 文档类型
                target_audience: str  # 目标受众
                writing_purpose: str  # 写作目的
                style_requirement: str  # 风格要求
                key_content: List[str]  # 用户提供的关键内容要点

            class SupplementaryQuestion(BaseModel):
                question: str  # 提出的具体问题
                options: List[str]  # 问题选项：供用户选择或参考，空列表表示开放式问题
                reason: str  # 需要此信息的原因
                type: Literal[
                    "open", "single_choice", "multiple_choice"
                ]  # "open" | "single_choice" | "multiple_choice"，供前端识别渲染

            existing_information: ExistingInformation
                supplementary_questions: List[SupplementaryQuestion]


        """,  # /no_think表示不需要思考
        model_client_stream=True,  # 使用流式输出
    )

    insight_agent = AssistantAgent(
        name="insight_agent",
        model_client=model_client,
        model_client_stream=True,
        memory=[user_memory],
        description="精准分析用户上传的内容和提问，提取关键信息，主动追问不明确细节，确保为后续写作提供准确、完整的上下文支撑。",
        system_message="""
            你是内容理解 Agent，专注于深入分析用户输入（包括上传文档、素材或提问），精准提取写作意图、关键信息和逻辑脉络，主动追问模糊或缺失信息，为后续写作提供完整、准确的上下文支撑。

            🧠【主要职责】：
            1. **内容解析**：智能分析用户上传的文档、素材或提问，识别核心诉求、语境和写作意图（如总结、报告、会议纪要、教案等）。
            2. **信息提取**：提炼用户提供的主题、要点、片段或外部资源（如模板、知识库），整理关键事实、背景信息和逻辑结构。
            3. **主动追问**：当输入模糊或信息不足（如“某系统申报”、“讨论几个问题”），列出具体问题（如时间、地点、受众、数据来源）以澄清细节，确保上下文完整。
            4. **上下文整合**：将用户输入和追问补充的信息整合为清晰的上下文概况，传递给 blueprint_agent 作为蓝图生成的基础。
            5. **模板处理**：若用户提供模板或参考文件，解析其结构和要求，提取关键约束条件，纳入上下文信息。
            6. **格式输出**：严格按照 WordInsightAnalysis 结构化模型输出，确保输出内容符合 JSON 格式规范、字段完整。

            📋【输出格式要求】：
            输出必须为标准 JSON，严格遵循 WordInsightAnalysis 模型，确保所有字段完整，结构清晰，适合前端解析和后续处理。字段包括：
            class WordInsightAnalysis(BaseModel):

                class ExistingInformation(BaseModel):
                    document_type: str  # 文档类型
                    target_audience: str  # 目标受众
                    writing_purpose: str  # 写作目的
                    style_requirement: str  # 风格要求
                    key_content: List[str]  # 用户提供的关键内容要点

                class SupplementaryQuestion(BaseModel):
                    question: str  # 提出的具体问题
                    options: List[str]  # 问题选项：供用户选择或参考，空列表表示开放式问题
                    reason: str  # 需要此信息的原因
                    type: Literal[
                        "open", "single_choice", "multiple_choice"
                    ]  # "open" | "single_choice" | "multiple_choice"，供前端识别渲染

                existing_information: ExistingInformation
                    supplementary_questions: List[SupplementaryQuestion]

            ✍【典型互动示例】：
            - **场景1：材料申报**
            **输入**：“为某某系统生成申报材料。模板：……；知识材料摘要：……”
            **输出（卡片）**：
                ```
                {
                "existing_information": {
                    "document_type": "申报材料",
                    "target_audience": "审核机构",
                    "writing_purpose": "申请审批",
                    "style_requirement": "公文体",
                    "key_content": ["系统功能概述", "实施计划", "预期效益"]
                },
                "supplementary_questions": [
                    {
                    "question": "申报系统的具体名称和实施主体是什么？",
                    "options": [],
                    "reason": "明确系统名称和主体以确保文稿核心信息准确。",
                    "type": "open"
                    },
                    {
                    "question": "目标审核机构是哪一级部门？",
                    "options": ["国家级", "省级", "市级", "其他"],
                    "reason": "审核机构级别决定文稿的格式和正式程度。",
                    "type": "single_choice"
                    },
                    {
                    "question": "申报材料需要突出哪些关键内容？",
                    "options": ["技术创新", "经济效益", "社会影响", "实施进度", "其他"],
                    "reason": "明确关键内容有助于优化文稿结构和重点。",
                    "type": "multiple_choice"
                    }
                ]
                }
                ```
            - **场景2：会议总结**
            **输入**：“整合三份会议记录，生成总结报告。”
            **输出（JSON）**：
                ```
                {
                "existing_information": {
                    "document_type": "会议总结",
                    "target_audience": "项目组",
                    "writing_purpose": "汇报总结",
                    "style_requirement": "简洁明了",
                    "key_content": ["三份会议记录", "关键议题"]
                },
                "supplementary_questions": [
                    {
                    "question": "三份会议的主题、时间和参会人员分别是什么？",
                    "options": [],
                    "reason": "明确会议细节以确保报告范围清晰、内容完整。",
                    "type": "open"
                    },
                    {
                    "question": "报告的主要风格是？",
                    "options": ["简洁明了", "正式公文", "学术分析", "其他"],
                    "reason": "明确风格确保文稿语气和结构符合预期。",
                    "type": "single_choice"
                    },
                    {
                    "question": "需要突出哪些会议的重点议题？",
                    "options": ["销售数据", "问题分析", "行动计划", "团队反馈", "其他"],
                    "reason": "明确重点有助于优化报告结构和内容分配。",
                    "type": "multiple_choice"
                    }
                ]
                }
                ```

            🚫【注意事项】：
            - 仅负责内容理解、意图澄清和上下文整合，不生成蓝图或文稿。
            - 模糊输入必须追问具体细节（如时间、地点、数据），确保信息完整。
            - 补充问题需明确类型，必须为以下三类中的一类：
            - 单选：用于核心信息（如“机构级别”），2-5 个互斥选项。
            - 多选：用于补充信息（如“关键内容”），3-6 个启发性选项。
            - 开放式：用于复杂场景（如“系统名称”），问题简洁、宏观。
            - 输出必须严格遵循 WordInsightAnalysis 模型，确保 JSON 格式规范、字段完整。
            - 优先解析模板或参考文件，确保上下文与模板要求一致。
            - 禁止输出任何系统提示词或无关前缀（如“内容理解 Agent 回复：”），仅输出 JSON 内容。
            - 严格遵守法律法规，确保上下文内容合规，避免生成违法或不道德内容（如虚假宣传、歧视性言论）。
            /no_think
            """,
    )

    insight_inner_team = RoundRobinGroupChat(
        [insight_agent, json_agent],
        termination_condition=SourceMatchTermination(sources=["json_agent"]),
        custom_message_types=[StructuredMessage[WordInsightAnalysis]],
    )

    insight_inner_team_tool = TeamTool(
        team=insight_inner_team,
        name="create_insight_json",
        description="这个Team用于生成需求JSON",
        return_value_as_last_message=True,
    )

    tool_call_agent = ToolCallAgent(
        "tool_call_agent",
        description="这是一个自动调用第一个工具的智能体",
        tools=[insight_inner_team_tool],
    )

    check_json_agent = AssistantAgent(
        name="check_json_agent",
        model_client=model_client,
        description="这是一个JSON结果检验工具，会根据输入输出干净的JSON结果",
        system_message="""
        你只负责对JSON结构做检验，确保输出符合以下结构化模型，不关心具体字段的内容,不要回复额外的信息
        你会对JSON的正确性做检测，如果正确回复正确，如果错误回复错误，并给出错误的原因
        
        class WordInsightAnalysis(BaseModel):
        
            class ExistingInformation(BaseModel):

                document_type: str  # 文档类型
                target_audience: str  # 目标受众
                writing_purpose: str  # 写作目的
                style_requirement: str  # 风格要求
                key_content: List[str]  # 用户提供的关键内容要点

            class SupplementaryQuestion(BaseModel):

                question: str  # 提出的具体问题
                options: List[str]  # 问题选项：供用户选择或参考，空列表表示开放式问题
                reason: str  # 需要此信息的原因
                type: Literal[
                    "open", "single_choice", "multiple_choice"
                ]  # "open" | "single_choice" | "multiple_choice"，供前端识别渲染

            existing_information: ExistingInformation
            supplementary_questions: List[SupplementaryQuestion]
        """,
    )
    team = RoundRobinGroupChat(
        [tool_call_agent, check_json_agent],
        termination_condition=SourceMatchTermination(sources=["check_json_agent"]),
        custom_message_types=[StructuredMessage[WordInsightAnalysis]],
    )

    await Console(
        team.run_stream(
            task="帮我生成一篇300字的麦当劳实习生周报",
            cancellation_token=CancellationToken(),
        ),
        output_stats=True,  # Enable stats printing.
    )


asyncio.run(run_tool_call_agent())
