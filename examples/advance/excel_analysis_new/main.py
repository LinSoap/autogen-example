from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from config.model_config import model_client
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_agentchat.conditions import (
    MaxMessageTermination,
    TextMentionTermination,
    HandoffTermination,
)
import asyncio


async def main():
    # 定义三个 Agent
    planer = AssistantAgent(
        name="planer",
        model_client=model_client,
        handoffs=["analyzer", "writer", "user_proxy"],
        system_message="""
        你是一个任务规划协调员。你擅长对用户的请求进行需求理解和任务分解。
        你总是会把任务分解成更小的子任务，并将其委托给适当的代理。
        使用一个任务清单检查和跟踪最后的任务是否完成。并在完成任务时勾选已完成的任务
        在所有任务完成后回复`任务已完成`

        例如：
            - [ ] 需要了解原始数据的结构和内容
            - [ ] 需要对原始数据进行清洗和建模
            - [ ] 需要生成详细且专业的报告:

        以下是你可以委托的代理
        - analyzer: 会使用数据分析工具进行数据分析
        - writer: 负责生成报告详细且专业的报告
        - user_proxy: 负责与用户进行交互
        总是先发送你的计划,然后交给适当的代理。
        总是一次交给一个代理。
        """,
        model_client_stream=True,
    )

    user_proxy = UserProxyAgent("user_proxy")

    excel_mcp_server = StdioServerParams(
        command="uvx", args=["excel-mcp-server", "stdio"]
    )
    async with McpWorkbench(excel_mcp_server) as workbench:  # type: ignore
        analyzer = AssistantAgent(
            name="analyzer",
            model_client=model_client,
            handoffs=["planer"],
            workbench=workbench,
            system_message="""
            你是数据分析专家，负责对数据进行分析。你可以调用工具进行数据分析。
            你需要使用中文回复，大多数情况下不要获取整个文件数据。
            你需要对分析结果进行审查和反馈。判断被分配的任务是否完成，并提供反馈。
            当你在任务完成或需要用户时，使用handoff方法将结果交给planer。
            如果任务未完成，提供详细的反馈信息。
            """,
            model_client_stream=True,
        )

        # analyzer_critic = AssistantAgent(
        #     name="analyzer_critic",
        #     model_client=model_client,
        #     handoffs=["planer"],
        #     system_message="""
        #     你是数据分析专家，负责对数据进行分析。你可以调用工具进行数据分析。
        #     你需要对分析结果进行审查和反馈。判断被分配的任务是否完成，并提供反馈。
        #     如果任务完成，在使用handoff方法将结果交给planer。
        #     如果任务未完成，提供详细的反馈信息。

        #     """,
        #     model_client_stream=True,
        # )

        # analyzer_team = RoundRobinGroupChat(
        #     [analyzer, analyzer_critic],
        #     name="analyzer_team",
        #     max_turns=10,
        # )

        writer = AssistantAgent(
            name="writer",
            model_client=model_client,
            handoffs=["planer"],
            system_message="你是写作专家，负责生成报告。当你在任务完成或需要用户时，使用handoff方法将结果交给planer。",
            model_client_stream=True,
        )

        # 终止条件
        termination_condition = (
            MaxMessageTermination(max_messages=20)
            | TextMentionTermination(text="任务已完成", sources=["planer"])
            | HandoffTermination("user_proxy")
        )
        team = Swarm(
            [planer, analyzer, writer, user_proxy],
            termination_condition=termination_condition,
        )

        while True:
            try:
                task = input("请输入您的任务（输入'quit'退出）: ")
                if task.lower() == "quit":
                    break
                print(f"正在处理任务: {task}")

                await Console(
                    team.run_stream(
                        task=TextMessage(content=task + "/no_think", source="user"),
                    )
                )

                await team.save_state()
            except KeyboardInterrupt:
                print("\n程序已中断")
                return


if __name__ == "__main__":
    asyncio.run(main())
