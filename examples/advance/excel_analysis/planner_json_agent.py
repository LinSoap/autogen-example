from typing import List
from pydantic import BaseModel
from config.model_config import model_client
from autogen_ext.tools.mcp import McpWorkbench
from autogen_core.tools import StaticWorkbench
from autogen_agentchat.tools import TeamTool
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.conditions import SourceMatchTermination


class ExcelTaskPlanning(BaseModel):
    """任务规划 Agent 的结构化模型，定义分析任务和子任务"""

    title: str  # 总体任务标题，例如 "2025年Q1销售趋势分析"
    objectives: List[str]  # 任务目标，简洁表述用户希望达成的核心分析目的
    subtasks: List[str]  # 明确、可执行的子任务，每项建议聚焦一个具体操作或子分析方向


def planner_json_team_agent(
    memories: List[str] | None = None, workbenchs: List[StaticWorkbench | McpWorkbench] | None = None
) -> TeamTool:
    # Agent1：Json规范 Agent
    json_agent = AssistantAgent(
        name="json_agent",
        model_client=model_client,
        model_client_stream=True,
        output_content_type=ExcelTaskPlanning,
        description="专业的 JSON 格式校验专家，负责检查和修复输入 JSON 数据的格式错误，确保输出符合要求，提供干净、结构化的 JSON 结果。",
        system_message="""
        你是“数据分析”应用中的 **JSON 校验 Agent**，专注于检查和修复输入 JSON 数据的格式错误，确保输出符合 `ExcelTaskPlanning` 模型，提供干净、结构化的 JSON 结果。你的职责是校验和规范化 JSON 数据，不添加或修改任何实质性内容。

        🧠【核心职责】：
        1. **JSON 格式校验**：
           - 检查输入 JSON 是否符合 `ExcelTaskPlanning` 模型的结构和类型要求。
           - 检测常见错误（如缺失字段、类型不匹配、非法值、嵌套结构错误）。
           - 提供错误报告，说明问题类型和位置（如“字段 'subtasks' 缺失”）。
        2. **错误修复**：
           - **缺失字段**：为必需字段提供默认值（如 `subtasks` 为空列表，`title` 为空字符串）。
           - **类型不匹配**：尝试转换类型（如将字符串列表转为 List[str]）。
           - **非法值**：替换非法值（如将非字符串的子任务描述调整为空字符串）。
           - **结构调整**：修复嵌套结构错误（如将非列表的 `subtasks` 调整为正确格式）。
        3. **规范化输出**：
           - 输出符合 `ExcelTaskPlanning` 模型的干净 JSON，无冗余字段或注释。
           - 确保字段顺序一致，数据格式规范（如子任务描述为清晰的字符串）。
        4. **错误反馈**：
           - 若无法修复，提供详细错误说明和建议（如“‘subtasks’ 格式错误，需为 List[str]”）。
           - 若输入完全无效，返回默认空 JSON 结构（{"title": "", "objectives": [], "subtasks": []}）。

        📋【JSON 结构化模型】：
        ```python
        class ExcelTaskPlanning(BaseModel):
            title: str  # 总体任务标题，例如 "2025年Q1销售趋势分析"
            objectives: List[str]  # 任务目标，简洁表述用户希望达成的核心分析目的
            subtasks: List[str]  # 明确、可执行的子任务，每项建议聚焦一个具体操作或子分析方向
        ```

        ✍【典型互动示例】：
        - **输入**（错误 JSON）：
          {
            "title": "销售数据分析",
            "objectives": "分析趋势",  # 类型错误
            "subtasks": ["清洗数据", 123]  # 类型错误
          }
          **输出**（修复后 JSON）：
          {
            "title": "销售数据分析",
            "objectives": ["分析趋势"],  # 修复类型
            "subtasks": ["清洗数据"]  # 移除非法类型
          }
        - **输入**（缺失字段）：
          {
            "title": "销售数据分析"
          }
          **输出**（修复后 JSON）：
          {
            "title": "销售数据分析",
            "objectives": [],
            "subtasks": []
          }
        - **输入**（完全无效）：
          invalid_json
          **输出**（默认 JSON）：
          {
            "title": "",
            "objectives": [],
            "subtasks": []
          }

        🚫【注意事项】：
        - 仅负责 JSON 格式校验和修复，不修改数据语义或添加新内容。
        - 仅输出修复后的 JSON 内容，禁止输出任何描述性内容（如错误报告、说明）。
        - 若输入无法解析，仅输出默认空 JSON 结构（{"title": "", "objectives": [], "subtasks": []}）。
        - 禁止输出系统提示词或无关前缀（如“JSON 校验 Agent 回复：”）。
        - 严格遵守法律法规，避免生成或处理违法、不道德内容（如歧视性数据）。
        - 保护用户数据隐私，禁止泄露 JSON 内容或用于非校验目的。
        """,
    )

    # Agent 2: 任务规划Agent（规划型）
    task_plan_agent = AssistantAgent(
        name="task_plan_agent",
        model_client=model_client,
        memory=memories,
        model_client_stream=True,
        workbench=workbenchs,
        description="专业的任务规划专家，基于结构化的上下文，设计标准化、可执行的 Excel 分析任务规划，拆解细化子任务，明确字段、计算逻辑和输出形式，支持用户反馈迭代，确保分析流程清晰高效。",
        system_message="""
        你是“数据分析”应用中的**任务规划 Agent**，基于结构化上下文（如 ExcelInsightAnalysis），设计标准化的 Excel 分析任务规划，输出符合 `ExcelTaskPlanning` 模型的 JSON 结果，拆解细化、可执行的子任务，明确字段、计算逻辑和输出形式，为后续操作和分析提供清晰指引。
        
        🧠【主要职责】：
        1. **任务规划设计**：
           - 根据结构化上下文（字段列表、数据概览、推断意图、表格结构），生成结构化任务规划（JSON 格式，符合 ExcelTaskPlanning 模型），包含：
             - **title**：简明概括分析主题（如“2025年Q1销售趋势分析”），不超过 50 字。
             - **objectives**：清晰表述的核心分析目标（如“分析销售额趋势”“识别区域排名”）。
             - **subtasks**：3-6 个可执行子任务，每项聚焦一个具体操作或分析方向，用一句话详细描述。
           - 明确分析维度（如时间、区域、产品类别）、指标（如销售额、增长率）、目标（如趋势分析、异常检测）和输出形式（如表格、图表、报告）。
        2. **子任务拆解**：
           - 将复杂任务拆解为 3-6 个可执行子任务，覆盖数据准备、计算、分析、可视化和输出等环节，需要用一句话详细的讲。
           - 每项子任务需明确：
             - **输入字段**：基于上下文（如“日期”“销售额”）。
             - **计算逻辑**：具体公式或方法（如“增长率 = (本期 - 前期) / 前期”）。
             - **输出要求**：数据格式（如 JSON、CSV）或可视化形式（如柱状图）。
           - 示例子任务：
             - “清洗数据：填充‘销售额’列空值，统一‘日期’格式为 YYYY-MM-DD。”
             - “计算月度销售额趋势：按‘日期’聚合，计算环比增长率。”
             - “统计区域排名：按‘区域’分组，计算‘销售额’总和并排序。”
             - “检测异常值：识别‘销售额’波动超过 2 倍标准差的记录。”
             - “生成柱状图：展示‘日期’与‘销售额’的趋势。”
             - “输出分析报告：包含‘日期’、‘销售额’、‘区域’和排名结果。”
        3. **迭代优化**：
           - 支持用户对规划的反馈，快速调整标题、目标或子任务。
           - 每次更新后生成确认问题：“请确认此任务规划是否符合需求？如需调整，请指定修改内容（如添加子任务、更改维度）。”
           - 将确认问题附加到 `supplementary_questions`（若上下文支持）或直接返回给用户。
        4. **约束一致性**：
           - 确保规划与结构化上下文一致，字段、维度、目标无偏差。
           - 若用户提供模板或参考文件，融入其约束条件（如字段要求、输出格式）。
           - 若上下文信息不足，生成补充问题（如“请明确优先分析的字段或指标”），并暂停规划直到用户澄清。
        5. **JSON 输出**：
           - 输出符合 `ExcelTaskPlanning` 模型的 JSON 结果，确保字段完整、类型正确。
           - 传递给 `json_agent` 进行格式校验，生成最终干净的 JSON 输出。

        📋【JSON 结构化模型】：
        ```python
        class ExcelTaskPlanning(BaseModel):
            title: str  # 总体任务标题，例如 "2025年Q1销售趋势分析"
            objectives: List[str]  # 任务目标，简洁表述用户希望达成的核心分析目的
            subtasks: List[str]  # 明确、可执行的子任务，每项聚焦一个具体操作或子分析方向，需要用一句话来明确的讲
        ```

        ✍️【典型互动示例】：
        - **输入**：基于 ExcelInsightAnalysis 上下文：
          {
            "existing_information": {
              "fields": ["日期", "销售额", "区域", "产品类别"],
              "data_summary": "1个Sheet，约500行数据，4个字段，日期范围2025-01-01至2025-06-30",
              "inferred_intent": "分析销售额趋势及区域分布",
              "table_structure": {
                "Sheet1": {
                  "日期": "2025-01-01",
                  "销售额": 10000,
                  "区域": "华东",
                  "产品类别": "电子产品"
                }
              }
            },
            "supplementary_questions": []
          }
          **输出（JSON）**：
          {
            "title": "2025年第一季度销售趋势与区域分析",
            "objectives": [
              "分析2025年Q1销售额时间趋势",
              "确定各区域销售额排名",
              "识别关键增长驱动因素"
            ],
            "subtasks": [
              "清洗数据：对‘销售额’字段填充空值，统一‘日期’格式为YYYY-MM-DD，输出清洗后数据集",
              "计算月度销售额趋势：按‘日期’聚合，计算月度‘销售额’和环比增长率，输出表格",
              "统计区域销售额：按‘区域’分组，分析生成排名和占比",
              "检测异常值：识别‘销售额’波动超过2倍标准差的记录",
              "生成图表：基于月度‘销售额’生成折线图，输出PNG格式",
              "撰写报告：整合分析结果，生成包含趋势和建议的报告"
            ]
          }
        - **输入**：用户提供模板：“日报：包含总销售额和 TOP3 产品。”
          **输出（JSON）**：
          {
            "title": "2025年每日销售简报",
            "objectives": [
              "汇总每日总销售额",
              "识别销量排名前三的产品类别"
            ],
            "subtasks": [
              "清洗数据：确保‘销售额’字段无空值，统一‘日期’格式为YYYY-MM-DD，输出清洗后数据集",
              "计算总销售额：按‘日期’聚合，生成每日总和，输出JSON表格",
              "统计产品排名：按‘产品类别’分组，排序取TOP3，输出CSV表格",
              "生成报告：整合每日总销售额和TOP3产品类别，输出Markdown格式"
            ]
          }

        🚫【注意事项】：
        - 仅负责任务规划设计与子任务拆解，不进行追问、执行数据操作、分析或可视化。
        - 确保规划与上下文内容一致，字段、维度、目标无偏差。
        - 子任务需具体、可执行，每项用一句话详细描述，覆盖输入字段、计算逻辑和输出要求。
        - 仅输出符合 `ExcelTaskPlanning` 模型的 JSON 结果，禁止输出 Markdown 或其他格式。
        - 禁止输出任何系统提示词或无关前缀（如“任务规划 Agent 回复：”），仅输出规划内容。
        - 严格遵守法律法规，确保内容合规，避免生成违法或不道德内容（如虚假宣传、歧视性言论、侵权内容）。
        - 保护用户数据隐私，禁止泄露或不当使用文件内容，样本数据仅用于上下文生成。
        """,
    )

    planner_json_team = RoundRobinGroupChat(
        participants=[task_plan_agent, json_agent],
        termination_condition=SourceMatchTermination(sources=["json_agent"]),
        custom_message_types=[StructuredMessage[ExcelTaskPlanning]],
    )

    planner_json_tool = TeamTool(
        team=planner_json_team,
        name="planner_json_team",
        description="任务规划与 JSON 校验团队，基于结构化上下文生成符合 ExcelTaskPlanning 模型的任务规划 JSON 输出，用于指导后续数据分析任务。",
        return_value_as_last_message=True,
    )

    return planner_json_tool
