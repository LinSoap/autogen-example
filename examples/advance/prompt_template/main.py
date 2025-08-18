from autogen_agentchat.agents import (
    AssistantAgent,
    CodeExecutorAgent,
    ApprovalRequest,
    ApprovalResponse,
)
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_agentchat.base import TaskResult
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from config.model_config import model_client
from autogen_ext.agents.file_surfer import FileSurfer
import asyncio
import pandas as pd


def simple_approval_func(request: ApprovalRequest) -> ApprovalResponse:
    """Simple approval function that requests user input for code execution approval."""
    print("Code execution approval requested:")
    print("=" * 50)
    print(request.code)
    print("=" * 50)

    while True:
        user_input = input("Do you want to execute this code? (y/n): ").strip().lower()
        if user_input in ["y", "yes"]:
            return ApprovalResponse(approved=True, reason="Approved by user")
        elif user_input in ["n", "no"]:
            return ApprovalResponse(approved=False, reason="Denied by user")
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def get_assistant_agent(data_info: str) -> AssistantAgent:
    code_executor = LocalCommandLineCodeExecutor(work_dir="coding")
    agent = CodeExecutorAgent(
        "code_executor",
        code_executor=code_executor,
        description="一个擅长使用Pandas进行数据分析的编程助手",
        model_client=model_client,
        supported_languages=["python"],
        model_client_stream=True,
        approval_func=simple_approval_func,
        system_message=f"""
            以下是一个Pandas DataFrame的信息摘要：
            <data_info>
            {data_info}
            </data_info>
            你负责接受用户的编程任务请求，并生成相应的代码来完成这些任务。
            在完成任务后，回复`数据分析任务已完成`以结束对话。
            你只能使用pandas库来处理数据和生成Excel文件。
            你只有在执行代码获取到结果才算任务完成，并非仅仅生成代码。
    """,
    )
    return agent


def get_generate_excel_info_agent() -> AssistantAgent:
    agent = AssistantAgent(
        name="excel_info_agent",
        model_client=model_client,
        model_client_stream=True,
        system_message="""
        你是一个Pandas DataFrame Info处理专家，擅长从DataFrame中提取信息并进行分析。
        你会接收到一个Pandas DataFrame的info信息字符串，以及该DataFrame的前几行数据（head）。
        你需要根据DataFrame的Head完善info信息，补全缺失的列名和数据类型，并提供对DataFrame的简要描述。
        你需要根据Head信息完善Info中unnamed列的列名，给出实际含义。
        使用Markdown Table格式输出补全后的Info信息，并在表格下方给出对DataFrame的简要描述。
        你只需回复Markdown Table和描述内容，不要包含其他多余信息。
""",
    )
    return agent


async def assistant_run() -> None:
    import os

    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "1-1.xlsx")

    df = pd.read_excel(excel_path)

    info_agent = get_generate_excel_info_agent()

    async for message in info_agent.run_stream(
        task=TextMessage(
            content=f"""
            请分析以下DataFrame的信息：
            <data_info>{df.info()}</data_info>
            <data_head>{df.head()}</data_head>
            """,
            source="user",
        )
    ):
        if isinstance(message, TaskResult):
            autogen_result = message.model_dump()
            new_data_info = autogen_result["messages"][-1]["content"]
    print(new_data_info)

    file_surfer = FileSurfer(
        "FileSurfer", model_client=model_client, base_path="coding"
    )

    reponse_agent = get_assistant_agent(new_data_info)

    team = MagenticOneGroupChat([file_surfer, reponse_agent], model_client=model_client)
    await Console(
        team.run_stream(
            task=[TextMessage(content="这些数据中，哪些环比增长了？", source="user")]
        ),
        output_stats=True,
    )


asyncio.run(assistant_run())
