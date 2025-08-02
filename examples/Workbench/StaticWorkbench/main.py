from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_core.tools import FunctionTool, StaticWorkbench
from autogen_agentchat.ui import Console
from config.model_config import model_client
from typing import List
import asyncio


def get_file_path() -> List[str]:
    """
    返回值为用户上传的文件路径
    """
    return ["./examples/Workbench/StaticWorkbench/file/test.txt"]


def read_file_content(file_path: str) -> str:
    """
    传入file_path，可以返回文件内容
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


workbench = StaticWorkbench(
    tools=[
        FunctionTool(get_file_path, description="获取用户上传的文件路径"),
        FunctionTool(read_file_content, description="读取指定文件路径的内容"),
    ]
)


file_agent = AssistantAgent(
    name="agent",
    model_client=model_client,
    workbench=workbench,
    model_client_stream=True,
    reflect_on_tool_use=False,
    system_message="""
        你是一个可以读取用户当前对话所上传文件的Agent。

        🤖【MCP 工具】：
        get_file_path
        read_file_content
        """,
)


check_agent = AssistantAgent(
    name="check_agent",
    model_client=model_client,
    system_message="""
        你是一个检查Agent，负责根据file_agent输出的内容，来判断file_agent是否读到了文件内容。
        如果成功读取到文件内容，请回复 APPROACH
        如果没有成功读取到文件内容，请回复 REJECT
        """,
)


text_mention_termination = TextMentionTermination(text="APPROACH")

max_message_termination = MaxMessageTermination(
    max_messages=20,
)

team = RoundRobinGroupChat(
    participants=[file_agent, check_agent],
    termination_condition=text_mention_termination | max_message_termination,
)


async def assistant_run() -> None:
    await Console(
        team.run_stream(
            task="请告诉我这个文件中的内容",
        ),
        output_stats=True,
    )


asyncio.run(assistant_run())
