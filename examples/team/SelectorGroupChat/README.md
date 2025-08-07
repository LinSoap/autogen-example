# SelectorGroupChat 智能分配示例

**难度等级** 🟢 入门

本章节介绍 SelectorGroupChat 的动态角色分配能力，通过自定义 selector_prompt，实现团队成员自动选择最合适的 agent 发言。

**前置知识**
- AssistantAgent
- SelectorGroupChat
- 终止条件设置

## 运行方式
```bash
uv run -m examples.team.SelectorGroupChat.main
```

## 概述
本示例展示了 SelectorGroupChat 如何根据任务内容自动分配最合适的 agent 响应，实现高效的多智能体协作。

## 系统架构
系统包含三个主要智能体：

### 核心组件
- **analyst**: 数据分析师，只负责数据分析相关任务
- **pm**: 产品经理，只负责产品优化建议相关任务
- **dev**: 开发者，只负责技术实现方案相关任务
- **SelectorGroupChat**: 智能分配团队，自动选择最合适的 agent 发言

### 工具组件
- 无需额外工具，全部为角色分工

## 工作流程
1. 用户输入问题
2. SelectorGroupChat 根据 selector_prompt 自动选择最合适的 agent
3. agent 响应并输出结果
4. 满足终止条件后自动结束

## 核心组件详解

### SelectorGroupChat 的作用
- 根据 selector_prompt 及当前对话内容，自动分配 agent 发言
- 支持自定义分配逻辑和角色描述
- 允许同一 agent 连续发言（allow_repeated_speaker）

### selector_prompt 示例
```
请选择最合适的 agent 来完成当前任务。

可选角色：
{roles}

当前对话内容：
{history}

请根据对话内容，从 {participants} 中选择一位最合适的 agent 进行回复。只能选择一位 agent。
```

## 关键特性
- 智能角色分配：根据任务内容自动选择 agent
- 角色分工明确：每个 agent 只负责自己领域任务
- 终止条件灵活：支持多种终止方式，防止死循环
- 可扩展性强：可自定义角色、分配逻辑和团队规模

---

本示例为多智能体协作和自动分配提供了基础模板，适用于专家团队、自动问答、智能客服等场景。
