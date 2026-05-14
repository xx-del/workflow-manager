---
title: Workflow Manager 指令过滤机制
summary: 工作流返回的 pending_instructions 只包含 delegate_task 类型，feedback 由子 agent 内部执行
tags: [workflow-manager, agent-pool, instruction-filtering]
keywords: [feedback, delegate_task, handoff, 指令过滤, pending_instructions]
---

# Workflow Manager 指令过滤机制

## 问题描述

资产收集工作流执行时，返回 20 条指令而非预期的 10 条。每个步骤返回 2 条指令（delegate_task + feedback）。

## 解决方案

**2026-04-21 方案D**：将 feedback 注入到 delegate_task context，由子 agent 内部执行。

## 修改内容

### 1. agent_pool_client.py

**修改位置**：第 199-258 行

**新增逻辑**：
- 将 agent_id、task_id、feedback 命令注入到 params['context']
- 子 agent 从 context 读取必要信息
- 子 agent 执行完任务后调用 terminal 执行 feedback

**删除逻辑**：
- 删除独立的 feedback 指令（第 322-324 行）

### 2. executor.py

**修改位置**：第 364-369 行

**修改前**：
```python
pending_instructions = [
    inst for inst in all_instructions
    if inst.get('action') in ['delegate_task', 'feedback']
]
```

**修改后**：
```python
pending_instructions = [
    inst for inst in all_instructions
    if inst.get('action') == 'delegate_task'
]
```

## 指令类型与执行者

| 指令类型 | 执行者 | 说明 |
|----------|--------|------|
| `delegate_task` | 主 AI | 执行子 Agent 任务 |
| `feedback` | 子 agent 内部 | 已注入到 context，不再独立返回 |

## 效果

- 指令数量：20 → 10
- 功能完整：保留（子 agent 内部执行 feedback）
- 主 AI 职责：简化，只需执行 delegate_task

## 时间戳

2026-04-21

## 作者

Hermes AI (方案D实现)
