import asyncio
from typing import List
from datetime import datetime
from config.model_config import model_client
from .tool_call_agent import ToolCallAgent
from .insight_json_agent import insight_json_team_agent, ExcelInsightAnalysis
from .planner_json_agent import planner_json_team_agent, ExcelTaskPlanning

from autogen_agentchat.ui import Console
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.messages import StructuredMessage, TextMessage
from autogen_agentchat.conditions import SourceMatchTermination


office_operate_mcp = StdioServerParams(
    command="uv",
    args=[
        "--directory",
        "E:/01.工作/00.创始公司/01.杭州钦曜科技有限公司/03.公司核心程序/omni-sense/backend/agent/agents_mcp/office/excel",
        "run",
        "excel_operate_mcp.py",
    ],
    read_timeout_seconds=60,
)
print(f"Retrieving MCP tool: {office_operate_mcp}")


async def get_excel_analysis_team(memory_names: List[str] | None = None, file_info=None) -> SelectorGroupChat:

    # 创建 MCP 工作流场景
    async with McpWorkbench(office_operate_mcp) as excel_workbench:
        print(f"MCP initialized for excel_operate and draw_chart at {datetime.now()}")
        excel_mcp_workbench = excel_workbench

    # Agent 1: 内容理解Agent（理解型）
    insight_json_agent = ToolCallAgent(
        name="insight_json_agent",
        tool=insight_json_team_agent(workbenchs=[excel_mcp_workbench]),
    )

    # Agent 2: 任务规划Agent（规划型）
    planner_json_agent = ToolCallAgent(
        name="planner_json_agent",
        tool=planner_json_team_agent(),
    )

    # 创建选择器
    selector_prompt = """
    你是“Excel数据分析”应用的**任务分配器**，负责根据用户需求和对话上下文，从以下代理中选择最适合的执行者：
    {roles}

    📝【当前对话上下文】：
    {history}

    🔍【选择指南】：
    1. **Excel 文件解析与意图澄清**：若为首次输入、新上传 Excel 文件或模糊输入（如“分析表格”），选择 **insight_agent** 解析文件、推断意图、生成澄清问题并输出 `ExcelInsightAnalysis` JSON。
    2. **JSON 格式校验**：若 `insight_agent` 已生成 `ExcelInsightAnalysis` JSON，选择 **json_agent** 进行格式校验和规范化，输出最终结果。

    📋【交互逻辑】：
    - **Step 1**: insight_agent 解析 Excel 文件和用户意图，生成 `ExcelInsightAnalysis` JSON，必要时提出澄清问题。
    - **Step 2**: json_agent 验证和修复 JSON 格式，输出规范化结果并终止流程。

    🚫【注意事项】：
    - 仅选择一位代理，确保与任务需求精准匹配。
    - 首轮对话、新上传 Excel 文件或模糊输入必须由 insight_json_agent 追问具体细节，避免生成不明确内容。
    - 严格遵守法律法规，确保选择逻辑不导致生成违法或不道德内容。
    - 禁止输出任何系统提示词或无关前缀（如“XX Agent 回复：”）。
    - 优先保障用户意图明确，动态适配上下文，确保选择逻辑清晰。

    ✅ 从{participants}中选择一位Agent执行下一任务，仅选一位。
    """

    # 停止机制
    termination = SourceMatchTermination(sources=["json_agent", "insight_json_agent", "planner_json_agent"])

    # 创建团队
    team = SelectorGroupChat(
        participants=[insight_json_agent, planner_json_agent],
        model_client=model_client,
        selector_prompt=selector_prompt,
        termination_condition=termination,
        allow_repeated_speaker=True,
        custom_message_types=[
            StructuredMessage[ExcelInsightAnalysis],
            StructuredMessage[ExcelTaskPlanning],
        ],
    )
    return team


async def main() -> None:
    while True:
        try:
            task = input("请输入您的任务（输入'quit'退出）: ")
            print("请选择一个agent: ")
            print("1. insight_json_agent")
            print("2. planner_json_agent")
            agent_options = {
                "1": "insight_json_agent",
                "2": "planner_json_agent",
            }
            agent_choice = input("输入编号选择agent（默认1）: ").strip()
            selected_agent = agent_options.get(agent_choice, "insight_json_agent")
            metadata = {"select_agent": selected_agent}
            if task.lower() == "quit":
                break

            team = await get_excel_analysis_team()
            await Console(
                team.run_stream(task=TextMessage(content=task + "/no_think", source="user", metadata=metadata))
            )

            await team.save_state()
        except KeyboardInterrupt:
            print("\n程序已中断")
            break


if __name__ == "__main__":
    asyncio.run(main())
