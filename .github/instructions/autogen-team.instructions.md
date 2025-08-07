---
applyTo: "**/*.py"
---

1. RoundRobinGroupChat
   擅长功能：

适合需要多角色反思、批评、协作的场景
所有 Agent 共享上下文，轮流发言
保证团队信息一致性，适合主-Agent+评论-Agent 模式
使用案例：
主-Agent 负责任务执行，评论-Agent 负责反馈和审核，直到评论-Agent 回复“APPROVE”为止。

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from config.model_config import model_client

primary_agent = AssistantAgent("primary", model_client=model_client)
critic_agent = AssistantAgent("critic", model_client=model_client)
termination = TextMentionTermination("APPROVE")
team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=termination)
result = await team.run(task="写一首关于秋天的诗。")
print(result)

2. SelectorGroupChat
   擅长功能：

动态角色分配
适合专家团队，自动选择最合适的 Agent 发言
提高协作效率，适合多领域知识融合
使用案例：

```

selector_prompt = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""

team = SelectorGroupChat(
    [planning_agent, web_search_agent, data_analyst_agent],
    model_client=model_client,
    termination_condition=termination,
    selector_prompt=selector_prompt,
    allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
)
```

3. MagenticOneGroupChat
   擅长功能：

通用型多智能体系统
支持跨领域任务分解、复杂推理
适合网页、文件分析等开放任务
使用案例：
团队成员分别负责网页抓取、内容分析、报告撰写，协作完成复杂信息处理任务。

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")
crawler = AssistantAgent("crawler", model_client=model_client)
analyzer = AssistantAgent("analyzer", model_client=model_client)
writer = AssistantAgent("writer", model_client=model_client)
team = MagenticOneGroupChat([crawler, analyzer, writer])
result = await team.run(task="抓取某网站内容并生成分析报告。")
print(result)

4. Swarm
   擅长功能：

流程化、分阶段协作
通过 HandoffMessage 实现任务交接
适合流水线式任务处理，如数据清洗、建模、评估
使用案例：
数据清洗 Agent 处理原始数据，建模 Agent 进行模型训练，评估 Agent 完成模型评估，任务逐步交接。

如需进一步扩展或定制团队协作模式，可根据实际需求调整 Agent 角色、终止条件和工具集。

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")
cleaner = AssistantAgent("cleaner", model_client=model_client)
modeler = AssistantAgent("modeler", model_client=model_client)
evaluator = AssistantAgent("evaluator", model_client=model_client)
team = Swarm([cleaner, modeler, evaluator])
result = await team.run(task="对原始数据进行清洗、建模并评估模型效果。")
print(result)

每个 Team 都可以使用以下三种方式运行和输出内容

1. 无流式打印输出

```
result = await team.run(task="Write a short poem about the fall season.")
print(result)
```

2. 流式打印输出

```
async for message in team.run_stream(task="Write a short poem about the fall season."):  # type: ignore
    if isinstance(message, TaskResult):
        print("Stop Reason:", message.stop_reason)
    else:
        print(message)
```

3. 控制台流式输出(最优先使用方式)

```
await Console(team.run_stream(task="Write a short poem about the fall season."))  # Stream the messages to the console.
```
