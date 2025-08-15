# 项目 Roadmap

本项目包含多个 AutoGen 示例，涵盖从入门到进阶的多智能体协作、工具

## 目录结构与文档列表

### Agent 相关示例
- [Hello World Agent 示例](./examples/agent/hello_world/README.md)  
    🟢 入门级，展示 AssistantAgent 的基本用法。

- [Society of Mind Agent 示例](./examples/agent/society_of_mind_agent/README.md)  
    🟡 中级，展示多智能体团队协作与流程控制。

- [Custom Agent 示例](./examples/agent/custom_agent/README.md)  
    🔴 高级，演示如何实现自动调用工具（如函数）的自定义智能体 ToolCallAgent，适合希望学习工具集成与高级智能体扩展的开发者。

- [CodeExecutorAgent 代码执行示例](./examples/agent/code_executor_agent/README.md)  
    🟢 入门级，展示如何使用 CodeExecutorAgent 在 Docker 容器中安全执行代码，实现自动化数据分析任务。

### Tool 相关示例
- [Agent Tool 示例](./examples/tool/agent_tool/README.md)  
    🟡 中级，展示 AgentTool 工具集成与多智能体数据校验。

- [Team Tool JSON 生成示例](./examples/tool/insure_json_team_tool/README.md)  
    🟡 中级，展示如何通过团队协作确保标准 JSON 输出，适合结构化数据场景。

### 进阶/高级示例
- [Custom Tool Call Agent 示例](./examples/advance/custom_tool_call_agent/README.md)  
    🔴 高级+，演示如何实现自动调用多智能体团队工具、结构化输出校验的自定义 ToolCallAgent，适合深入理解多工具、多团队协作与结构化数据输出的开发者。

- [Report Writer New 示例](./examples/advance/report_writer_new/README.md)  
    🔴 高级+，展示 AutoGen 0.7 版本团队嵌套特性的完整演示，通过多层团队架构实现智能写作系统，适合希望深入理解团队嵌套机制和层次化智能体管理的开发者。

### Team 团队协作示例
- [SelectorGroupChat 团队智能分配示例](./examples/team/SelectorGroupChat/README.md)  
    🟢 初级，展示 SelectorGroupChat 智能分配机制，自动选择最合适的 Agent 处理任务，适合多领域专家团队协作。
- [RoundRobinGroupChat 轮询团队协作示例](./examples/team/RoundRobinGroupChat/README.md)  
    🟢 初级，展示团队成员轮流发言、反思与协作，适合主-Agent+评论-Agent 场景。

