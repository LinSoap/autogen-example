from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination, ExternalTermination
from autogen_agentchat.ui import Console
from config.model_config import model_client
import asyncio

async def main():
    analyst = AssistantAgent(
        "analyst",
        model_client=model_client,
        system_message="你是数据分析师，只负责数据分析相关任务。遇到非分析任务请回复：非我职责。分析完成后请回复：分析已完成。遇到异常请回复：分析失败。",
        model_client_stream=True
    )
    pm = AssistantAgent(
        "pm",
        model_client=model_client,
        system_message="你是产品经理，只负责产品优化建议相关任务。遇到非产品建议任务请回复：非我职责。建议完成后请回复：建议已完成。遇到异常请回复：建议失败。",
        model_client_stream=True
    )
    dev = AssistantAgent(
        "dev",
        model_client=model_client,
        system_message="你是开发者，只负责技术实现方案相关任务。遇到非技术方案任务请回复：非我职责。方案完成后请回复：方案已完成。遇到异常请回复：方案失败。",
        model_client_stream=True
    )
    termination_condition = (
        TextMentionTermination("建议已完成。") |
        TextMentionTermination("分析已完成。") |
        TextMentionTermination("方案已完成。") |
        TextMentionTermination("分析失败。") |
        TextMentionTermination("建议失败。") |
        TextMentionTermination("方案失败。") |
        MaxMessageTermination(max_messages=15) |
        ExternalTermination()
    )
    selector_prompt = """请选择最合适的 agent 来完成当前任务。

可选角色：
{roles}

当前对话内容：
{history}

请根据对话内容，从 {participants} 中选择一位最合适的 agent 进行回复。只能选择一位 agent。
"""
    team = SelectorGroupChat(
        [analyst, pm, dev],
        model_client=model_client,
        termination_condition=termination_condition,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True,
    )
    # 随机三个问题，分别只触发一个 agent
    tasks = [
        "请分析最近的用户活跃数据。",  # 只分析师
        "请给出产品的优化建议。",      # 只产品经理
        "请设计一个用户分群的技术实现方案。"  # 只开发者
    ]
    for task in tasks:
        print(f"\n--- 问题: {task} ---")
        await Console(team.run_stream(task=task), output_stats=True)

if __name__ == "__main__":
    asyncio.run(main())
