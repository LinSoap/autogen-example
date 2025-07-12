# Custom Tool Call Agent 示例

**难度等级**: 🔴 高级+

本示例演示如何实现一个能够自动调用多智能体团队工具、并实现结构化输出校验的自定义智能体 `ToolCallAgent`。适合希望深入理解 AutoGen 智能体与多工具、多团队协作集成的开发者。

**前置知识**:
- [自定义Agent](../../agent/custom_agent/README.md)
- Python 类与继承
- BaseChatAgent 智能体基础
- 工具（Tool）与 TeamTool 机制
- 多智能体团队编排
- Pydantic 结构化模型
- 异步编程

## 运行方式
```bash
uv run -m examples.advance.custom_tool_call_agent.tool_call_agent
```

系统会自动调用内部团队工具，生成结构化 JSON 输出，并由校验智能体进行格式校验。

## 概述
本示例通过自定义 `ToolCallAgent`，集成了多智能体团队（如需求分析、JSON 校验等），实现了自动调用团队工具、结构化数据输出与校验的完整流程。用户输入任务后，系统自动完成需求分析、结构化输出、格式校验等步骤。

## 系统架构

### 主要组件
- **ToolCallAgent**: 自定义智能体，自动调用团队工具并返回结构化结果
- **insight_agent**: 内容理解与需求分析智能体
- **json_agent**: 结构化 JSON 检查与修正智能体
- **insight_inner_team**: 由 insight_agent 和 json_agent 组成的团队，负责需求分析和结构化输出
- **insight_inner_team_tool**: 将团队封装为工具，供 ToolCallAgent 调用
- **check_json_agent**: JSON 格式校验智能体
- **team**: 由 ToolCallAgent 和 check_json_agent 组成的团队，实现完整的结构化输出与校验流程

### 工作流程
1. **用户输入任务**: 例如“帮我生成一篇300字的麦当劳实习生周报”
2. **ToolCallAgent 自动调用团队工具**: 调用 insight_inner_team_tool，完成需求分析与结构化输出
3. **结构化输出校验**: check_json_agent 检查 JSON 格式正确性
4. **输出最终结构化结果**: 输出干净、合规的结构化 JSON

## 组件详解

### ToolCallAgent 的作用
- 继承自 `BaseChatAgent`
- 支持注册多个工具（包括团队工具 TeamTool）
- 自动将用户输入作为参数传递给第一个工具，并异步获取结构化结果
- 工具名称需唯一，避免冲突
- 支持流式输出与上下文记忆

### insight_inner_team 及 TeamTool 封装
- 由 insight_agent（内容理解）和 json_agent（结构化校验）组成
- 通过 TeamTool 封装为单一工具，便于 ToolCallAgent 调用
- 输出严格遵循 `WordInsightAnalysis` Pydantic 结构化模型

### 校验与多轮协作
- check_json_agent 对结构化输出进行格式和内容校验，确保最终输出合规
- 支持多轮流式输出与团队协作

### 执行逻辑
```
用户输入 → ToolCallAgent 自动调用团队工具 → 结构化输出 → 校验 → 输出最终结果
```

- **第一步**: 用户输入任务描述
- **第二步**: ToolCallAgent 自动调用 insight_inner_team_tool，完成需求分析与结构化输出
- **第三步**: check_json_agent 校验 JSON 格式
- **第四步**: 输出最终结构化 JSON

## 关键特性

- **多团队协作**: 支持多智能体团队协作与工具封装
- **结构化输出**: 严格遵循 Pydantic 模型，适合前端解析与后续处理
- **自动工具调用**: 智能体自动调用团队工具，无需手动干预
- **异步与流式执行**: 支持异步与流式消息处理
- **类型安全与校验**: 多层校验，确保输出合规

---

本示例为复杂多智能体团队与工具集成、结构化数据输出与校验提供了完整模板，适合扩展为更复杂的业务流程与多工具协作