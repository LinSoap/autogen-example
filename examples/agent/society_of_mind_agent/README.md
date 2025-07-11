# Society of Mind Agent 示例

**难度等级**: 🟡 中级

本示例展示了如何使用 AutoGen 的 `SocietyOfMindAgent` 构建复杂的多智能体协作系统。适合有一定 AutoGen 基础，希望学习高级智能体编排和流程控制的开发者。

**前置知识**:
- 模型配置
- Assistant Agent
- SelectorGroupChat
- 终止条件
- 智能体团队协作
- 自定义选择函数


## 运行方式
```bash
uv run -m examples.agent.society_of_mind_agent.main
```

系统会循环接收用户输入，自动按照智能体顺序执行任务，最终提供完整的写作服务。

## 概述
本示例展示了如何使用 AutoGen 的 `SocietyOfMindAgent` 来构建一个智能写作助手系统。该系统能够自动完成从需求分析到内容生成的完整写作流程。

## 系统架构
系统包含两个层次的智能体团队：

### 主要智能体团队
- **insight_agent**: 需求收集助手，提取关键信息并提出补充问题
- **outline_agent**: 大纲生成助手，根据需求生成详细的写作大纲
- **genearte_agent**: 内容生成助手，根据大纲生成完整文章
- **society_of_ming_agent**: 报告助手，负责后续的修改和问答

### 内部智能体团队（Society of Mind）
- **query_agent**: 查询助手，解答用户问题
- **modify_agent**: 修改助手，根据反馈优化内容

## Society of Mind 的作用
`SocietyOfMindAgent` 封装了一个内部团队（`inner_team`），包含查询和修改两个智能体。它的作用是：

1. **智能路由**: 根据用户意图自动选择合适的内部智能体
2. **功能整合**: 将多个专业智能体整合为一个统一的接口
3. **流程简化**: 外部只需与一个智能体交互，内部自动处理复杂的任务分配

## 工作流程
1. **需求分析**: insight_agent 收集用户需求
2. **大纲生成**: outline_agent 创建写作大纲
3. **内容生成**: genearte_agent 生成完整文章
4. **后续服务**: society_of_ming_agent 处理修改和问答请求



## 核心组件详解

### selector_func 的作用
`selector_func` 是一个自定义的智能体选择函数，负责控制主要智能体团队的执行顺序。它的作用包括：

1. **状态追踪**: 通过分析对话历史，追踪哪些智能体已经完成了任务
2. **流程控制**: 确保智能体按照预定的顺序执行任务
3. **智能路由**: 根据当前状态智能选择下一个应该执行的智能体

### 执行逻辑
```
insight_agent → outline_agent → genearte_agent → society_of_ming_agent
```

- **第一步**: 如果没有任何智能体发言，启动 `insight_agent` 进行需求收集
- **第二步**: 当 `insight_agent` 完成后，启动 `outline_agent` 生成大纲
- **第三步**: 当前两个智能体都完成后，启动 `genearte_agent` 生成内容
- **第四步**: 当前三个智能体都完成后，启动 `society_of_ming_agent` 提供后续服务

这种设计确保了写作流程的有序性和完整性，每个智能体都在合适的时机被调用，避免了混乱的对话流