# Team Tool JSON 生成示例

本示例展示了如何使用 AutoGen 的 `TeamTool` 功能，构建一个能够确保生成标准 JSON 格式的智能代理团队。

## 功能概述

该工具通过组合多个 Agent 形成一个团队，专门用于分析用户输入并生成符合特定数据模型的 JSON 结果。主要包含：

1. **内容理解 Agent**：分析用户需求，提取关键信息
2. **JSON 验证 Agent**：确保输出符合指定的数据结构
3. **引导 Agent**：作为用户接口，调用团队工具

## 核心组件

### 1. 数据模型定义

使用 Pydantic 定义严格的数据结构：

```python
class WordInsightAnalysis(BaseModel):
    """insight_agent 的结构化分析模型"""
    
    class ExistingInformation(BaseModel):
        """已有信息确认"""
        document_type: str  # 文档类型
        target_audience: str  # 目标受众
        writing_purpose: str  # 写作目的
        style_requirement: str  # 风格要求
        key_content: List[str]  # 用户提供的关键内容要点
    
    class SupplementaryQuestion(BaseModel):
        """补充信息问题"""
        question: str  # 提出的具体问题
        options: List[str]  # 问题选项
        reason: str  # 需要此信息的原因
        type: Literal["open", "single_choice", "multiple_choice"]
    
    existing_information: ExistingInformation
    supplementary_questions: List[SupplementaryQuestion]
```

### 2. Agent 团队构建

#### 内容理解 Agent (`insight_agent`)
- 负责分析用户输入，提取关键信息
- 主动追问不明确的细节
- 生成初步的分析结果

#### JSON 验证 Agent (`json_agent`)
- 专门负责 JSON 格式验证和修正
- 使用 `output_content_type=WordInsightAnalysis` 确保结构化输出
- 解决常见的 JSON 格式错误

### 3. 团队工具创建

```python
# 创建团队
insight_inner_team = RoundRobinGroupChat(
    [insight_agent, json_agent],
    termination_condition=SourceMatchTermination(sources=["json_agent"]),
    custom_message_types=[StructuredMessage[WordInsightAnalysis]],
)

# 封装为工具
tool = TeamTool(
    team=insight_inner_team,
    name="create_insight_json",
    description="这个Team用于生成需求JSON",
    return_value_as_last_message=True,
)
```

## JSON 格式保证机制

### 1. 双重验证机制
- **第一层**：`insight_agent` 按照指定模型生成内容
- **第二层**：`json_agent` 专门验证和修正 JSON 格式

### 2. 结构化输出
- 使用 `output_content_type=WordInsightAnalysis` 强制结构化输出
- Pydantic 模型自动验证数据类型和结构

### 3. 终止条件控制
- 使用 `SourceMatchTermination(sources=["json_agent"])` 确保最终输出来自 JSON 验证 Agent
- 保证最后的消息是经过验证的 JSON 格式

## 使用示例

### 基本用法

```python
# 创建引导 Agent
agent = AssistantAgent(
    name="guide_agent",
    model_client=model_client,
    tools=[tool],  # 使用团队工具
    system_message="请直接调用create_insight_json工具来生成JSON结果。"
)

# 运行示例
async def assistant_run():
    await Console(
        agent.on_messages_stream(
            [TextMessage(content="帮我生成一篇300字的麦当劳实习生周报", source="user")],
            cancellation_token=CancellationToken(),
        ),
        output_stats=True,
    )

asyncio.run(assistant_run())
```

### 预期输出格式

```json
{
  "existing_information": {
    "document_type": "实习生周报",
    "target_audience": "实习生导师",
    "writing_purpose": "汇报工作",
    "style_requirement": "简洁明了",
    "key_content": ["本周工作内容", "学习收获", "遇到的问题"]
  },
  "supplementary_questions": [
    {
      "question": "实习的具体岗位和工作内容是什么？",
      "options": [],
      "reason": "明确岗位职责以确保周报内容准确。",
      "type": "open"
    },
    {
      "question": "周报的主要风格偏好？",
      "options": ["正式商务", "轻松友好", "数据导向", "其他"],
      "reason": "确定写作风格以匹配企业文化。",
      "type": "single_choice"
    }
  ]
}
```

## 关键特性

- **可靠的 JSON 输出**：双重验证机制确保格式正确
- **智能内容分析**：深度理解用户需求，主动补充缺失信息
- **结构化数据**：严格遵循 Pydantic 数据模型
- **流式处理**：支持实时输出，提升用户体验
- **团队协作**：多个 Agent 专业分工，提高结果质量

## 配置要求

确保项目中包含以下依赖：

```toml
[project]
dependencies = [
    "autogen-agentchat>=0.6.4",
    "autogen-ext[openai]>=0.6.4",
    "pydantic",
]
```

并正确配置模型客户端（参考 [`config.model_config`](../../../config/model_config.py)）。