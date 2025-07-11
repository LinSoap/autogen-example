# Agent Tool 示例

**难度等级**: 🟡 中级

本示例展示了如何使用 AutoGen 的 `AgentTool` 和多智能体协作，实现自动数据生成与格式校验。适合有一定 AutoGen 基础，希望学习智能体工具集成与团队协作的开发者。

**前置知识**:
- [Assistant Agent 基础](../../agent/hello_world/README.md)
- AgentTool 工具用法
- RoundRobinGroupChat
- 终止条件
- 异步编程

## 运行方式
```bash
uv run -m examples.tool.agent_tool.main
```

系统会自动生成一个 JSON 或 XML 数据，并通过多智能体协作完成格式校验，最终输出校验结果。

## 概述
本示例演示了如何通过多个智能体协作，自动生成数据并判断其格式是否正确。通过 `AgentTool`，可以让一个智能体调用另一个智能体作为工具，提升系统的灵活性和可扩展性。

## 系统架构
系统包含两个主要智能体和两个工具型智能体：

### 核心组件
- **generate_agent**: 数据生成助手，根据用户输入生成 JSON 或 XML 数据（可能正确也可能错误）
- **check_agent**: 格式校验助手，负责判断数据格式是否为干净的 JSON 或 XML
- **json_check_agent**: JSON 校验工具智能体，判断输入是否为干净的 JSON
- **xml_check_agent**: XML 校验工具智能体，判断输入是否为干净的 XML

### 工具集成
- **json_check_agent_tool**: 将 `json_check_agent` 封装为工具，供 `check_agent` 调用
- **xml_check_agent_tool**: 将 `xml_check_agent` 封装为工具，供 `check_agent` 调用

## 工作流程
1. **数据生成**: `generate_agent` 根据任务生成 JSON 或 XML 数据
2. **格式校验**: `check_agent` 自动调用 `json_check_agent_tool` 或 `xml_check_agent_tool` 对生成的数据进行格式校验
3. **结果输出**: 校验结果通过控制台输出

## 核心组件详解

### AgentTool 的作用
`AgentTool` 可以将一个智能体包装为工具，供其他智能体在推理过程中调用，实现智能体间的能力复用和组合。

### check_agent 的工作机制
- `check_agent` 配置了 `reflect_on_tool_use=True`，在判断数据格式时，会自动调用合适的校验工具（JSON 或 XML）
- 工具调用结果作为最终消息返回

### 团队协作逻辑
系统采用 `RoundRobinGroupChat` 轮询机制，确保 `generate_agent` 先生成数据，`check_agent` 再进行校验，最后由 `check_agent` 终止流程。

### 执行逻辑
```
generate_agent → check_agent（自动调用 json/xml 校验工具）→ 输出结果
```

- **第一步**: `generate_agent` 生成数据
- **第二步**: `check_agent` 判断数据类型并调用对应校验工具
- **第三步**: 校验结果输出到终端

这种设计展示了 AutoGen 智能体工具化和团队协作的基本模式，为构建更复杂的多智能体系统提供了范例。