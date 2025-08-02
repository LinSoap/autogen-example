# StaticWorkbench Agent 示例

**难度等级** 🟢 入门

本示例展示了如何使用 `StaticWorkbench` 将 `tool` 转换为 `Workbench`。

**前置知识**
- FunctionTool
- Workbench

## 运行方式
```bash
uv run -m examples.Workbench.StaticWorkbench.main
```

## 概述
由于普通的 `FunctionTool` 无法和 `Workbench` 一起使用，这样就导致在存在调用 MCP 的系统中，无法通过 `FunctionTool` 向 Agent 传递用户所上传的文件地址，所以本示例展示了如何使用 AutoGen 的 `StaticWorkbench` 将普通的 `tool` 转换为 `Workbench`，从而可以让 Agent 读取到用户所上传的文件地址。

## 系统架构
系统包含两个主要智能体：

### 核心组件
- **file_agent**: 文件处理智能体，可以读取用户上传的文件内容
- **check_agent**: 检查智能体，负责验证 file_agent 是否成功读取到文件内容
- **StaticWorkbench**: 静态工作台，将函数工具转换为工作台格式

### 工具组件
- **get_file_path**: 获取用户上传的文件路径
- **read_file_content**: 读取指定文件路径的内容

## 工作流程
1. **工作台创建**: 使用 `StaticWorkbench` 将函数工具转换为工作台
2. **文件读取**: file_agent 使用工作台工具获取文件路径并读取内容
3. **内容验证**: check_agent 检查是否成功读取到文件内容
4. **终止判断**: 根据验证结果决定是否终止对话

## 核心组件详解

### StaticWorkbench 的作用
`StaticWorkbench` 是 AutoGen 中用于将普通工具转换为工作台的组件，它的作用包括：

1. **工具转换**: 将 `FunctionTool` 转换为 Workbench 格式
2. **MCP 兼容**: 在 MCP（Model Context Protocol）系统中支持文件操作
3. **工具管理**: 统一管理多个工具函数

### 关键参数说明
- **tools**: 需要转换的工具列表，支持多个 `FunctionTool`
- **workbench**: 智能体的工作台配置，提供工具调用能力
- **reflect_on_tool_use**: 是否反思工具使用结果

### 团队协作机制
系统使用 `RoundRobinGroupChat` 实现智能体轮询协作：
- **参与者**: [file_agent, check_agent]
- **终止条件**: 当 check_agent 回复 "APPROACH" 或达到最大消息数时终止

### 执行逻辑
```
用户请求 → file_agent 获取文件路径 → file_agent 读取文件内容 → check_agent 验证结果 → 输出结果
```

- **第一步**: 用户请求读取文件内容
- **第二步**: file_agent 调用 `get_file_path` 获取文件路径
- **第三步**: file_agent 调用 `read_file_content` 读取文件内容
- **第四步**: check_agent 验证是否成功读取到内容
- **第五步**: 根据验证结果输出 "APPROACH" 或 "REJECT"

## 关键特性

- **工具转换**: 将普通函数转换为 Workbench 兼容格式
- **文件操作**: 支持文件路径获取和内容读取
- **MCP 集成**: 兼容 Model Context Protocol 文件处理
- **验证机制**: 双重验证确保文件读取成功
- **团队协作**: 多智能体协作完成文件处理任务

---

本示例为在 MCP 系统中进行文件操作提供了基础模板，解决了普通 `FunctionTool` 与 `Workbench` 不兼容的问题。