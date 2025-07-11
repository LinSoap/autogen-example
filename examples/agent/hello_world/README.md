# Hello World Agent 示例

**难度等级**: 🟢 入门

本示例展示了如何使用 AutoGen 创建最基本的智能体并进行简单对话。适合AutoGen初学者，学习智能体的基本创建和使用方法。

**前置知识**:
- 模型配置
- Assistant Agent 基础
- 异步编程概念

## 运行方式
```bash
uv run -m examples.agent.hello_world.main
```

系统会创建一个智能助手并询问其能力，展示最基本的智能体交互。

## 概述
本示例展示了如何使用 AutoGen 的 `AssistantAgent` 创建一个简单的智能助手。这是学习 AutoGen 的第一步，演示了智能体的基本创建、配置和交互流程。

## 系统架构
系统包含单个智能体：

### 核心组件
- **assistant_agent**: 智能助手，负责回答用户问题

## 工作流程
1. **智能体创建**: 使用 `AssistantAgent` 创建智能助手
2. **消息发送**: 向智能体发送文本消息
3. **流式响应**: 智能体以流式方式返回回答
4. **控制台输出**: 使用 `Console` 在终端显示对话过程

## 核心组件详解

### AssistantAgent 的作用
`AssistantAgent` 是 AutoGen 中最基础的智能体类型，它的作用包括：

1. **消息处理**: 接收和处理文本消息
2. **模型调用**: 与配置的大语言模型进行交互
3. **响应生成**: 根据系统消息和用户输入生成回答

### 关键参数说明
- **name**: 智能体名称，用于识别和日志记录
- **model_client**: 模型客户端，定义使用的大语言模型
- **system_message**: 系统消息，定义智能体的角色和行为
- **model_client_stream**: 启用流式响应，提供更好的用户体验

### 执行逻辑
```
创建智能体 → 发送消息 → 流式响应 → 控制台输出
```

- **第一步**: 创建配置好的 `AssistantAgent` 实例
- **第二步**: 使用 `TextMessage` 创建用户消息
- **第三步**: 调用 `on_messages_stream` 方法处理消息
- **第四步**: 通过 `Console` 在终端显示对话过程和统计信息

这种设计展示了 AutoGen 智能体的基本工作原理，为后续学习更复杂的多智能体系统打下基础。