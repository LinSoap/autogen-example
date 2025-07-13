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

from .tool_call_agent import ToolCallAgent


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


def get_insight_agent_tool(memory: Optional[Sequence[Memory]] = None) -> ToolCallAgent:
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
        memory=memory,
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

    return insight_inner_team_tool
