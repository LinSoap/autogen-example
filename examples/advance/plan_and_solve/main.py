import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination, TimeoutTermination,SourceMatchTermination,FunctionCallTermination
from autogen_agentchat.teams import RoundRobinGroupChat,SelectorGroupChat
from autogen_agentchat.tools import AgentTool,TeamTool
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.ui import Console
from config.model_config import model_client,default_model_info
import asyncio
import random

# tool_call_model_client = OpenAIChatCompletionClient(
#     model=os.getenv("OPENAI_MODEL", "deepseek-chat"),
#     api_key=os.getenv("OPENAI_API_KEY", ""),
#     base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
#     model_info=default_model_info,
# )

async def excel_fetch() -> str:
    """获取Excel的CSV格式字符串"""
    headers = ["ID", "姓名", "年龄", "成绩", "城市"]
    names = ["张伟", "王芳", "李强", "刘洋", "陈杰", "杨敏", "赵磊", "黄丽", "周鑫", "吴婷"]
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "南京", "苏州", "武汉"]

    rows = []
    for i in range(1, 11):
        row = [
            str(i),
            random.choice(names),
            str(random.randint(18, 30)),
            str(round(random.uniform(60, 100), 2)),
            random.choice(cities)
        ]
        rows.append(",".join(row))
    csv_data = ",".join(headers) + "\n" + "\n".join(rows)
    return csv_data


async def task_done() -> str:
    """用于标记任务完成"""
    return "任务已完成"

async def task_failed() -> str:
    """用于标记任务失败"""
    return "任务已失败"


excel_mcp_server = StdioServerParams(
    command="npx", args=["--yes", "@negokaz/excel-mcp-server"]
)

async def main():

    async with McpWorkbench(excel_mcp_server) as workbench:  # type: ignore
        analyzer = AssistantAgent(
            "analyzer",
            model_client=model_client,
            model_client_stream=True,
            workbench=workbench,
            system_message="你是一个数据分析师，你需要使用提供的工具来获取Excel数据，并进行分析。",
        )

        analyzer_critic = AssistantAgent(
            "analyzer_critic",
            model_client=model_client,
            model_client_stream=True,
            system_message="""
            你是一个数据分析检查员，你需要检查分析师的工作，并提出改进建议。判断分析结果是否完成了任务目标
            如果完成了，回复 '分析任务已完成'，否则指出问题并提供改进建议。
            """,
        )

        analyzer_team = RoundRobinGroupChat(
            [analyzer, analyzer_critic],
            name="analyzer_team",
            termination_condition=TextMentionTermination("分析任务已完成") | MaxMessageTermination(10)
        )


        analyzer_team_tool = TeamTool(
            team=analyzer_team,
            name="analyzer_team_tool",
            description="A tool for the analyzer team.",
            return_value_as_last_message=False,
        )

        writer = AssistantAgent(
            "writer",
            model_client=model_client,
            system_message="你是一个写作专家，负责生成专业且详细的报告。",
            model_client_stream=True
        )

        writer_tool = AgentTool(agent=writer)

        plan_agent = AssistantAgent(
            "plan_agent",
            model_client=model_client,
            tools=[task_done, task_failed, analyzer_team_tool, writer_tool],
            model_client_stream=True,
            system_message="""
            你是一个任务规划协调员。你擅长对用户的请求进行需求理解和任务分解。
            你总是会把任务分解成更小的子任务，并将其委托给适当的代理。
            使用一个任务清单检查和跟踪最后的任务是否完成。并在完成任务时勾选已完成的任务
            你需要根据目前的任务进度和子任务的完成情况，合理分配后续任务。在有必要时，更新任务清单。
            如果所有子任务都已完成，调用 `task_done` 工具标记最终任务完成。
            只有当
             - [x]
            所有子任务都完成后，才调用 `task_done` 工具标记最终任务完成。
            如果任务出现了失败，你首先考虑调整任务策略，仅当调整无效时，调用 `task_failed` 工具标记任务失败。
            如果是数据分析任务，为每个任务添加需要分析的问题。
            

            例如：
                - [ ] (analyzer)
                需要了解原始数据的结构和内容 (/home/数据分析.xlsx)
                - [ ] (analyzer)
                需要对原始数据进行建模,获取描述性统计信息（/home/数据分析.xlsx）
                - [ ] (writer)
                需要生成详细且专业的报告:

            以下是你可以委托的代理
            - analyzer: 会使用数据分析工具进行数据分析
            - writer: 负责生成报告详细且专业的报告
            根据目前已有的代理，设计合适的任务分配方案。

            """,
        )



        # 组合终止条件：任务完成、消息数限制、超时
        termination = (
            TimeoutTermination(120) |
            FunctionCallTermination(function_name="task_done")
        )
        team = RoundRobinGroupChat([plan_agent], termination_condition=termination)
        await Console(team.run_stream(task="帮我分析表，做出一些描述性统计分析，/home/linsoap/Downloads/前科重点人员 (副本).xlsx"), output_stats=True)


if __name__ == "__main__":
    asyncio.run(main())