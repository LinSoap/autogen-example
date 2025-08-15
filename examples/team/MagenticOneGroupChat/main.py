import asyncio
from autogen_agentchat.agents import (
    CodeExecutorAgent,
    ApprovalRequest,
    ApprovalResponse,
)
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_agentchat.ui import Console
from autogen_ext.agents.file_surfer import FileSurfer
from config.model_config import model_client


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


async def main() -> None:
    code_executor = LocalCommandLineCodeExecutor(work_dir="coding")

    file_surfer = FileSurfer(
        "FileSurfer", model_client=model_client, base_path="coding"
    )

    code_executor_agent = CodeExecutorAgent(
        "code_executor",
        code_executor=code_executor,
        model_client=model_client,
        supported_languages=["python"],
        model_client_stream=True,
        approval_func=simple_approval_func,
        system_message="""
            你负责接受用户的编程任务请求，并生成相应的代码来完成这些任务。
            在完成任务后，回复`数据分析任务已完成`以结束对话。
            你只能使用pandas库来处理数据和生成Excel文件。
            你只有在执行代码获取到结果才算任务完成，并非仅仅生成代码。
    """,
    )

    team = MagenticOneGroupChat(
        [file_surfer, code_executor_agent], model_client=model_client
    )

    await Console(team.run_stream(task="帮我分析excel2.xlsx文件，生成一个数据分析报告"))

    await model_client.close()
    await code_executor.stop()


asyncio.run(main())
