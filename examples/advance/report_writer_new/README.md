# Report Writer New 示例

**难度等级**: 🔴 高级+

本示例展示了如何使用 AutoGen 0.7 版本的新特性——团队嵌套功能，构建一个完整的智能写作系统。该系统通过多层团队架构实现了从需求分析到文稿生成的全流程自动化，适合希望深入理解 AutoGen 最新团队嵌套特性和多智能体协作的开发者。

**前置知识**:
- AutoGen 0.7 团队嵌套特性
- [Report Writer 基础版本](../report_writer/README.md)
- RoundRobinGroupChat 和 SelectorGroupChat
- StructuredMessage 与 Pydantic 模型
- 多层团队架构设计
- Agent handoffs 机制

## 运行方式
```bash
uv run -m examples.advance.report_writer_new.main
```

系统会循环接收用户输入，自动完成从需求理解、蓝图生成到文稿撰写的完整流程，支持文稿润色和内容解释功能。

## 概述
本示例是 AutoGen 0.7 版本团队嵌套特性的完整演示，通过将专业团队作为子组件嵌入主团队，实现了更精细的任务分工和更高效的协作流程。系统包含需求分析团队、蓝图生成团队和独立的写作智能体，形成了层次化的智能写作解决方案。

## 🆕 AutoGen 0.7 新特性

### 团队嵌套 (Team-in-Team)
- **嵌套架构**: 支持在 `SelectorGroupChat` 中直接使用 `RoundRobinGroupChat` 作为参与者
- **层次化管理**: 每个子团队专注特定任务，主团队负责整体协调
- **智能路由**: 通过 `selector_func` 实现团队间的智能切换和任务分配


## 系统架构

### 主要组件

#### 子团队 (Sub-Teams)
- **team_insight**: 需求分析团队
  - `word_insight_agent`: 内容理解与意图澄清
  - `word_insight_json_agent`: JSON 格式校验与修复
- **team_blueprint**: 蓝图生成团队
  - `word_blueprint_agent`: 写作蓝图生成
  - `word_blueprint_json_agent`: 蓝图结构校验

#### 独立智能体
- **writer_agent**: 文稿撰写智能体
- **refiner_agent**: 文稿润色智能体
- **explainer_agent**: 内容解释智能体

#### 主团队架构
- **final_team**: `SelectorGroupChat` 主团队，包含所有子团队和独立智能体

### 团队嵌套结构
```
final_team (SelectorGroupChat)
├── team_insight (RoundRobinGroupChat)
│   ├── word_insight_agent
│   └── word_insight_json_agent
├── team_blueprint (RoundRobinGroupChat)
│   ├── word_blueprint_agent
│   └── word_blueprint_json_agent
├── writer_agent
├── refiner_agent
└── explainer_agent
```

## 工作流程

### 多层协作流程
1. **需求分析阶段**: `final_team` 选择 `team_insight` 子团队
   - `word_insight_agent` 分析用户需求，生成结构化分析
   - `word_insight_json_agent` 校验并修复 JSON 格式
2. **蓝图生成阶段**: 选择 `team_blueprint` 子团队
   - `word_blueprint_agent` 基于分析结果生成写作蓝图
   - `word_blueprint_json_agent` 校验蓝图结构
3. **文稿撰写阶段**: 选择 `writer_agent` 生成完整文稿
4. **后续服务**: 根据需求选择 `refiner_agent` 或 `explainer_agent`

### 智能选择逻辑
```python
def selector_func(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    agent_names = set()
    for msg in messages:
        if hasattr(msg, "source") and msg.source:
            agent_names.add(msg.source)

    if "word_insight_json_agent" not in agent_names:
        return "team_insight"
    
    if "word_insight_json_agent" in agent_names and "word_blueprint_json_agent" not in agent_names:
        return "team_blueprint"
    
    if all(agent in agent_names for agent in ["word_insight_json_agent", "word_blueprint_json_agent"]) and "writer_agent" not in agent_names:
        return "writer_agent"
    
    return messages[-1].metadata.get("select_agent")
```

## 核心组件详解

### 团队嵌套机制
- **子团队封装**: 每个 `RoundRobinGroupChat` 作为独立处理单元，内部完成特定任务
- **主团队协调**: `SelectorGroupChat` 负责在子团队间进行选择和调度
- **状态传递**: 通过 `StructuredMessage` 在团队间传递结构化数据

### 结构化数据模型
```python
class WordInsightAnalysis(BaseModel):
    """需求分析结构化模型"""
    existing_information: ExistingInformation
    supplementary_questions: List[SupplementaryQuestion]

class WordBlueprintStructure(BaseModel):
    """蓝图结构化模型"""
    title: str
    sections: List[Section]
    estimated_length: str
```

## 执行逻辑
```
用户输入 → team_insight (需求分析+JSON校验) → team_blueprint (蓝图生成+结构校验) → writer_agent (文稿撰写) → [可选] refiner_agent/explainer_agent
```

- **第一步**: 主团队选择 `team_insight`，子团队内部完成需求分析和JSON校验
- **第二步**: 主团队选择 `team_blueprint`，子团队内部完成蓝图生成和结构校验  
- **第三步**: 主团队选择 `writer_agent` 完成文稿撰写
- **第四步**: 根据用户需求选择润色或解释服务

## 🆕 关键特性

- **团队嵌套**: 首次展示 AutoGen 0.7 团队嵌套特性，实现层次化智能体管理
- **专业分工**: 每个子团队专注特定领域，提高任务处理的专业度和效率
- **智能路由**: 通过状态追踪实现团队间的智能切换和任务分配
- **结构化输出**: 全流程使用 Pydantic 模型，确保数据传递的准确性和一致性
- **异步流式处理**: 支持实时流式输出，提升用户体验
- **多模态支持**: 支持文件上传、MCP 工具调用等多种输入方式
- **容错机制**: 内置 JSON 校验和修复机制，确保系统稳定性

---

本示例为 AutoGen 0.7 版本的团队嵌套特性提供了完整的实践模板，适合构建复杂的多智能体协作系统和企业级AI应用。