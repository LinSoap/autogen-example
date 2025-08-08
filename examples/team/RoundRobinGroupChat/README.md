# RoundRobinGroupChat Yoda风格示例

**难度等级** 🟢 入门

本章节介绍如何使用 AutoGen 的 RoundRobinGroupChat 实现多智能体协作，主-Agent模仿 yoda 风格生成名言，评论-Agent审核并终止。

**前置知识**
- AutoGen Agent 基础
- 多智能体协作
- 流式输出与 Console 控制台

## 运行方式
```bash
uv run -m examples.team.RoundRobinGroupChat.main
```

## 概述
本示例展示了如何通过 RoundRobinGroupChat 轮流协作，实现主-Agent生成 yoda 风格名言，评论-Agent审核并回复“APPROVE”自动终止。

## 系统架构
系统包含两个主要智能体，并采用多重终止条件保障安全与健壮：

### 核心组件
- **primary_agent**: 负责生成 yoda 风格的学习名言
- **critic_agent**: 负责审核主-Agent回复，合理则回复“APPROVE”终止
- **RoundRobinGroupChat**: 轮流协作团队，保证信息一致性
- **终止条件**: 组合 TextMentionTermination("APPROVE")、MaxMessageTermination(8)、TimeoutTermination(60)，防止死循环、消息泛滥和长时间无响应

### 工具组件
- **Console**: 控制台流式输出，实时展示智能体对话过程

## 工作流程
1. 用户发起“请用 yoda 风格说一句关于学习的名言”请求
2. primary_agent 生成 yoda 风格回复
3. critic_agent 审核回复，合理则回复“APPROVE”
4. 终止条件触发（满足“APPROVE”、消息数达到8或超时60秒任一条件），团队对话结束

## 核心组件详解
- **primary_agent**: system_message 强制 yoda 风格输出，开启 model_client_stream 实时流式输出
- **critic_agent**: system_message 设定审核规则，合理则终止
- **终止条件**: 采用 TextMentionTermination("APPROVE") | MaxMessageTermination(8) | TimeoutTermination(60) 组合，提升健壮性和安全性
- **Console**: 通过 team.run_stream 实现流式控制台输出

## 关键特性
- 多智能体轮流协作
- 终止条件灵活可控（支持文本、消息数、超时三重保护）
- 流式输出，实时观察对话过程
- 代码结构清晰，易于扩展

---
本示例为多智能体协作、流式输出和终止机制提供了基础模板，适合 AutoGen 新手和进阶开发者参考。
