# Agent-Pool集成问题

**发现时间**: 2026-05-11
**影响**: workflow-manager与agent-pool协作时发现的问题

---

## 问题1：execute命令返回格式不完整

### 问题描述

agent-pool的execute命令默认为plan模式，只返回匹配结果，不返回完整的执行计划（pending_instructions）。

### 实际返回

```json
{
  "success": true,
  "agent": "cli-executor",
  "strategy": "reuse"
}
```

### 期望返回（根据SKILL.md）

```json
{
  "type": "execution_plan",
  "execution": {
    "tool": "delegate_task",
    "params": {...}
  }
}
```

### 解决方案

- 使用`orchestrator.execute()`的完整模式
- 或直接使用workflow-manager的executor.py（自动调用agent_pool_client.execute_full）

---

## 问题2：匹配策略阈值不一致

### 问题描述

agent-pool SKILL.md描述的匹配策略阈值与实际执行不一致。

### SKILL.md标准

| 策略 | 相似度阈值 |
|------|-----------|
| REUSE | ≥0.75 |
| BORROW | 0.60-0.75 |
| GENERATE | <0.60 |

### 实际执行

```
相似度: 0.6294
策略: reuse
```

**分析**：相似度0.6294 < 0.75，按标准应为BORROW，但实际为REUSE。

### 根本原因

agent-pool在低复杂度任务时降低了REUSE阈值。

### 影响

可能匹配到不合适的agent。

---

## 问题3：主AI执行pending_instructions流程

### 正确流程

根据workflow-manager v5.3.0：

```
executor.execute() 自动执行：
├─ [0/6] 生成执行计划 → status.md
├─ [1/6] 加载工作流
├─ [2/6] 展开嵌套节点
├─ [3/6] 分析步骤依赖
├─ [4/6] 调用 agent-pool（agent_pool_client.execute_full）
└─ [5/6] 返回 pending_instructions
     ↓
主 AI 执行：
├─ 执行 pending_instructions 中的每条指令
├─ 更新追踪状态（executor.update_step_status）
├─ 汇总结果
└─ 调用 finalize 停止心跳
```

### 实际执行问题

1. 未生成status.md（[0/6]阶段）
2. agent-pool execute未返回pending_instructions
3. 主AI需要手动构造delegate_task参数

---

## 建议

### 建议1：统一agent-pool返回格式

agent-pool execute命令应返回完整的执行计划，包含pending_instructions字段。

### 建议2：统一匹配策略阈值

确保agent-pool的匹配策略判断与SKILL.md描述一致，或更新SKILL.md说明低复杂度任务的特殊处理。

### 建议3：workflow-manager自动生成status.md

在executor.execute()开始时，自动调用generate_execution_plan_md()生成status.md。

---

## 相关文档

- [SKILL.md](../SKILL.md) - workflow-manager技能文档
- [agent-pool/SKILL.md](../../agent-pool/SKILL.md) - agent-pool技能文档
- [executor.py](../src/core/executor.py) - 工作流执行器代码
- [agent_pool_client.py](../src/core/agent_pool_client.py) - agent-pool客户端代码
