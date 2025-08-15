# MagenticOneGroupChat 协作示例

**难度等级** 🟡 中级

本示例展示了使用 `MagenticOneGroupChat`（通用型多智能体团队）实现跨领域任务分解与协作：文件抓取（FileSurfer）与代码执行（CodeExecutorAgent）联合完成数据分析并生成报告。

## 运行方式
```bash
uv run -m examples.team.MagenticOneGroupChat.main
```

## 概述
该示例通过两个主要 agent 协作完成任务：
- `FileSurfer`：负责在工作目录（`coding`）中查找并读取目标文件（如 `excel2.xlsx`）。
- `CodeExecutorAgent`：根据任务生成 Python 代码并在本地沙箱环境（LocalCommandLineCodeExecutor）执行，生成数据分析报告。

示例同时包含一个简单的用户审批函数 `simple_approval_func`，用于在执行代码前向用户展示代码并确认是否执行，保证执行安全性和用户控制权。

## 系统架构

### 核心组件
- `file_surfer`（FileSurfer）
  - 作用：在指定 `base_path`（示例为 `coding`）查找并读取文件内容，供其他 agent 使用。
- `code_executor_agent`（CodeExecutorAgent）
  - 作用：基于模型生成可执行脚本（仅支持 Python），并在 `LocalCommandLineCodeExecutor` 提供的受控工作目录中运行。
- `simple_approval_func`
  - 作用：在执行前展示生成的代码，等待用户输入 y/n 决定是否运行。

### 执行环境
- `LocalCommandLineCodeExecutor(work_dir="coding")`：在本地受限目录执行代码（示例中为 `coding`）。
  - 注意：相比 Docker 执行器，Local 执行器对主机有更高风险；运行此示例前请确认环境安全，或改用 DockerCommandLineCodeExecutor 保持隔离。

## 工作流程
1. 启动模型客户端和 code executor（Local 或 Docker）。
2. `FileSurfer` 搜索并读取目标文件（如 `excel2.xlsx`）。
3. `CodeExecutorAgent` 根据用户需求与文件内容生成 Python 脚本（使用 pandas）。
4. `simple_approval_func` 向用户展示脚本并请求确认。
5. 经用户批准后，在受控执行器中运行脚本，生成报告文件。
6. 结束后关闭模型客户端并停止执行器。

## 核心配置摘录

```python
code_executor = LocalCommandLineCodeExecutor(work_dir="coding")

file_surfer = FileSurfer("FileSurfer", model_client=model_client, base_path="coding")

code_executor_agent = CodeExecutorAgent(
    "code_executor",
    code_executor=code_executor,
    model_client=model_client,
    supported_languages=["python"],
    model_client_stream=True,
    approval_func=simple_approval_func,
    system_message="...",
)

team = MagenticOneGroupChat([file_surfer, code_executor_agent], model_client=model_client)
await Console(team.run_stream(task="帮我分析excel2.xlsx文件，生成一个数据分析报告"))
```

## 建议与注意事项
- 安全性：当使用 `LocalCommandLineCodeExecutor` 时，请确保 `work_dir` 仅包含可信文件并限制对主机的访问。若需更强隔离，优先使用 Docker 执行器。
- 审批机制：始终保留审批函数或其他审查流程，避免执行未知或潜在危险的代码。
- 终止条件：在长期任务或自动化脚本中建议添加 `TimeoutTermination`、`MaxMessageTermination` 或基于文本的终止条件，防止死循环或资源耗尽。
- 依赖管理：确保环境中安装了示例所需的依赖（例如 pandas），或使用镜像预装环境。
- 可扩展性：可添加更多 agent（如数据可视化 agent、结果校验 agent）以实现更复杂的流水线。

## 关键特性
- 跨角色协作：文件抓取与代码执行分工明确，提高系统可解释性与安全性。
- 人机可控：审查与审批机制确保执行可控。
- 易于扩展：可插入更多专家型 agent 以增强分析质量。

---

此示例适合用于学习如何在 AutoGen 框架中组合文件处理与代码执行能力，构建安全且可审计的数据分析自动化流程。
