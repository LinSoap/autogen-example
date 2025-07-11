from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.tools import AgentTool
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from pydantic import BaseModel
from config.model_config import model_client
import asyncio


json_check_agent = AssistantAgent(
    name="json_check_agent",
    model_client=model_client,
    model_client_stream=True,
    description="这是一个JSON结果检验工具，会判断这是否是一个干净的JSON结果",
    system_message="""
    你是一个JSON结果检验工具，你会根据输入的JSON数据做检验，如果是一个干净的JSON结果，则返回True，否则返回False。
    """,
)
json_check_agent_tool = AgentTool(
    agent=json_check_agent, return_value_as_last_message=True
)

xml_check_agent = AssistantAgent(
    name="xml_check_agent",
    model_client=model_client,
    model_client_stream=True,
    description="这是一个XML结果检验工具，会判断这是否是一个干净的XML结果",
    system_message="""
    你是一个XML结果检验工具，你会根据输入的XML数据做检验，如果是一个干净的XML结果，则返回True，否则返回False。
    """,
)

xml_check_agent_tool = AgentTool(
    agent=xml_check_agent, return_value_as_last_message=True
)

check_agent = AssistantAgent(
    name="check_agent",
    model_client=model_client,
    model_client_stream=True,
    reflect_on_tool_use=True,
    tools=[json_check_agent_tool, xml_check_agent_tool],
    description="这是一个错误格式检验工具，会根据输入的内容判断是否是一个干净的JSON或XML结果",
    system_message="""
    你必须调用json_check_agent或xml_check_agent来检验输入的内容是否是一个干净的JSON或XML结果。
    """,
)

generate_agent = AssistantAgent(
    name="generate_agent",
    model_client=model_client,
    model_client_stream=True,
    system_message="""
    你是一个数据生成工具,你会根据用户的输入生成一个JSON或XML结果。
    这个JSON或是XML可能是正确的，也可能是错误的。
    """,
)

team = RoundRobinGroupChat(
    participants=[generate_agent, check_agent],
    termination_condition=SourceMatchTermination(["check_agent"]),
)


async def assistant_run() -> None:
    await Console(
        team.run_stream(task="帮我生成一个JSON结果"),
        output_stats=True,
    )


asyncio.run(assistant_run())
