# workflow-manager 执行架构详解

## 核心发现（代码验证）

**executor.py 内置了 agent_pool_client 调用，主 AI 不需要也不应该手动调用 agent-pool。**

---

## 执行流程（代码证据）

```
主 AI 调用 workflow-manager 技能
     ↓
executor.execute() 自动执行：
     ├─ [1/6] 加载工作流（loader.load）
     ├─ [2/6] 展开嵌套节点（workflow_expander.expand）
     ├─ [3/6] 分析步骤依赖（analyzer.analyze）
     ├─ [4/6] 调用 agent-pool（agent_pool_client.execute_full）
     └─ [5/6] 返回 pending_instructions
     ↓
主 AI 执行：
     ├─ 执行 pending_instructions 中的每条指令
     ├─ 更新追踪状态（executor.update_step_status）
     ├─ 汇总结果
     └─ 调用 finalize 停止心跳
```

---

## 关键代码位置

| 文件 | 行数 | 功能 |
|------|------|------|
| `src/core/executor.py` | 842 | `agent_pool_client.execute_full()` 调用 |
| `src/core/executor.py` | 213-257 | 返回 `pending_instructions` 给主 AI |
| `src/core/agent_pool_client.py` | 108-182 | `execute_full()` 方法实现 |
| `src/core/agent_pool_client.py` | 381-388 | 构建 instructions 列表 |

---

## 返回值结构

```python
{
    'status': 'execution_required',  # ← 表示需要主 AI 执行
    'pending_instructions': [...],   # ← 主 AI 必须执行这些指令
    'execution_status': 'awaiting_delegate_task',
    'execution_mode': {
        'type': 'strict_serial',     # 执行模式
        'delegate_task_usage': 'single'
    },
    'ai_action_required': {
        'tool': 'delegate_task',
        'usage': '逐个调用 delegate_task(task=...)'
    }
}
```

---

## 主 AI 职责边界

| 操作 | 执行者 | 说明 |
|------|--------|------|
| 加载工作流 | executor.py | 自动 |
| 展开节点 | executor.py | 自动 |
| 分析依赖 | executor.py | 自动 |
| 调用 agent-pool | executor.py | **自动（关键）** |
| 生成指令 | executor.py | 自动 |
| 执行指令 | 主 AI | 调用 delegate_task |
| 更新状态 | 主 AI | 调用 executor.update_step_status |
| 汇总结果 | 主 AI | 生成报告 |
| 停止心跳 | 主 AI | 调用 finalize |

---

## 常见误解纠正

### ❌ 错误理解

"主 AI 需要调用 agent-pool 技能来匹配 agent"

### ✅ 正确理解

"workflow-manager 的 executor.py 已经内置了 agent_pool_client 调用，主 AI 只需执行返回的 pending_instructions"

---

## 验证方法

在执行工作流时，日志会显示：

```
[AgentPoolClient] 执行任务: ...
[AgentPoolClient] 能力: [...]
[Executor] 收集到 N 条指令，返回执行计划
```

如果看到这些日志，说明 executor.py 正确调用了 agent_pool_client。

---

## 文档更新记录

- 2026-05-09: 创建文档，记录架构发现
- 2026-05-09: 优化 SKILL.md，减少重复内容（708→531 行）
