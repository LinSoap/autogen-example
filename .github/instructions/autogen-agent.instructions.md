---
applyTo: '**/*.py'
---
AutoGen Agent 规则与最佳实践

Agent 定义
Agent 是具备独立身份、能力和工具集的智能体，负责处理指定任务。
每个 Agent 需明确命名、分配模型、设定系统提示（system_message），可选工具集（tools）。
Agent 类型
AssistantAgent：通用型助手，适合大多数任务。
Agent 配置
推荐使用 OpenAIChatCompletionClient 或兼容模型作为 model_client。
system_message 应简明描述 Agent 角色和行为。
tools 参数用于注入函数或外部工具，提升 Agent 能力。
Agent 交互
通过 run 或 run_stream 方法执行任务，支持异步流式输出。
可与其他 Agent 组队协作，或单独完成任务。
支持多步推理、工具调用、上下文记忆。
终止与控制
可设置终止条件（如 TextMentionTermination、ExternalTermination）灵活控制 Agent 生命周期。
支持 reset() 重置状态，set() 触发外部终止，cancellation_token 实现即时中断。
代码规范
优先使用官方推荐 API 和结构，注重可读性与可扩展性。
Agent 相关代码需便于行为观察和调试，支持团队协作扩展。
示例代码

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


这是我的 Agent 创建时需要的所有参数
name (str) – The name of the agent.

model_client (ChatCompletionClient) – The model client to use for inference.

tools (List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None, optional) – The tools to register with the agent.

workbench (Workbench | Sequence[Workbench] | None, optional) – The workbench or list of workbenches to use for the agent. Tools cannot be used when workbench is set and vice versa.

handoffs (List[HandoffBase | str] | None, optional) – The handoff configurations for the agent, allowing it to transfer to other agents by responding with a HandoffMessage. The transfer is only executed when the team is in Swarm. If a handoff is a string, it should represent the target agent’s name.

model_context (ChatCompletionContext | None, optional) – The model context for storing and retrieving LLMMessage. It can be preloaded with initial messages. The initial messages will be cleared when the agent is reset.

description (str, optional) – The description of the agent.

system_message (str, optional) – The system message for the model. If provided, it will be prepended to the messages in the model context when making an inference. Set to None to disable.

model_client_stream (bool, optional) – If True, the model client will be used in streaming mode. on_messages_stream() and BaseChatAgent.run_stream() methods will also yield ModelClientStreamingChunkEvent messages as the model client produces chunks of response. Defaults to False.

reflect_on_tool_use (bool, optional) – If True, the agent will make another model inference using the tool call and result to generate a response. If False, the tool call result will be returned as the response. By default, if output_content_type is set, this will be True; if output_content_type is not set, this will be False.

output_content_type (type[BaseModel] | None, optional) – The output content type for StructuredMessage response as a Pydantic model. This will be used with the model client to generate structured output. If this is set, the agent will respond with a StructuredMessage instead of a TextMessage in the final response, unless reflect_on_tool_use is False and a tool call is made.

output_content_type_format (str | None, optional) – (Experimental) The format string used for the content of a StructuredMessage response.

max_tool_iterations (int, optional) – The maximum number of tool iterations to perform until the model stops making tool calls. Defaults to 1, which means the agent will only execute the tool calls made by the model once, and return the result as a ToolCallSummaryMessage, or a TextMessage or a StructuredMessage (when using structured output) in chat_message as the final response. As soon as the model stops making tool calls, the agent will stop executing tool calls and return the result as the final response. The value must be greater than or equal to 1.

tool_call_summary_format (str, optional) – Static format string applied to each tool call result when composing the ToolCallSummaryMessage. Defaults to "{result}". Ignored if tool_call_summary_formatter is provided. When reflect_on_tool_use is False, the summaries for all tool calls are concatenated with a newline (’n’) and returned as the response. Placeholders available in the template: {tool_name}, {arguments}, {result}, {is_error}.

tool_call_summary_formatter (Callable[[FunctionCall, FunctionExecutionResult], str] | None, optional) –

Callable that receives the FunctionCall and its FunctionExecutionResult and returns the summary string. Overrides tool_call_summary_format when supplied and allows conditional logic — for example, emitting static string like "Tool FooBar executed successfully." on success and a full payload (including all passed arguments etc.) only on failure.

Limitation: The callable is not serializable; values provided via YAML/JSON configs are ignored.


对于每个Agent，最好开启 model_client_stream 模式，这样可以在控制台实时查看 Agent 的输出。