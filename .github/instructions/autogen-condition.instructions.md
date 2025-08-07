---
applyTo: "**/*.py"
---

    # 防止错误类终止条件
    MaxMessageTermination：在产生指定数量的消息后终止，包括代理和任务消息，防止消息泛滥或死循环。
    TokenUsageTermination：当使用了指定数量的提示或完成 token 时终止，防止资源消耗过多。
    TimeoutTermination：在指定秒数后终止，防止任务长时间无响应。
    ExternalTermination：支持从外部程序控制终止，适用于 UI 集成（如聊天界面的“停止”按钮），防止用户无法中断任务。
    StopMessageTermination：当代理产生 StopMessage 时终止，防止异常流程继续。
    FunctionalTermination：当自定义函数表达式在最新消息序列上返回 True 时终止，可用于防止特定错误场景。

    # 任务成功类终止条件
    TextMentionTermination：当消息中提及特定文本或字符串（如“TERMINATE”或“任务完成”）时终止，表示任务已完成。
    HandoffTermination：当请求交接到特定目标时终止，适用于任务流程交接或完成。
    SourceMatchTermination：在特定代理回复后终止，表示任务由指定角色完成。
    TextMessageTermination：当代理产生 TextMessage 时终止，通常用于检测任务完成的回复。
    FunctionCallTermination：当代理产生包含指定名称 FunctionExecutionResult 的 ToolCallExecutionEvent 时终止，表示指定函数已成功调用。

# 1. 按消息数量终止

max_msg_term = MaxMessageTermination(max_messages=10)

# 2. 检测指定文本出现即终止

text_mention_term = TextMentionTermination(text="任务完成", source="assistant")

# 3. 收到 StopMessage 时终止

stop_msg_term = StopMessageTermination()

# 4. 按 token 使用量终止

token_usage_term = TokenUsageTermination(max_total_tokens=1000)

# 5. 收到指定目标的 HandoffMessage 时终止

handoff_term = HandoffTermination(target="reviewer")

# 6. 按时间终止

timeout_term = TimeoutTermination(timeout_seconds=60)

# 7. 由外部调用 set() 方法主动终止

external_term = ExternalTermination()

# 终止时调用 external_term.set()

# 8. 指定 Agent 回复后终止

source_match_term = SourceMatchTermination(source="user")

# 9. 收到 TextMessage 时终止

text_msg_term = TextMessageTermination(source="assistant")

# 10. 指定函数调用结果出现时终止

func_call_term = FunctionCallTermination(function_name="submit_report")

# 11. 支持自定义函数表达式

def custom_condition(messages):
return any("error" in m.content for m in messages)

functional_term = FunctionalTermination(condition_fn=custom_condition)

以上所有的终止条件都是 bool 类型，可以通过 bool 表达式组合使用。
例如

```
max_msg_termination = MaxMessageTermination(max_messages=10)
text_termination = TextMentionTermination("APPROVE")
combined_termination = max_msg_termination | text_termination

round_robin_team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=combined_termination)

# Use asyncio.run(...) if you are running this script as a standalone script.
await Console(round_robin_team.run_stream(task="Write a unique, Haiku about the weather in Paris"))
```

或者是

```
combined_termination = max_msg_termination & text_termination
```

在使用终止条件时，既要设置任务成功类终止条件，也要设置防止错误类终止条件，以确保任务在预期的情况下完成或终止。
