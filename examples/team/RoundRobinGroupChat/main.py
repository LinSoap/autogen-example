from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination, TimeoutTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from config.model_config import model_client
import asyncio

async def main():
    primary_agent = AssistantAgent(
        "primary",
        model_client=model_client,
        system_message="你是一个擅长模仿 yoda 说话风格的 AI。每次回复都要像 yoda 一样说话。",
        model_client_stream=True
    )
    critic_agent = AssistantAgent(
        "critic",
        model_client=model_client,
        system_message="你是一个严格的评论员，只要主-Agent回复是 yoda 风格且内容合理，就回复 'APPROVE'，否则请指出问题。",
        model_client_stream=True
    )
    # 组合终止条件：任务完成、消息数限制、超时
    termination = (
        TextMentionTermination("APPROVE") |
        MaxMessageTermination(8) |
        TimeoutTermination(60)
    )
    team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=termination)
    await Console(team.run_stream(task="请用 yoda 风格说一句关于学习的名言。"), output_stats=True)

if __name__ == "__main__":
    asyncio.run(main())
