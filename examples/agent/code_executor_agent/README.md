# CodeExecutorAgent 代码执行示例

**难度等级** 🟢 入门

本示例展示了如何使用 `CodeExecutorAgent` 在 Docker 容器中安全执行代码，实现自动化数据分析任务。

**前置知识**
- CodeExecutorAgent
- DockerCommandLineCodeExecutor
- 用户审批机制

## 运行方式
```bash
uv run -m examples.agent.code_executor_agent.main
```

## 概述
`CodeExecutorAgent` 是 AutoGen 中专门用于代码执行的智能体，它能够根据用户需求生成 Python 代码并在安全的 Docker 容器环境中执行。本示例展示了如何设置代码执行环境、实现用户审批机制，以及如何完成数据分析任务。

## 系统架构
系统包含一个主要智能体：

### 核心组件
- **code_executor_agent**: 代码执行智能体，负责生成和执行 Python 代码
- **DockerCommandLineCodeExecutor**: Docker 代码执行器，提供安全的代码执行环境
- **simple_approval_func**: 用户审批函数，控制代码执行权限

### 工具组件
- **Docker 容器**: 使用 `felixlohmeier/pandas:1.3.3` 镜像提供 pandas 环境
- **文件系统**: 工作目录设置为 `coding`，用于文件读写

## 工作流程
1. **环境初始化**: 启动 Docker 容器并配置工作环境
2. **代码生成**: Agent 根据任务需求生成 Python 代码
3. **用户审批**: 展示代码内容，等待用户确认是否执行
4. **代码执行**: 在 Docker 容器中安全执行已审批的代码
5. **结果输出**: 返回执行结果并生成分析报告
6. **任务完成**: Agent 回复 "数据分析任务已完成" 结束对话

## 核心组件详解

### CodeExecutorAgent 配置
```python
code_executor_agent = CodeExecutorAgent(
    "code_executor",
    code_executor=code_executor,           # Docker 执行器
    model_client=model_client,             # 模型客户端
    supported_languages=["python"],        # 支持的编程语言
    model_client_stream=True,              # 启用流式输出
    approval_func=simple_approval_func,    # 用户审批函数
    system_message="...",                  # 系统提示消息
)
```

### Docker 执行环境
- **镜像**: `felixlohmeier/pandas:1.3.3` - 预装 pandas 库的 Python 环境
- **工作目录**: `coding` - 代码执行和文件操作的工作空间
- **安全性**: 容器化执行，隔离主机环境

### 用户审批机制
审批函数会：
1. 显示即将执行的代码内容
2. 等待用户输入 y/n 确认
3. 返回 ApprovalResponse 对象控制执行权限

### 终止条件组合
```python
termination_condition = (
    TextMentionTermination("数据分析任务已完成") |  # 任务完成信号
    MaxMessageTermination(15) |                    # 最大消息数限制
    TimeoutTermination(300)                        # 超时保护 (5分钟)
)
```

### 执行逻辑
```
用户任务 → 代码生成 → 用户审批 → Docker执行 → 结果输出 → 任务完成
```

- **第一步**: 接收用户的数据分析任务请求
- **第二步**: Agent 分析任务并生成相应的 Python 代码
- **第三步**: 展示代码内容给用户，等待审批确认
- **第四步**: 在 Docker 容器中安全执行已审批的代码
- **第五步**: 返回执行结果，如数据分析报告
- **第六步**: Agent 确认任务完成并结束对话

## 关键特性

- **安全执行**: Docker 容器隔离，保护主机环境安全
- **用户控制**: 审批机制确保用户对代码执行的完全控制
- **流式输出**: 实时查看 Agent 的思考和执行过程
- **自动终止**: 多重终止条件防止无限循环
- **数据分析**: 专门针对数据分析任务优化的执行环境
- **文件操作**: 支持读取 CSV 文件和生成 Markdown 报告

---

本示例为自动化代码生成和执行提供了安全可控的基础模板，适用于数据分析、报告生成、自动化脚本等场景。
