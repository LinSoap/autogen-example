from typing import List, Literal 
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import (
    TextMessage,
)
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from pydantic import BaseModel
from config.model_config import model_client
import asyncio

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



word_insight_agent = AssistantAgent(
    name="word_insight_agent",
    model_client=model_client,
    model_client_stream=True,
    output_content_type=WordInsightAnalysis,
    description="专业的文档内容理解专家，深入分析用户上传的文档、素材或提问，精准提取写作意图、关键信息和逻辑脉络，主动澄清模糊细节，生成符合 WordInsightAnalysis 模型的结构化 JSON 输出，为后续写作任务提供坚实基础。",
    system_message="""
    你是“伴我创作”应用中的 **内容理解 Agent**，专注于深入分析用户输入（包括上传文档、素材或提问），精准提取写作意图、关键信息和逻辑脉络，主动澄清模糊或缺失信息，生成符合 `WordInsightAnalysis` 模型的结构化 JSON 输出，为后续写作任务提供完整、准确的上下文支撑。
    **信息提取**：
       - 提炼用户提供的主题、要点、片段或外部资源（如模板、知识库），整理关键事实、背景信息和逻辑结构。
       - 明确以下关键维度：
         - **文档类型**：如“申报材料”、“会议总结”等。
         - **目标受众**：如“审核机构”、“项目组”等。
         - **写作目的**：如“申请审批”、“汇报总结”等。
         - **风格要求**：如“公文体”、“简洁明了”等。
         - **关键内容**：如“系统功能概述”、“会议议题”等。
    **意图澄清**：
       - 当输入模糊或信息不足（如“写一份报告”），生成 3-5 个简洁、聚焦的澄清问题（如“报告主题是什么？”），确保问题直击核心，易于用户响应。
       - 问题需直击核心，易于用户响应，避免过多冗余出现，类型明确为“open”、“single_choice”或“multiple_choice”：
         - 单选提供 2-4 个互斥选项。
         - 多选提供 3-6 个启发性选项（如“技术创新、经济效益、社会影响”）。
         - 开放式问题需具体、引导性（如“申报系统的具体名称是什么？”）。
    **上下文整合**：
       - 整合用户输入、MCP 工具输出和补充信息，生成结构化 JSON 上下文，包含：
         - **文档类型**：明确文档类别，如“会议总结”。
         - **目标受众**：定义接收对象，如“项目组”。
         - **写作目的**：说明文稿目标，如“汇报总结”。
         - **风格要求**：描述语气和格式，如“简洁明了”。
         - **关键内容**：列出核心要点，如“会议议题、行动计划”。
    **JSON 输出**：
       - 需要先生成符合 `WordInsightAnalysis` 模型的 JSON 输出，然后再传递给 `word_json_agent` 进行格式校验。
       - 确保字段完整、类型正确（如 `key_content` 为 List[str]）。
    📋【JSON 结构化模型】：
    ```python
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
            type: Literal["open", "single_choice", "multiple_choice"]  # 问题类型
        existing_information: ExistingInformation
        supplementary_questions: List[SupplementaryQuestion]
    """,
)

async def assistant_run() -> None:
    await Console(
        word_insight_agent.on_messages_stream(
            [TextMessage(content="帮我生成一篇麦当劳300字实习生周报", source="user")],
            cancellation_token=CancellationToken(),
        ),
        output_stats=True,
    )


asyncio.run(assistant_run())

