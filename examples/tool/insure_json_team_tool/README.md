# Team Tool JSON 生成示例

**难度等级**: 🟡 中级

本示例展示了如何使用 AutoGen 的 `TeamTool` 功能，构建一个能够确保生成标准 JSON 格式的智能代理团队。适合有一定 AutoGen 基础，希望学习多智能体协作与结构化输出的开发者。

**前置知识**:
- 模型配置
- Assistant Agent 基础
- RoundRobinGroupChat
- 终止条件
- 工具调用

## 运行方式
```bash
uv run -m examples.tool.insure_json_team_tool.main
```

系统会自动分析用户输入，调用团队工具，最终输出符合要求的 JSON 结构化结果。

## 概述
本示例展示了如何通过多智能体协作，自动完成从需求理解到结构化 JSON 输出的完整流程。通过双重验证机制，确保输出的 JSON 严格符合预设的数据模型。

## 系统架构
系统包含两个主要智能体：

- **insight_agent**：内容理解助手，负责分析用户输入、提取关键信息并主动追问细节
- **json_agent**：JSON 验证助手，专门负责验证和修正输出的 JSON 格式

二者通过团队工具（TeamTool）组合，形成一个结构化输出的智能体团队。

## 工作流程
1. **需求分析**：insight_agent 分析用户输入，生成初步结构化内容
2. **格式验证**：json_agent 验证并修正 JSON 格式，确保符合数据模型
3. **结构化输出**：最终输出严格符合 Pydantic 模型的 JSON 结果

## 核心组件详解

### 数据模型定义
使用 Pydantic 定义严格的数据结构，确保输出内容的规范性和一致性。

### 团队工具的作用
`TeamTool` 封装了一个内部团队，自动协调 insight_agent 和 json_agent 的协作，保证输出的 JSON 既有内容深度又符合格式要求。

### 终止条件
通过 `SourceMatchTermination(sources=["json_agent"])` 控制流程，确保最终输出来自 json_agent，保证格式正确。

## 执行逻辑
```
insight_agent → json_agent
```
- **第一步**：insight_agent 负责内容理解与结构化
- **第二步**：json_agent 验证并修正 JSON 格式
- **终止**：输出最终结构化 JSON

## 关键特性

- **可靠的 JSON 输出**：双重验证机制确保格式正确
- **智能内容分析**：深度理解用户需求，主动补充缺失信息
- **结构化数据**：严格遵循 Pydantic 数据模型
- **团队协作**：多个 Agent 专业分工，提高结果质量

